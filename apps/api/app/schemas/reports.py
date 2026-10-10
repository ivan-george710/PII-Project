from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictInt

from app.schemas.common import Schema


class SourceLocation(Schema):
    artifact_id: UUID | None = None
    kind: Literal["message", "native_text", "ocr", "face"]
    page_number: int | None = Field(default=None, ge=1)
    slide_number: int | None = Field(default=None, ge=1)
    source_ref: str | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    bbox: tuple[float, float, float, float] | None = None


class Finding(Schema):
    id: UUID
    rule_id: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    recognizer: str
    location: SourceLocation
    action: Literal["redacted", "allowed_disabled"]


class EventBatch(Schema):
    submission_id: UUID
    organization_id: UUID
    employee_id: UUID
    policy_version: StrictInt = Field(ge=1)
    occurred_at: datetime
    status: Literal["completed", "failed"]
    findings: list[Finding] = Field(default_factory=list)
    failure_code: str | None = None


class EmployeeSummary(Schema):
    id: UUID
    display_name: str
    email: str


class GroupedFinding(Schema):
    rule_id: str
    category: str
    count: StrictInt = Field(ge=1)
    action: Literal["redacted", "allowed_disabled"]
    locations: list[SourceLocation] = Field(default_factory=list)


class ReportEvent(Schema):
    id: UUID
    submission_id: UUID
    employee: EmployeeSummary
    occurred_at: datetime
    policy_version: StrictInt = Field(ge=1)
    status: Literal["completed", "failed"]
    failure_code: str | None = None
    findings: list[GroupedFinding] = Field(default_factory=list)
    total_findings: StrictInt = Field(ge=0)


class ReportCategoryCount(Schema):
    category: str
    count: StrictInt = Field(ge=0)


class ReportSummaryResponse(Schema):
    submission_count: StrictInt = Field(ge=0)
    failed_count: StrictInt = Field(ge=0)
    redacted_count: StrictInt = Field(ge=0)
    allowed_disabled_count: StrictInt = Field(ge=0)
    by_category: list[ReportCategoryCount] = Field(default_factory=list)


class ReportEventsPage(Schema):
    items: list[ReportEvent] = Field(default_factory=list)
    next_cursor: str | None = None
