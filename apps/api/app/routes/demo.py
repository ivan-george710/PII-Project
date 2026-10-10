from uuid import UUID
import os

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth.permissions import require_employee
from app.db.session import get_db
from app.schemas.common import ApiError
from app.schemas.demo import DemoAttachmentRequest, DemoSampleList
from app.schemas.uploads import AttachmentResponse
from app.services.demo import create_sample_attachment, list_samples
from app.storage.files import LocalFileStorage, storage_for_request

router = APIRouter(prefix="/api/v1/demo/samples", tags=["Demo samples"])


def _enabled() -> None:
    from app.config import get_settings

    settings = get_settings()
    enabled = os.environ.get("SHOW_DEMO_SAMPLES", "false").lower() == "true"
    if settings.app_env == "production" or not enabled:
        raise ApiError(404, "NOT_FOUND", "Samples unavailable")


@router.get("", response_model=DemoSampleList)
def catalog(identity=Depends(require_employee)):
    _enabled()
    return {"items": list_samples()}


@router.post("/{sample_id}/attachments", response_model=AttachmentResponse, status_code=201)
def attach_sample(
    sample_id: UUID,
    body: DemoAttachmentRequest,
    response: Response,
    identity=Depends(require_employee),
    db: Session = Depends(get_db),
    storage: LocalFileStorage = Depends(storage_for_request),
):
    _enabled()
    item, created = create_sample_attachment(
        db,
        storage,
        identity.organization_id,
        identity.user_id,
        sample_id,
        body.client_request_id,
    )
    if not created:
        response.status_code = 200
    return AttachmentResponse(
        id=item.id,
        filename=item.filename,
        mime_type=item.mime_type,
        size_bytes=item.size_bytes,
        state=item.state,
        sanitized_download_url=None,
    )
