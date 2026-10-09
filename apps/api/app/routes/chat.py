import asyncio
import base64
import hashlib
import json
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.permissions import require_employee
from app.db.models.attachment import Attachment
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.submission import Submission
from app.db.session import get_db
from app.llm.client import ProviderArtifact, ProviderMessage, ProviderRequest
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    ConversationsPage,
    DeltaEvent,
    DoneEvent,
    ErrorEvent,
    MessageResponse,
    MessagesPage,
    MessageSubmissionRequest,
    ProcessingEvent,
    SanitizedEvent,
)
from app.schemas.common import ApiError
from app.schemas.uploads import AttachmentResponse
from app.services.chat import require_current_policy, resanitize_history
from app.services.guard import (
    Engine,
    EventBatch,
    EventRecord,
    EventSink,
    PolicyStore,
    SanitizeRequest,
    SanitizeResult,
)
from app.storage.files import LocalFileStorage, storage_for_request

router = APIRouter(prefix="/api/v1", tags=["Employee chat"])


def _conversation(db: Session, identity, conversation_id: UUID) -> Conversation:
    value = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == identity.organization_id,
            Conversation.employee_id == identity.user_id,
        )
    )
    if not value:
        raise ApiError(404, "NOT_FOUND", "Conversation unavailable")
    return value


def _page(db: Session, model, identity, limit: int, cursor: str | None, extra=None):
    stamp = model.updated_at if model is Conversation else model.created_at
    ident = model.id
    query = select(model)
    if model is Conversation:
        query = query.where(
            model.organization_id == identity.organization_id,
            model.employee_id == identity.user_id,
        )
    else:
        query = query.where(extra)
    if cursor:
        try:
            value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
            if (
                value["organization"] != str(identity.organization_id)
                or value["employee"] != str(identity.user_id)
                or value["table"] != model.__tablename__
            ):
                raise ValueError()
            time = datetime.fromisoformat(value["time"])
            row_id = UUID(value["id"])
        except (ValueError, KeyError, TypeError):
            raise ApiError(422, "INVALID_CURSOR", "Invalid page cursor") from None
        query = query.where(or_(stamp < time, and_(stamp == time, ident < row_id)))
    values = list(db.scalars(query.order_by(stamp.desc(), ident.desc()).limit(limit + 1)))
    next_cursor = None
    if len(values) > limit:
        last = values[limit - 1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "organization": str(identity.organization_id),
                    "employee": str(identity.user_id),
                    "table": model.__tablename__,
                    "time": getattr(last, stamp.key).isoformat(),
                    "id": str(last.id),
                }
            ).encode()
        ).decode()
    return values[:limit], next_cursor


def _message_dto(row: Message) -> MessageResponse:
    return MessageResponse(
        id=row.id,
        conversation_id=row.conversation_id,
        role=row.role,
        text=row.sanitized_text,
        attachment_ids=[UUID(value) for value in json.loads(row.attachment_ids)],
        state=row.state,
        created_at=row.created_at,
    )


def _attachment_dto(row: Attachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=row.id,
        filename=row.filename,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        state=row.state,
        sanitized_download_url=(
            f"/api/v1/uploads/{row.id}/sanitized" if row.state == "sanitized" else None
        ),
    )


def _event(name: str, payload) -> bytes:
    encoded = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)
    return f"event: {name}\ndata: {encoded}\n\n".encode("utf-8")


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(
    body: ConversationCreate,
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
):
    item = Conversation(
        organization_id=identity.organization_id,
        employee_id=identity.user_id,
        title=body.title,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/conversations", response_model=ConversationsPage)
def list_conversations(
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
):
    items, next_cursor = _page(db, Conversation, identity, limit, cursor)
    return {
        "items": [ConversationResponse.model_validate(item) for item in items],
        "next_cursor": next_cursor,
    }


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesPage)
def list_messages(
    conversation_id: UUID,
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
):
    conversation = _conversation(db, identity, conversation_id)
    items, next_cursor = _page(
        db,
        Message,
        identity,
        limit,
        cursor,
        (Message.conversation_id == conversation.id)
        & (Message.organization_id == identity.organization_id),
    )
    return {"items": [_message_dto(item) for item in items], "next_cursor": next_cursor}


@router.post("/conversations/{conversation_id}/messages")
def submit_message(
    conversation_id: UUID,
    body: MessageSubmissionRequest,
    request: Request,
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
):
    request_hash = hashlib.sha256(
        json.dumps(
            {
                "text": body.text,
                "attachment_ids": [str(item) for item in body.attachment_ids],
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    existing = db.scalar(
        select(Submission).where(
            Submission.employee_id == identity.user_id,
            Submission.conversation_id == conversation_id,
            Submission.client_request_id == body.client_request_id,
        )
    )
    if existing:
        if existing.request_hash != request_hash:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Request ID was already used")
        if existing.state == "processing":
            raise ApiError(409, "SUBMISSION_ACTIVE", "A request is already processing")
        if not existing.stream_result:
            raise ApiError(503, "PROCESSING_FAILED", "The previous request could not be completed")
        return StreamingResponse(
            iter((existing.stream_result or "").encode("utf-8") for _ in [0]),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )
    submission = Submission(
        organization_id=identity.organization_id,
        employee_id=identity.user_id,
        conversation_id=conversation_id,
        client_request_id=body.client_request_id,
        request_hash=request_hash,
        state="processing",
    )
    db.add(submission)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if not db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.organization_id == identity.organization_id,
                Conversation.employee_id == identity.user_id,
            )
        ):
            raise ApiError(404, "NOT_FOUND", "Conversation unavailable") from None
        raise ApiError(409, "SUBMISSION_ACTIVE", "A request is already processing") from None
    db.refresh(submission)
    try:
        conversation = _conversation(db, identity, conversation_id)
    except ApiError:
        submission.state = "failed"
        db.commit()
        raise
    attachments = []
    for attachment_id in body.attachment_ids:
        attachment = db.scalar(
            select(Attachment).where(
                Attachment.id == attachment_id,
                Attachment.organization_id == identity.organization_id,
                Attachment.employee_id == identity.user_id,
            )
        )
        if not attachment or attachment.state != "uploaded":
            submission.state = "failed"
            db.commit()
            raise ApiError(404, "NOT_FOUND", "Attachment unavailable")
        attachments.append(attachment)

    policy_store: PolicyStore | None = getattr(request.app.state, "policy_store", None)
    engine: Engine | None = getattr(request.app.state, "sanitization_engine", None)
    event_sink: EventSink | None = getattr(request.app.state, "event_sink", None)
    llm = getattr(request.app.state, "llm_client", None)
    storage: LocalFileStorage = storage_for_request()
    if not policy_store or not engine or not event_sink or not llm:
        from app.config import get_settings

        settings = get_settings()
        if (
            settings.app_env in {"development", "test"}
            and settings.demo_adapters_enabled
        ):
            from app.services.guard import LocalEventSink, RuleEngine, StaticPolicyStore
            from demo.adapters.llm import DemoLLM

            request.app.state.policy_store = policy_store or StaticPolicyStore()
            request.app.state.sanitization_engine = engine or RuleEngine()
            request.app.state.event_sink = event_sink or LocalEventSink()
            request.app.state.llm_client = llm or DemoLLM()
            policy_store = request.app.state.policy_store
            engine = request.app.state.sanitization_engine
            event_sink = request.app.state.event_sink
            llm = request.app.state.llm_client
    if not policy_store or not engine or not event_sink or not llm:
        submission.state = "failed"
        db.commit()
        raise ApiError(503, "GUARD_UNAVAILABLE", "Required privacy services are unavailable")

    async def stream():
        frames: list[bytes] = []
        user_msg = None
        assistant_msg = None
        try:
            processing = ProcessingEvent(submission_id=submission.id)
            frames.append(_event("processing", processing))
            yield frames[-1]
            policy = require_current_policy(policy_store, identity.organization_id)
            # Re-sanitize every retained turn under this exact immutable snapshot.
            history = list(
                db.scalars(
                    select(Message)
                    .where(
                        Message.conversation_id == conversation.id,
                        Message.organization_id == identity.organization_id,
                        Message.state == "completed",
                    )
                    .order_by(Message.created_at.asc(), Message.id.asc())
                )
            )
            safe_history = resanitize_history(
                messages=history,
                organization_id=identity.organization_id,
                policy=policy,
                engine=engine,
            )
            report_events: list[EventRecord] = []
            historical_artifacts: list[ProviderArtifact] = []
            for item in history:
                retained = SanitizeResult.model_validate(
                    engine.sanitize(
                        SanitizeRequest(
                            organization_id=identity.organization_id,
                            policy=policy,
                            text=item.sanitized_text,
                        )
                    ).model_dump()
                )
                for index, finding in enumerate(retained.findings):
                    report_events.append(
                        EventRecord(
                            event_key=f"history:{item.id}:{policy.version}:{index}",
                            organization_id=identity.organization_id,
                            employee_id=identity.user_id,
                            conversation_id=conversation.id,
                            rule=finding.rule,
                            action=finding.action,
                            count=finding.count,
                            policy_version=policy.version,
                        )
                    )
                if item.role == "user":
                    for attachment_id in json.loads(item.attachment_ids):
                        retained_attachment = db.scalar(
                            select(Attachment).where(
                                Attachment.id == UUID(attachment_id),
                                Attachment.organization_id == identity.organization_id,
                                Attachment.employee_id == identity.user_id,
                            )
                        )
                        if retained_attachment is None:
                            raise ValueError("Historical attachment unavailable")
                        original = storage.read_original(retained_attachment.original_key)
                        retained_result = SanitizeResult.model_validate(
                            engine.sanitize(
                                SanitizeRequest(
                                    organization_id=identity.organization_id,
                                    policy=policy,
                                    text="",
                                    filename=retained_attachment.filename,
                                    mime_type=retained_attachment.mime_type,
                                    original_bytes=original,
                                )
                            ).model_dump()
                        )
                        if retained_result.sanitized_bytes is None:
                            raise ValueError("Historical sanitized artifact unavailable")
                        key = storage.write_sanitized(
                            identity.organization_id,
                            identity.user_id,
                            retained_attachment.id,
                            retained_result.sanitized_bytes,
                        )
                        retained_attachment.sanitized_key = key
                        retained_attachment.state = "sanitized"
                        if retained_attachment.mime_type in {"image/png", "image/jpeg"}:
                            historical_artifacts.append(
                                ProviderArtifact.from_image(
                                    retained_attachment.filename,
                                    retained_attachment.mime_type,
                                    retained_result.sanitized_bytes,
                                )
                            )
                        else:
                            if not retained_result.sanitized_text.strip():
                                raise ValueError("Historical sanitized text unavailable")
                            historical_artifacts.append(
                                ProviderArtifact.from_text(
                                    retained_attachment.filename,
                                    retained_result.sanitized_text,
                                )
                            )
                        for index, finding in enumerate(retained_result.findings):
                            report_events.append(
                                EventRecord(
                                    event_key=f"history:attachment:{retained_attachment.id}:{policy.version}:{index}",
                                    organization_id=identity.organization_id,
                                    employee_id=identity.user_id,
                                    conversation_id=conversation.id,
                                    attachment_id=retained_attachment.id,
                                    rule=finding.rule,
                                    action=finding.action,
                                    count=finding.count,
                                    policy_version=policy.version,
                                )
                            )
            sanitized = SanitizeResult.model_validate(
                engine.sanitize(
                    SanitizeRequest(
                        organization_id=identity.organization_id,
                        policy=policy,
                        text=body.text,
                    )
                ).model_dump()
            )
            user_msg = Message(
                organization_id=identity.organization_id,
                conversation_id=conversation.id,
                role="user",
                sanitized_text=sanitized.sanitized_text,
                state="completed",
                policy_version=policy.version,
                attachment_ids=json.dumps([str(item.id) for item in attachments]),
            )
            db.add(user_msg)
            safe_artifacts: list[ProviderArtifact] = []
            sanitized_rows = []
            for attachment in attachments:
                raw = storage.read_original(attachment.original_key)
                artifact_result = SanitizeResult.model_validate(
                    engine.sanitize(
                        SanitizeRequest(
                            organization_id=identity.organization_id,
                            policy=policy,
                            text="",
                            filename=attachment.filename,
                            mime_type=attachment.mime_type,
                            original_bytes=raw,
                        )
                    ).model_dump()
                )
                if artifact_result.sanitized_bytes is None:
                    raise ValueError("Sanitized artifact unavailable")
                key = storage.write_sanitized(
                    identity.organization_id,
                    identity.user_id,
                    attachment.id,
                    artifact_result.sanitized_bytes,
                )
                attachment.sanitized_key = key
                attachment.state = "sanitized"
                if attachment.mime_type in {"image/png", "image/jpeg"}:
                    safe_artifacts.append(
                        ProviderArtifact.from_image(
                            attachment.filename,
                            attachment.mime_type,
                            artifact_result.sanitized_bytes,
                        )
                    )
                else:
                    extracted = artifact_result.sanitized_text
                    if not extracted.strip():
                        raise ValueError("Sanitized document text unavailable")
                    safe_artifacts.append(ProviderArtifact.from_text(attachment.filename, extracted))
                sanitized_rows.append(_attachment_dto(attachment))
                for index, finding in enumerate(artifact_result.findings):
                    report_events.append(
                        EventRecord(
                            event_key=f"{submission.id}:{policy.version}:{attachment.id}:{index}",
                            organization_id=identity.organization_id,
                            employee_id=identity.user_id,
                            conversation_id=conversation.id,
                            attachment_id=attachment.id,
                            rule=finding.rule,
                            action=finding.action,
                            count=finding.count,
                            policy_version=policy.version,
                        )
                    )
            all_findings = sanitized.findings
            report_events.extend(
                [
                        EventRecord(
                            event_key=f"{submission.id}:{policy.version}:text:{i}",
                            organization_id=identity.organization_id,
                            employee_id=identity.user_id,
                            conversation_id=conversation.id,
                            rule=finding.rule,
                            action=finding.action,
                            count=finding.count,
                            policy_version=policy.version,
                        )
                        for i, finding in enumerate(all_findings)
                ]
            )
            event_sink.record(EventBatch(events=report_events))
            db.flush()
            sanitized_event = SanitizedEvent(
                submission_id=submission.id,
                user_message=_message_dto(user_msg),
                attachments=sanitized_rows,
                policy_version=policy.version,
            )
            frames.append(_event("sanitized", sanitized_event))
            db.commit()
            yield frames[-1]
            payload = ProviderRequest(
                submission_id=submission.id,
                messages=[
                    *safe_history,
                    ProviderMessage(role="user", sanitized_text=sanitized.sanitized_text),
                ],
                artifacts=[*historical_artifacts, *safe_artifacts],
            )
            assistant_msg = Message(
                organization_id=identity.organization_id,
                conversation_id=conversation.id,
                role="assistant",
                sanitized_text="",
                state="processing",
                policy_version=policy.version,
                attachment_ids="[]",
            )
            db.add(assistant_msg)
            db.flush()
            accumulated = ""
            sequence = 1
            async for provider_delta in llm.stream(payload):
                from app.llm.client import ProviderDelta

                delta = ProviderDelta.model_validate(
                    provider_delta.model_dump()
                    if isinstance(provider_delta, ProviderDelta)
                    else provider_delta
                )
                accumulated += delta.text
                event = DeltaEvent(
                    submission_id=submission.id,
                    assistant_message_id=assistant_msg.id,
                    sequence=sequence,
                    text=delta.text,
                )
                sequence += 1
                submission.next_sequence = sequence
                db.commit()
                frame = _event("delta", event)
                frames.append(frame)
                yield frame
            assistant_msg.sanitized_text = accumulated
            assistant_msg.state = "completed"
            db.flush()
            done = DoneEvent(
                submission_id=submission.id,
                assistant_message=_message_dto(assistant_msg),
            )
            frames.append(_event("done", done))
            submission.state = "completed"
            submission.assistant_message_id = assistant_msg.id
            submission.stream_result = b"".join(frames).decode("utf-8")
            db.commit()
            yield frames[-1]
        except asyncio.CancelledError:
            db.rollback()
            submission.state = "cancelled"
            failure = ErrorEvent(
                submission_id=submission.id,
                code="SUBMISSION_CANCELLED",
                message="The request was cancelled.",
                retryable=False,
            )
            frames.append(_event("error", failure))
            submission.stream_result = b"".join(frames).decode("utf-8")
            db.commit()
            raise
        except Exception:
            db.rollback()
            submission.state = "failed"
            db.commit()
            failure = ErrorEvent(
                submission_id=submission.id,
                code="PROCESSING_FAILED",
                message="Your request could not be safely processed. Please retry.",
                retryable=True,
            )
            frame = _event("error", failure)
            frames.append(frame)
            submission.stream_result = b"".join(frames).decode("utf-8")
            db.commit()
            yield frame

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
