from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, field_validator

from app.schemas.common import Schema

AllowedMime = Literal[
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image/png",
    "image/jpeg",
]
Filename = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=255)
]


class UploadInitRequest(Schema):
    filename: Filename
    declared_mime: AllowedMime
    size_bytes: int = Field(strict=True, ge=1, le=25 * 1024 * 1024)


class AttachmentResponse(Schema):
    id: UUID
    filename: Filename
    mime_type: AllowedMime
    size_bytes: int = Field(strict=True, ge=1, le=25 * 1024 * 1024)
    state: Literal["pending_upload", "uploaded", "processing", "sanitized", "failed"]
    sanitized_download_url: str | None


class UploadGrant(Schema):
    method: Literal["PUT"] = "PUT"
    url: str
    headers: dict[str, str]
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class UploadInitResponse(Schema):
    attachment: AttachmentResponse
    upload: UploadGrant


class EmptyUploadCompletion(Schema):
    pass
