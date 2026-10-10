from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    PrivateAttr,
    StringConstraints,
    field_validator,
    model_validator,
)

from pii_guard.rules.builtins import BUILTIN_RULE_IDS, RuleId


class EngineBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


TrimmedName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
]
PatternText = Annotated[str, StringConstraints(min_length=1, max_length=512)]
Filename = Annotated[str, StringConstraints(min_length=1, max_length=255)]
MimeType = Annotated[str, StringConstraints(min_length=1)]
RuleIdString = Annotated[str, StringConstraints(min_length=1)]
Category = Annotated[str, StringConstraints(min_length=1)]
RecognizerName = Annotated[str, StringConstraints(min_length=1)]
SourceRef = Annotated[str, StringConstraints(min_length=1)]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class CustomRule(EngineBaseModel):
    id: UUID
    name: TrimmedName
    kind: Literal["exact", "regex"]
    pattern: PatternText
    case_sensitive: StrictBool
    enabled: StrictBool


class PolicySnapshot(EngineBaseModel):
    organization_id: UUID
    version: Annotated[StrictInt, Field(ge=1)]
    builtins: dict[RuleId, StrictBool]
    custom_rules: Annotated[list[CustomRule], Field(max_length=100)]

    @model_validator(mode="after")
    def validate_policy(self) -> PolicySnapshot:
        expected = set(BUILTIN_RULE_IDS)
        actual = set(self.builtins)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            details = []
            if missing:
                details.append(f"missing built-ins: {', '.join(missing)}")
            if extra:
                details.append(f"unknown built-ins: {', '.join(extra)}")
            raise ValueError("; ".join(details) or "invalid built-ins")

        custom_ids = [rule.id for rule in self.custom_rules]
        if len(custom_ids) != len(set(custom_ids)):
            raise ValueError("custom rule IDs must be unique")

        return self


class ArtifactInput(EngineBaseModel):
    id: UUID
    filename: Filename
    source_path: Path
    declared_mime: MimeType | None

    @field_validator("filename")
    @classmethod
    def filename_must_be_basename(cls, value: str) -> str:
        if Path(value).name != value or value in {".", ".."}:
            raise ValueError("filename must be a basename")
        return value


class SanitizeRequest(EngineBaseModel):
    submission_id: UUID
    text: Annotated[str, StringConstraints(max_length=100000)]
    artifacts: Annotated[list[ArtifactInput], Field(max_length=5)]
    policy: PolicySnapshot
    output_dir: Path

    @model_validator(mode="after")
    def require_text_or_artifact(self) -> SanitizeRequest:
        if not self.text.strip() and not self.artifacts:
            raise ValueError("request must include non-empty text or at least one artifact")
        return self


BBox = tuple[
    Annotated[float, Field(ge=0, le=1)],
    Annotated[float, Field(ge=0, le=1)],
    Annotated[float, Field(ge=0, le=1)],
    Annotated[float, Field(ge=0, le=1)],
]


class SourceLocation(EngineBaseModel):
    artifact_id: UUID | None
    kind: Literal["message", "native_text", "ocr", "face"]
    page_number: Annotated[StrictInt, Field(gt=0)] | None
    slide_number: Annotated[StrictInt, Field(gt=0)] | None
    source_ref: SourceRef | None
    start: Annotated[StrictInt, Field(ge=0)] | None
    end: Annotated[StrictInt, Field(ge=0)] | None
    bbox: BBox | None

    @model_validator(mode="after")
    def validate_location_boundaries(self) -> SourceLocation:
        if self.kind == "message" and self.artifact_id is not None:
            raise ValueError("message locations must not include artifact_id")
        if self.kind != "message" and self.artifact_id is None:
            raise ValueError("artifact locations require artifact_id")

        if self.kind == "face":
            if self.bbox is None:
                raise ValueError("face locations require bbox")
        else:
            if self.start is None or self.end is None:
                raise ValueError("text locations require start and end")
            if self.end <= self.start:
                raise ValueError("end must be greater than start")

        if self.bbox is not None:
            x, y, width, height = self.bbox
            if width <= 0 or height <= 0:
                raise ValueError("bbox width and height must be positive")
            if x + width > 1 or y + height > 1:
                raise ValueError("bbox must stay within normalized bounds")

        return self


class Finding(EngineBaseModel):
    id: UUID
    rule_id: RuleIdString
    category: Category
    confidence: Annotated[float, Field(ge=0, le=1)]
    recognizer: RecognizerName
    location: SourceLocation
    action: Literal["redacted", "allowed_disabled"]


class SanitizedArtifact(EngineBaseModel):
    artifact_id: UUID
    filename: Filename
    mime_type: MimeType
    output_path: Path
    size_bytes: Annotated[StrictInt, Field(gt=0)]
    sha256: Sha256Hex
    format_changed: StrictBool

    @field_validator("filename")
    @classmethod
    def filename_must_be_basename(cls, value: str) -> str:
        if Path(value).name != value or value in {".", ".."}:
            raise ValueError("filename must be a basename")
        return value


class SanitizeResult(EngineBaseModel):
    _artifact_texts: dict[UUID, str] = PrivateAttr(default_factory=dict)
    submission_id: UUID
    policy_version: Annotated[StrictInt, Field(gt=0)]
    sanitized_text: str
    artifacts: list[SanitizedArtifact]
    findings: list[Finding]
    warnings: list[str]


class ExtractedTextBlock(EngineBaseModel):
    text: str
    location: SourceLocation
    extraction_method: Literal["native_text", "ocr"]
    confidence: Annotated[float, Field(ge=0, le=1)] | None = None

    @model_validator(mode="after")
    def validate_extracted_block(self) -> ExtractedTextBlock:
        if self.location.kind != self.extraction_method:
            raise ValueError("extraction method must match location kind")
        if self.location.start != 0 or self.location.end != len(self.text):
            raise ValueError("extracted block spans must cover block-local text")
        if not self.location.source_ref:
            raise ValueError("extracted blocks require stable source references")
        if self.extraction_method == "ocr" and self.location.bbox is None:
            raise ValueError("OCR blocks require normalized coordinates")
        return self


class ExtractedArtifact(EngineBaseModel):
    artifact_id: UUID
    filename: Filename
    mime_type: MimeType
    file_type: Literal["pdf", "docx", "pptx", "png", "jpeg"]
    blocks: list[ExtractedTextBlock]
    warnings: list[str]

    @model_validator(mode="after")
    def validate_extracted_artifact(self) -> ExtractedArtifact:
        if any(block.location.artifact_id != self.artifact_id for block in self.blocks):
            raise ValueError("block artifact identity must match extracted artifact")
        refs = [block.location.source_ref for block in self.blocks]
        if len(refs) != len(set(refs)):
            raise ValueError("extracted source references must be unique")
        return self

    @property
    def full_text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text)
