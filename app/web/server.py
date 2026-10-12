"""Loopback-only, single-reviewer API. Public summaries never contain source text."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.formparsers import MultiPartParser

from app.engines.audit import AuditEngine, ReviewerFeedback
from app.engines.audit.storage import AuditStore, PROJECT_ROOT
from app.engines.file_intelligence import FileIntelligenceEngine
from app.engines.extraction.office import source_hash
from app.pipeline import DocumentPipeline
from .models import (DocumentState, StageState, Finding, FindingList, FindingDetail, SourceWindow,
                     PreviewHighlight, FeedbackRequest, MissedRequest, SaveRequest, LoadRequest,
                     ReviewIdentity, AuditView, AuditEvent, FindingComparison)

MAX_UPLOAD = 30 * 1024 * 1024
STATIC = Path(__file__).parent / "static"
STAGES = ["file_intelligence", "extraction", "detection", "face_detection", "redaction", "audit", "artifact_redaction", "artifact_verification"]
FORMATS = {".pdf": "pdf", ".docx": "docx", ".pptx": "pptx"}
MIME = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}


class LocalBoundary:
    """Bound requests before multipart parsing; block cross-origin mutation/DNS rebinding."""
    def __init__(self, app, max_upload_bytes, allow_test_host=False):
        self.app, self.maximum = app, max_upload_bytes
        self.hosts = {"127.0.0.1", "localhost", "[::1]"} | ({"testserver"} if allow_test_host else set())

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        host = headers.get(b"host", b"").decode("latin-1")
        hostname = host.split(":")[0] if not host.startswith("[") else host.split("]")[0] + "]"
        origin = headers.get(b"origin", b"").decode("latin-1")
        expected = scope.get("scheme", "http") + "://" + host
        async def reject(status, message):
            await JSONResponse({"detail": message}, status_code=status)(scope, receive, send)
        if hostname not in self.hosts or (origin and origin != expected):
            return await reject(403, "This application accepts trusted local requests only.")
        mutating = scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}
        if mutating and headers.get(b"x-cadence-local") != b"1":
            return await reject(403, "Use the local review application to submit changes.")
        # Multipart data stays in memory until explicitly written to our private area.
        # No framework spool file containing PII is allowed in the public OS temp area.
        maximum = self.maximum + 65536 if scope["path"] == "/api/documents" else 16384
        messages, size = [], 0
        if mutating:
            try:
                declared = int(headers.get(b"content-length", b"0"))
            except ValueError:
                return await reject(400, "Invalid request size.")
            if declared > maximum:
                return await reject(413, "The upload or request exceeds the local size limit.")
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                size += len(message.get("body", b""))
                if size > maximum:
                    return await reject(413, "The upload or request exceeds the local size limit.")
                messages.append(message)
                if not message.get("more_body", False):
                    break
        async def replay():
            if messages:
                return messages.pop(0)
            return await receive()
        async def secured(message):
            if message["type"] == "http.response.start":
                message["headers"] += [(b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"), (b"x-frame-options", b"SAMEORIGIN"),
                    (b"content-security-policy", b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; object-src 'none'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'")]
            await send(message)
        started = False
        async def guarded_send(message):
            nonlocal started
            if message["type"] == "http.response.start": started = True
            await secured(message)
        try:
            await self.app(scope, replay if mutating else receive, guarded_send)
        except Exception:
            # Keep vendor exceptions/tracebacks out of Uvicorn and access logs.
            if not started:
                await JSONResponse({"detail":"The local operation failed. No sensitive error details are returned."},
                    status_code=500)(scope, receive, guarded_send)


@dataclass
class ReviewSession:
    session_id: str
    display_name: str
    format: str
    result: object
    saved_revision: int | None = None


def create_app(*, work_dir=None, pipeline=None, max_upload_bytes=MAX_UPLOAD, allow_test_host=False):
    if not 0 < max_upload_bytes <= MAX_UPLOAD:
        raise ValueError("Choose a bounded local upload size")
    store = AuditStore(work_dir or PROJECT_ROOT / ".private_review_app")
    store._prepare()
    root = store.directory
    for name in ("uploads", "artifacts", "audits"):
        AuditStore(root / name)._prepare()
    MultiPartParser.spool_max_size = MAX_UPLOAD + 65537
    engine = pipeline or DocumentPipeline(audit=AuditEngine(root / "audits"), artifact_output_dir=root / "artifacts")
    lock, sessions, saved_refs = RLock(), {}, {}
    app = FastAPI(title="Cadence PII Guard", debug=False, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(LocalBoundary, max_upload_bytes=max_upload_bytes, allow_test_host=allow_test_host)
    app.state.sessions, app.state.pipeline, app.state.work_dir = sessions, engine, root
    app.mount("/assets", StaticFiles(directory=STATIC), name="assets")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse({"detail": "Invalid request fields or source selection."}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return JSONResponse({"detail": "The local operation failed. No sensitive error details are returned."}, status_code=500)

    def session(identifier):
        if not re.fullmatch(r"[0-9a-f]{32}", identifier) or identifier not in sessions:
            raise HTTPException(404, "Review session not found.")
        return sessions[identifier]

    def audit(s):
        if s.result.audit_result is None:
            raise HTTPException(409, "Processing did not produce a reviewable audit.")
        return s.result.audit_result

    def file_for(s):
        artifact = s.result.artifact_result
        if artifact is None or artifact.path is None or s.result.failure:
            raise HTTPException(409, "No current review artifact is available.")
        path = Path(artifact.path)
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in [path, *path.parents]):
            raise HTTPException(409, "Artifact access is unavailable.")
        resolved = path.resolve()
        if not resolved.is_relative_to(root / "artifacts") or not resolved.is_file() or resolved.suffix != "." + s.format:
            raise HTTPException(409, "Artifact access is unavailable.")
        return resolved

    def state(s):
        result = s.result
        available = False
        try:
            file_for(s)
            available = True
        except HTTPException:
            pass
        stages = []
        issue_message = None
        if result.failure and result.extraction_result is not None:
            source = result.extraction_result
            mapping = source.pdf_source if source.file_type == "pdf" else source.structure
            if mapping is not None:
                try:
                    changed = source_hash(source.source_path) != mapping.source_sha256
                except OSError:
                    changed = True
                if changed:
                    issue_message = "The original upload changed or is missing. Upload a new copy before regenerating the artifact."
        for name in STAGES:
            completed = name in result.stage_timings
            failed = result.failure is not None and result.failure.stage == name
            if name == "artifact_verification" and result.artifact_result and result.artifact_result.verification_failures:
                failed = True
            stages.append(StageState(name=name, state="Failed" if failed else "Completed" if completed else "Pending",
                                     seconds=result.stage_timings.get(name)))
        return DocumentState(document_session_id=s.session_id, format=s.format,
            revision=result.audit_result.revision if result.audit_result else None, saved_revision=s.saved_revision,
            artifact_available=available, summary=result.sanitized_summary(), stages=stages, issue_message=issue_message)

    def finding(record, s=None):
        d = record.effective_detection
        visual=getattr(d,'category',None)=='BIOMETRIC'
        protected=visual and s is not None and s.result.artifact_result is not None and record.detection_id in s.result.artifact_result.protected_face_ids
        thumbnail=False;unplaced=False
        if visual and s is not None:
            unit=next(u for u in audit(s).extraction.visual.units if u.unit_id==d.unit_id)
            thumbnail=all(p.get('role')=='document_thumbnail' for p in unit.placements)
            unplaced=not any(p.get('mapped') for p in unit.placements)
        return Finding(finding_id=record.detection_id, entity_type=d.entity_type, location=d.page_number,
            confidence=d.confidence, recognizer=d.recognizer[:100], automated_decision=record.automated_decision,
            effective_decision=record.effective_decision, review_status='PROTECTED' if protected else record.redaction_status,
            corrected=record.corrected,kind='VISUAL' if visual else 'TEXT',locations=[] if thumbnail or unplaced else d.locations if visual else [d.page_number],
            biometric_action=('Blur verified' if protected else 'Retained by decision' if d.final_decision=='REJECT' else 'Blur requires review' if d.final_decision=='REVIEW' else 'Blur required') if visual else None,
            protected=protected,visual_location_label='Document preview image; no page/slide placement' if thumbnail
            else 'Unmapped package image; placement unverified' if unplaced else None)

    def record_for(s, identifier):
        current=audit(s)
        record = next((r for r in current.records+current.visual_records if r.detection_id == identifier), None)
        if record is None:
            raise HTTPException(404, "Finding not found in this review session.")
        return record

    def revision(s, expected):
        if audit(s).revision != expected:
            raise HTTPException(409, "This review changed. Refresh before submitting feedback.")

    def apply(s, feedback):
        updated = engine.apply_feedback(s.result, feedback)
        if updated.audit_result is None or (updated.failure and updated.failure.stage == "feedback"):
            raise HTTPException(422, "Feedback was not applied. Check the finding, source range and current decision.")
        # Adopt only the result returned by the pipeline; never edit engine objects.
        s.result = updated
        return state(s)

    @app.get("/")
    def home():
        return FileResponse(STATIC / "index.html", media_type="text/html")

    @app.get("/api/config")
    def config():
        return {"max_upload_bytes": max_upload_bytes, "supported_formats": list(FORMATS.values()), "trusted_local_only": True}

    @app.get("/api/documents", response_model=list[DocumentState])
    def documents():
        with lock:
            return [state(s) for s in sessions.values()]

    @app.post("/api/documents", response_model=DocumentState)
    def upload(file: UploadFile = File(...)):
        name = file.filename or ""
        if not name or len(name) > 160 or any(c in name for c in ("/", "\\", "\x00")) or any(ord(c) < 32 for c in name):
            raise HTTPException(400, "Choose a file with a simple document filename.")
        extension = Path(name).suffix.lower()
        if extension not in FORMATS:
            raise HTTPException(415, "Supported uploads are PDF, DOCX and PPTX.")
        identifier = uuid4().hex
        path = root / "uploads" / (uuid4().hex + extension)
        size = 0
        try:
            with path.open("xb") as target:
                if os.name != "nt": os.fchmod(target.fileno(), 0o600)
                while chunk := file.file.read(65536):
                    size += len(chunk)
                    if size > max_upload_bytes:
                        raise HTTPException(413, "The document exceeds the local upload size limit.")
                    target.write(chunk)
            if not size:
                raise HTTPException(400, "The document is empty.")
            try:
                metadata = FileIntelligenceEngine().analyze(str(path))
                if metadata.file_type != FORMATS[extension]:
                    raise ValueError()
            except Exception:
                raise HTTPException(400, "Document content is corrupt, unsupported or does not match its extension.") from None
            with lock:
                result = engine.process(path)
                s = ReviewSession(identifier, name, FORMATS[extension], result)
                sessions[identifier] = s
                return state(s)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            file.file.close()

    @app.get("/api/documents/{identifier}", response_model=DocumentState)
    def get_document(identifier: str):
        with lock: return state(session(identifier))

    @app.get("/api/documents/{identifier}/review", response_model=ReviewIdentity)
    def identity(identifier: str):
        with lock:
            s = session(identifier)
            pages = s.result.extraction_result.pages if s.result.extraction_result else []
            return ReviewIdentity(display_name=s.display_name,
                location_kind={"pdf": "page", "docx": "logical segment", "pptx": "slide"}[s.format], location_count=len(pages))

    @app.get("/api/documents/{identifier}/findings", response_model=FindingList)
    def findings(identifier: str, decision: str = Query("ALL", pattern="^(ALL|CONFIRM|REJECT|REVIEW)$"),
                 entity: str = Query("", max_length=60), location: int | None = Query(None, ge=1),
                 q: str = Query("", max_length=80), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
        with lock:
            s=session(identifier);current=audit(s)
            records=current.records+current.visual_records
            values = [finding(r,s) for r in records]
            selected = [v for v in values if (decision == "ALL" or v.effective_decision == decision)
                and (not entity or v.entity_type == entity) and (location is None or location in v.locations)
                and (not q or q.lower() in (v.finding_id + " " + v.entity_type + " " + v.recognizer).lower())]
            return FindingList(items=selected[offset:offset+limit], total=len(selected),
                entities=sorted({v.entity_type for v in values}), locations=sorted({n for v in values for n in v.locations}))

    @app.get("/api/documents/{identifier}/findings/{finding_id}", response_model=FindingDetail)
    def detail(identifier: str, finding_id: str):
        with lock:
            s = session(identifier)
            record = record_for(s, finding_id)
            d = record.effective_detection
            if getattr(d,'category',None)=='BIOMETRIC':
                metadata=finding(record,s);base=f'/api/documents/{identifier}/findings/{finding_id}/visual-crop'
                return FindingDetail(finding=metadata,before='',candidate='',after='',candidate_truncated=False,
                    visual_before_url=base+f'?revision={audit(s).revision}',
                    visual_after_url=base+f'?after=true&revision={audit(s).revision}' if metadata.protected else None)
            page = next(p for p in audit(s).extraction.pages if p.page_number == d.page_number)
            return FindingDetail(finding=finding(record), before=page.text[max(0,d.start-120):d.start],
                candidate=page.text[d.start:min(d.end,d.start+240)], after=page.text[d.end:d.end+120],
                candidate_truncated=d.end-d.start > 240)

    @app.get('/api/documents/{identifier}/findings/{finding_id}/visual-crop')
    def face_crop(identifier:str,finding_id:str,after:bool=False,expected:int|None=Query(None,alias='revision',ge=0)):
        with lock:
            s=session(identifier);current=audit(s);record=record_for(s,finding_id)
            if getattr(record.effective_detection,'category',None)!='BIOMETRIC':raise HTTPException(404,'Visual finding not found.')
            if expected is not None:revision(s,expected)
            try:
                if current.extraction.visual.source_sha256!=source_hash(current.extraction.source_path):raise ValueError()
                if after:file_for(s)
                from app.engines.redaction.visual_artifacts import visual_crop
                data=visual_crop(current.extraction,s.result.artifact_result,record.effective_detection,after)
                return Response(data,media_type='image/png')
            except Exception:raise HTTPException(409,'The bounded visual preview is unavailable or changed.') from None

    @app.get("/api/documents/{identifier}/findings/{finding_id}/comparison", response_model=FindingComparison)
    def comparison(identifier: str, finding_id: str):
        with lock:
            s = session(identifier)
            record = record_for(s, finding_id)
            if getattr(record.effective_detection,'category',None)=='BIOMETRIC':
                return FindingComparison(finding_id=finding_id,redacted_context=None,replacement=None,
                    state=finding(record,s).review_status)
            output = s.result.redaction_result
            page = next((p for p in output.pages if p.page_number == record.effective_detection.page_number), None) if output else None
            if page is None or record.redacted_start is None or record.redacted_end is None:
                return FindingComparison(finding_id=finding_id, redacted_context=None, replacement=None, state=record.redaction_status)
            start, end = record.redacted_start, record.redacted_end
            return FindingComparison(finding_id=finding_id, redacted_context=page.text[max(0, start-120):min(len(page.text), end+120)][:480],
                                     replacement=page.text[start:end][:240], state=record.redaction_status)

    @app.get("/api/documents/{identifier}/source", response_model=SourceWindow)
    def source_window(identifier: str, location: int = Query(1, ge=1), start: int = Query(0, ge=0), length: int = Query(1600, ge=1, le=2000)):
        with lock:
            current = audit(session(identifier))
            page = next((p for p in current.extraction.pages if p.page_number == location), None)
            if page is None or start > len(page.text):
                raise HTTPException(422, "Source location or window is invalid.")
            end = min(start+length,len(page.text))
            highlights = [PreviewHighlight(finding_id=r.detection_id, start=max(start,r.effective_detection.start),
                end=min(end,r.effective_detection.end), decision=r.effective_decision) for r in current.records
                if r.effective_detection.page_number == location and r.effective_detection.start < end
                and start < r.effective_detection.end]
            return SourceWindow(location=location,start=start,total_characters=len(page.text),text=page.text[start:end],highlights=highlights)

    @app.post("/api/documents/{identifier}/feedback", response_model=DocumentState)
    def feedback(identifier: str, body: FeedbackRequest):
        with lock:
            s = session(identifier)
            revision(s, body.expected_revision)
            record = record_for(s, body.finding_id)
            return apply(s, ReviewerFeedback(body.action, body.reviewer_id, body.finding_id,
                reason=body.reason, expected_decision=record.effective_decision))

    @app.post("/api/documents/{identifier}/missed-pii", response_model=DocumentState)
    def missed(identifier: str, body: MissedRequest):
        with lock:
            s = session(identifier)
            revision(s,body.expected_revision)
            if body.entity_type in {'FACE','BIOMETRIC'}:
                raise HTTPException(422,'Face additions require a supported visual-region mapping, not text offsets.')
            if not 0 < body.end-body.start <= 1000:
                raise HTTPException(422, "Select between 1 and 1,000 source characters.")
            return apply(s,ReviewerFeedback("MISSED_PII",body.reviewer_id,page_number=body.location,
                original_start=body.start,original_end=body.end,entity_type=body.entity_type,reason=body.reason))

    @app.get("/api/documents/{identifier}/artifact")
    def artifact(identifier: str, inline: bool = False):
        with lock:
            s = session(identifier)
            path = file_for(s)
            return FileResponse(path,media_type=MIME[s.format],filename="private-review-copy."+s.format,
                content_disposition_type="inline" if inline and s.format=="pdf" else "attachment")

    @app.get("/api/documents/{identifier}/audit", response_model=AuditView)
    def audit_view(identifier: str):
        with lock:
            s = session(identifier)
            current = audit(s)
            events = [AuditEvent(action=getattr(e.feedback.action, "value", e.feedback.action), finding_id=e.detection_id,
                timestamp=e.feedback.timestamp, reviewer_id=e.feedback.reviewer_id,reason=e.feedback.reason,
                previous_decision=e.previous_decision,new_decision=e.new_decision) for e in current.feedback]
            return AuditView(summary=state(s).summary,events=events)

    @app.post("/api/documents/{identifier}/save", response_model=DocumentState)
    def save(identifier: str, body: SaveRequest):
        with lock:
            s = session(identifier)
            revision(s,body.expected_revision)
            saved = engine.save_audit(s.result,expected_revision=s.saved_revision)
            if saved.failure:
                raise HTTPException(409, "Audit save failed or the persisted revision changed.")
            s.result = saved
            s.saved_revision = audit(s).revision
            return state(s)

    @app.get("/api/saved-audits")
    def saved_audits():
        with lock:
            items=[]
            for path in sorted((root/"audits").glob("audit_*.json")):
                if path.is_symlink() or not re.fullmatch(r"audit_[0-9a-f]{64}\.json",path.name): continue
                document_id=path.stem.removeprefix("audit_")
                reference=next((k for k,v in saved_refs.items() if v==document_id),None)
                if reference is None:
                    reference=uuid4().hex
                    saved_refs[reference]=document_id
                items.append({"audit_reference":reference,"label":"Saved audit "+str(len(items)+1)})
            return items

    @app.post("/api/load-audit", response_model=DocumentState)
    def load(body: LoadRequest):
        with lock:
            document_id=saved_refs.get(body.audit_reference)
            if document_id is None: raise HTTPException(404,"Saved audit reference not found.")
            result=engine.load_audit(document_id)
            if result.failure or result.audit_result is None:
                raise HTTPException(409,"Saved audit cannot be restored or its original source is unavailable.")
            identifier=uuid4().hex
            kind=result.extraction_result.file_type
            s=ReviewSession(identifier,"Restored "+kind.upper()+" review",kind,result,result.audit_result.revision)
            sessions[identifier]=s
            return state(s)
    return app
