import base64
from collections.abc import AsyncIterator
from typing import Literal
from uuid import UUID

from pydantic import Field, StringConstraints
from typing_extensions import Annotated

from app.schemas.common import Schema


class ProviderMessage(Schema):
    role: Literal["user", "assistant"]
    sanitized_text: Annotated[str, StringConstraints(strict=True, max_length=100_000)]


class ProviderArtifact(Schema):
    filename: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=255)]
    mime_type: Literal["image/png", "image/jpeg", "text/plain"]
    sanitized_text: Annotated[str, StringConstraints(strict=True, max_length=100_000)] | None = None
    sanitized_image_base64: Annotated[
        str, StringConstraints(strict=True, max_length=36_000_000)
    ] | None = None

    @classmethod
    def from_image(cls, filename: str, mime_type: str, content: bytes):
        if mime_type not in {"image/png", "image/jpeg"}:
            raise ValueError("Unsupported sanitized image type")
        return cls(
            filename=filename,
            mime_type=mime_type,
            sanitized_image_base64=base64.b64encode(content).decode("ascii"),
        )

    @classmethod
    def from_text(cls, filename: str, content: str):
        return cls(filename=filename, mime_type="text/plain", sanitized_text=content)

    def model_post_init(self, __context):
        has_text = self.sanitized_text is not None
        has_image = self.sanitized_image_base64 is not None
        if has_text == has_image:
            raise ValueError("Exactly one sanitized artifact representation is required")
        if self.mime_type == "text/plain" and not has_text:
            raise ValueError("Text artifact representation required")
        if self.mime_type != "text/plain" and not has_image:
            raise ValueError("Image artifact representation required")
        if has_image:
            try:
                base64.b64decode(self.sanitized_image_base64 or "", validate=True)
            except ValueError:
                raise ValueError("Invalid sanitized image representation") from None


class ProviderRequest(Schema):
    submission_id: UUID
    messages: list[ProviderMessage] = Field(min_length=1, max_length=100)
    artifacts: list[ProviderArtifact] = Field(max_length=5)


class ProviderDelta(Schema):
    text: Annotated[str, StringConstraints(strict=True, max_length=20_000)]


class LLMClient:
    async def stream(self, request: ProviderRequest) -> AsyncIterator[ProviderDelta]:
        raise NotImplementedError
