from pathlib import PurePath
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import require_employee
from app.db.models.attachment import Attachment
from app.db.session import get_db
from app.schemas.common import ApiError
from app.schemas.uploads import (
    AttachmentResponse,
    EmptyUploadCompletion,
    UploadInitRequest,
    UploadInitResponse,
)
from app.storage.files import LocalFileStorage, storage_for_request

router = APIRouter(prefix="/api/v1/uploads", tags=["Uploads"])


def attachment_dto(row: Attachment) -> AttachmentResponse:
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


def owned_attachment(db: Session, identity, attachment_id: UUID) -> Attachment:
    item = db.scalar(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.organization_id == identity.organization_id,
            Attachment.employee_id == identity.user_id,
        )
    )
    if not item:
        raise ApiError(404, "NOT_FOUND", "File unavailable")
    return item


@router.post("/init", response_model=UploadInitResponse, status_code=201)
def initialize_upload(
    body: UploadInitRequest,
    request: Request,
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
):
    filename = PurePath(body.filename.replace("\\", "/")).name
    if not filename or filename in {".", ".."}:
        raise ApiError(422, "VALIDATION_ERROR", "Invalid filename")
    storage = storage_for_request()
    item = Attachment(
        id=uuid4(),
        organization_id=identity.organization_id,
        employee_id=identity.user_id,
        conversation_id=None,
        original_key=f"original/{identity.organization_id}/{identity.user_id}",
        sanitized_key=None,
        filename=filename,
        mime_type=body.declared_mime,
        size_bytes=body.size_bytes,
        state="pending_upload",
    )
    item.original_key = (
        f"original/{identity.organization_id}/{identity.user_id}/{item.id}"
    )
    db.add(item)
    db.commit()
    grant = storage.create_upload(
        identity.organization_id,
        identity.user_id,
        item.id,
        filename,
        body.declared_mime,
        body.size_bytes,
    )
    return UploadInitResponse(attachment=attachment_dto(item), upload=grant)


@router.put("/{attachment_id}/content", status_code=204)
async def upload_content(
    attachment_id: UUID,
    request: Request,
    expires: int = Query(..., ge=1),
    signature: str = Query(..., min_length=64, max_length=64),
    db: Session = Depends(get_db),
):
    item = db.get(Attachment, attachment_id)
    if not item:
        raise ApiError(404, "NOT_FOUND", "Upload unavailable")
    if item.state != "pending_upload":
        raise ApiError(409, "UPLOAD_STATE_INVALID", "Upload is no longer available")
    storage = storage_for_request()
    if not storage.verify_signature(
        item.organization_id, item.employee_id, item.id, expires, signature
    ):
        raise ApiError(404, "NOT_FOUND", "Upload unavailable")
    content = await request.body()
    storage.receive_upload(item.organization_id, item.employee_id, item.id, content)
    return Response(status_code=204)


@router.post("/{attachment_id}/complete", response_model=AttachmentResponse)
def complete_upload(
    attachment_id: UUID,
    body: EmptyUploadCompletion,
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
    storage: LocalFileStorage = Depends(storage_for_request),
):
    item = owned_attachment(db, identity, attachment_id)
    try:
        key, size, digest = storage.verify_upload(
            item.organization_id,
            item.employee_id,
            item.id,
            item.filename,
            item.mime_type,
            item.size_bytes,
        )
    except ApiError:
        raise
    except OSError:
        raise ApiError(422, "UPLOAD_MISSING", "Uploaded file is unavailable") from None
    item.original_key = key
    item.size_bytes = size
    item.content_hash = digest
    item.state = "uploaded"
    db.commit()
    db.refresh(item)
    return attachment_dto(item)


@router.get("/{attachment_id}", response_model=AttachmentResponse)
def get_upload(
    attachment_id: UUID,
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
):
    return attachment_dto(owned_attachment(db, identity, attachment_id))


@router.get("/{attachment_id}/sanitized")
def get_sanitized_file(
    attachment_id: UUID,
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
    storage: LocalFileStorage = Depends(storage_for_request),
):
    item = owned_attachment(db, identity, attachment_id)
    if item.state != "sanitized" or not item.sanitized_key:
        raise ApiError(409, "FILE_NOT_READY", "Sanitized file is not available")
    try:
        content = storage.read_sanitized(item.sanitized_key)
    except OSError:
        raise ApiError(503, "STORAGE_UNAVAILABLE", "Sanitized file is unavailable") from None
    disposition_name = item.filename.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=content,
        media_type=item.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{disposition_name}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
