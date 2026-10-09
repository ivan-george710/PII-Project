from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, StringConstraints, TypeAdapter

from app.schemas.common import Schema
from app.schemas.uploads import AllowedMime

SampleTitle = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=80)
]
SampleDescription = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=240)
]
SampleText = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=100_000)
]
SampleFilename = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=255)
]
SampleTag = Literal["text_pii", "scanned_text", "faces", "custom_rules"]


class DemoSampleBase(Schema):
    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, from_attributes=True, frozen=True
    )
    id: UUID
    title: SampleTitle
    description: SampleDescription
    tags: list[SampleTag] = Field(max_length=4)


class DemoMessageSample(DemoSampleBase):
    kind: Literal["message"]
    text: SampleText


class DemoFileSample(DemoSampleBase):
    kind: Literal["file"]
    filename: SampleFilename
    mime_type: AllowedMime
    size_bytes: int = Field(strict=True, ge=1, le=25 * 1024 * 1024)


DemoSample = Annotated[
    DemoMessageSample | DemoFileSample, Field(discriminator="kind")
]
demo_sample_adapter = TypeAdapter(DemoSample)


class DemoSampleList(Schema):
    items: list[DemoSample]


class DemoAttachmentRequest(Schema):
    client_request_id: UUID
