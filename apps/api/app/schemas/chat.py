from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictBool, StringConstraints, field_validator, model_validator

from app.schemas.common import Schema
from app.schemas.uploads import AttachmentResponse

ChatTitle = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)
]
MessageText = Annotated[str, StringConstraints(strict=True, max_length=100_000)]
Cursor = Annotated[str, StringConstraints(strict=True, max_length=512)]


class ConversationCreate(Schema):
    title: ChatTitle = "New chat"


class ConversationResponse(Schema):
    id: UUID
    title: ChatTitle
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ConversationsPage(Schema):
    items: list[ConversationResponse]
    next_cursor: Cursor | None


class MessageResponse(Schema):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    text: MessageText
    attachment_ids: list[UUID] = Field(max_length=5)
    state: Literal["processing", "completed", "failed", "cancelled"]
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class MessagesPage(Schema):
    items: list[MessageResponse]
    next_cursor: Cursor | None


class MessageSubmission(Schema):
    text: MessageText
    attachment_ids: list[UUID] = Field(max_length=5)
    client_request_id: UUID

    @field_validator("attachment_ids")
    @classmethod
    def unique_attachments(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Attachment IDs must be unique")
        return value

    @field_validator("text")
    @classmethod
    def has_input(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value


class MessageSubmissionRequest(Schema):
    text: MessageText = ""
    attachment_ids: list[UUID] = Field(max_length=5)
    client_request_id: UUID

    @field_validator("attachment_ids")
    @classmethod
    def unique_attachments(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Attachment IDs must be unique")
        return value

    @model_validator(mode="after")
    def has_input(self):
        if not self.text.strip() and not self.attachment_ids:
            raise ValueError("Text or an attachment is required")
        return self


class MessageSubmissionValidated(MessageSubmissionRequest):
    @field_validator("text")
    @classmethod
    def has_input(cls, value: str, info) -> str:
        if not value.strip() and not info.data.get("attachment_ids"):
            raise ValueError("Text or an attachment is required")
        return value


class MessageSubmissionResponse(Schema):
    id: UUID
    state: Literal["processing", "completed", "failed", "cancelled"]


class StreamStage(StrEnum):
    SANITIZING = "sanitizing"


class ProcessingEvent(Schema):
    type: Literal["processing"] = "processing"
    submission_id: UUID
    stage: Literal["sanitizing"] = "sanitizing"


class SanitizedEvent(Schema):
    type: Literal["sanitized"] = "sanitized"
    submission_id: UUID
    user_message: MessageResponse
    attachments: list[AttachmentResponse]
    policy_version: str


class DeltaEvent(Schema):
    type: Literal["delta"] = "delta"
    submission_id: UUID
    assistant_message_id: UUID
    sequence: Annotated[int, Field(strict=True, ge=1)]
    text: str


class DoneEvent(Schema):
    type: Literal["done"] = "done"
    submission_id: UUID
    assistant_message: MessageResponse


class ErrorEvent(Schema):
    type: Literal["error"] = "error"
    submission_id: UUID
    code: str
    message: str
    retryable: StrictBool


StreamEvent = Annotated[
    ProcessingEvent | SanitizedEvent | DeltaEvent | DoneEvent | ErrorEvent,
    Field(discriminator="type"),
]
