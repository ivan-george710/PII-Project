import hashlib
import json
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing_extensions import Annotated

from app.db.models.attachment import Attachment
from app.schemas.common import ApiError, Schema
from app.schemas.demo import (
    DemoFileSample,
    DemoMessageSample,
    DemoSample,
    demo_sample_adapter,
)
from app.storage.files import LocalFileStorage

MANIFEST = Path(__file__).resolve().parents[4] / "demo" / "sample_documents" / "manifest.json"


class ManifestAsset(Schema):
    path: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=255)]
    sha256: Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]


class ManifestEntry(Schema):
    id: UUID
    kind: Literal["message", "file"]
    title: str
    description: str
    tags: list[str]
    text: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    asset: ManifestAsset | None = None


def _read_manifest() -> tuple[list[ManifestEntry], dict[UUID, bytes]]:
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        entries = [ManifestEntry.model_validate(item) for item in data["samples"]]
    except (OSError, ValueError, KeyError, TypeError):
        raise ApiError(503, "SAMPLES_UNAVAILABLE", "Test samples are unavailable") from None
    root = MANIFEST.parent.resolve()
    result, assets = [], {}
    for entry in entries:
        if entry.kind == "message":
            result.append(
                demo_sample_adapter.validate_python(
                    {
                        "id": entry.id,
                        "kind": "message",
                        "title": entry.title,
                        "description": entry.description,
                        "tags": entry.tags,
                        "text": entry.text,
                    }
                )
            )
            continue
        if not entry.asset or not entry.filename or not entry.mime_type or not entry.size_bytes:
            raise ApiError(503, "SAMPLES_UNAVAILABLE", "Test samples are unavailable")
        path = (root / entry.asset.path).resolve()
        if root not in path.parents or not path.is_file():
            raise ApiError(503, "SAMPLES_UNAVAILABLE", "Test samples are unavailable")
        try:
            content = path.read_bytes()
        except OSError:
            raise ApiError(503, "SAMPLES_UNAVAILABLE", "Test samples are unavailable") from None
        if len(content) != entry.size_bytes or hashlib.sha256(content).hexdigest() != entry.asset.sha256:
            raise ApiError(503, "SAMPLES_UNAVAILABLE", "Test samples are unavailable")
        result.append(
            demo_sample_adapter.validate_python(
                {
                    "id": entry.id,
                    "kind": "file",
                    "title": entry.title,
                    "description": entry.description,
                    "tags": entry.tags,
                    "filename": entry.filename,
                    "mime_type": entry.mime_type,
                    "size_bytes": entry.size_bytes,
                }
            )
        )
        assets[entry.id] = content
    return result, assets


def list_samples() -> list[DemoSample]:
    return _read_manifest()[0]


def create_sample_attachment(
    db: Session,
    storage: LocalFileStorage,
    organization_id: UUID,
    employee_id: UUID,
    sample_id: UUID,
    client_request_id: UUID,
) -> tuple[Attachment, bool]:
    sample, assets = _read_manifest()
    selected = next((item for item in sample if item.id == sample_id), None)
    if selected is None:
        raise ApiError(404, "NOT_FOUND", "Sample unavailable")
    if not isinstance(selected, DemoFileSample):
        raise ApiError(422, "INVALID_SAMPLE", "Only file samples can be attached")
    existing = db.scalar(
        select(Attachment).where(
            Attachment.employee_id == employee_id,
            Attachment.sample_id == sample_id,
            Attachment.sample_request_id == client_request_id,
        )
    )
    if existing:
        return existing, False
    content = assets[sample_id]
    attachment_id = uuid4()
    storage.receive_upload(organization_id, employee_id, attachment_id, content)
    original_key, size, digest = storage.verify_upload(
        organization_id,
        employee_id,
        attachment_id,
        selected.filename,
        selected.mime_type,
        selected.size_bytes,
    )
    item = Attachment(
        id=attachment_id,
        organization_id=organization_id,
        employee_id=employee_id,
        conversation_id=None,
        original_key=original_key,
        sanitized_key=None,
        filename=selected.filename,
        mime_type=selected.mime_type,
        size_bytes=size,
        content_hash=digest,
        sample_id=sample_id,
        sample_request_id=client_request_id,
        state="uploaded",
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Attachment).where(
                Attachment.employee_id == employee_id,
                Attachment.sample_id == sample_id,
                Attachment.sample_request_id == client_request_id,
            )
        )
        if existing:
            storage.delete(original_key)
            return existing, False
        storage.delete(original_key)
        raise ApiError(503, "SAMPLES_UNAVAILABLE", "Test sample could not be attached") from None
    db.refresh(item)
    return item, True
