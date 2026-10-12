from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StageState(BaseModel):
    name: str
    state: Literal["Pending", "Completed", "Failed"]
    seconds: float | None = None


class DocumentState(BaseModel):
    document_session_id: str
    format: str
    revision: int | None
    saved_revision: int | None
    artifact_available: bool
    summary: dict
    stages: list[StageState]
    issue_message: str | None = None


class Finding(BaseModel):
    finding_id: str
    entity_type: str
    location: int
    confidence: float
    recognizer: str
    automated_decision: str | None
    effective_decision: str
    review_status: str
    corrected: bool
    kind: Literal['TEXT','VISUAL'] = 'TEXT'
    locations: list[int] = Field(default_factory=list)
    biometric_action: str | None = None
    protected: bool = False
    visual_location_label: str | None = None


class FindingList(BaseModel):
    items: list[Finding]
    total: int
    entities: list[str]
    locations: list[int]


class FindingDetail(BaseModel):
    finding: Finding
    before: str
    candidate: str
    after: str
    candidate_truncated: bool
    visual_before_url: str | None = None
    visual_after_url: str | None = None


class FindingComparison(BaseModel):
    """Bounded actual Engine 4 output, never a full-document preview or clearance."""
    finding_id: str
    redacted_context: str | None = Field(max_length=480)
    replacement: str | None = Field(max_length=240)
    state: str


class PreviewHighlight(BaseModel):
    finding_id: str
    start: int
    end: int
    decision: str


class SourceWindow(BaseModel):
    location: int
    start: int
    total_characters: int
    text: str
    highlights: list[PreviewHighlight]


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)
    action: Literal["CONFIRM_PII", "FALSE_POSITIVE"]
    finding_id: str = Field(pattern=r"^[DHV]\d{6,}$")
    reviewer_id: str = Field(default="local-reviewer", min_length=1, max_length=80)
    reason: str | None = Field(default=None, max_length=1000)


class MissedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)
    location: int = Field(ge=1, strict=True)
    start: int = Field(ge=0, strict=True)
    end: int = Field(ge=1, strict=True)
    entity_type: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$", max_length=60)
    reviewer_id: str = Field(default="local-reviewer", min_length=1, max_length=80)
    reason: str | None = Field(default=None, max_length=1000)


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)


class LoadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audit_reference: str = Field(pattern=r"^[0-9a-f]{32}$")


class ReviewIdentity(BaseModel):
    display_name: str
    location_kind: str
    location_count: int


class AuditEvent(BaseModel):
    action: str
    finding_id: str
    timestamp: str
    reviewer_id: str
    reason: str | None
    previous_decision: str | None
    new_decision: str


class AuditView(BaseModel):
    summary: dict
    events: list[AuditEvent]
