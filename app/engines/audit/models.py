"""Internal audit objects contain PII. Use sanitized_summary for public display."""
from dataclasses import dataclass, field
from enum import Enum

from app.engines.extraction.models import ExtractionResult
from app.engines.pii_detection.models import DetectedPII, PIIDetectionResult
from app.engines.redaction.models import RedactionResult


class AuditValidationError(ValueError):
    pass


class FeedbackConflictError(AuditValidationError):
    pass


class AuditStorageError(RuntimeError):
    pass


class ReviewAction(str, Enum):
    CONFIRM_PII = "CONFIRM_PII"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    MISSED_PII = "MISSED_PII"


@dataclass(frozen=True)
class ReviewerFeedback:
    action: ReviewAction | str
    reviewer_id: str
    detection_id: str | None = None
    page_number: int | None = None
    original_start: int | None = None
    original_end: int | None = None
    entity_type: str | None = None
    reason: str | None = None
    timestamp: str | None = None
    expected_decision: str | None = None


@dataclass(frozen=True)
class FeedbackEvent:
    event_id: str
    detection_id: str
    feedback: ReviewerFeedback
    previous_decision: str | None
    new_decision: str


@dataclass
class AuditRecord:
    detection_id: str
    document_id: str
    original_detection: DetectedPII
    effective_detection: DetectedPII
    automated_decision: str | None
    effective_decision: str
    redaction_status: str
    tag: str | None = None
    superseded_by: str | None = None
    redacted_start: int | None = None
    redacted_end: int | None = None
    extraction_method: str | None = None
    corrected: bool = False


@dataclass
class ReviewItem:
    item_id: str
    category: str
    page_number: int
    detection_ids: list[str]
    explanation: str


@dataclass
class AuditResult:
    document_id: str
    extraction: ExtractionResult
    original_detection_result: PIIDetectionResult
    original_redaction_result: RedactionResult
    effective_detection_result: PIIDetectionResult
    redaction_result: RedactionResult
    records: list[AuditRecord]
    review_queue: list[ReviewItem]
    counts: dict[str, int]
    feedback: list[FeedbackEvent] = field(default_factory=list)
    revision: int = 0
    baseline_fingerprint: str = ""
    visual_records: list = field(default_factory=list)
    visual_result: object | None = None

    @property
    def human_review_complete(self) -> bool:
        """No known unresolved issues; never a claim of complete discovery."""
        return not self.review_queue

    @property
    def coverage_verified(self) -> bool:
        return False

    @property
    def downstream_export_permitted(self) -> bool:
        return False

    @property
    def safe_for_llm(self) -> bool:
        return False

    def sanitized_summary(self) -> dict:
        from .reporter import sanitized_summary
        return sanitized_summary(self)
