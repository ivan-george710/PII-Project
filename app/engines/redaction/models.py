"""Engine 4 output. All records and mappings are INTERNAL, sensitive audit data."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.engines.pii_detection.models import DetectedPII


class RedactionValidationError(ValueError):
    """Inputs do not describe the same, exact extracted document."""


@dataclass
class RedactedPage:
    page_number: int
    text: str
    extraction_method: str


@dataclass
class RedactionRecord:
    entity_type: str
    tag: str
    original_text: str
    page_number: int
    original_start: int
    original_end: int
    redacted_start: int
    redacted_end: int
    confidence: float
    recognizer: str | None
    detection_method: str | None
    validation_decision: str | None
    # Deprecated historical audit field; deterministic detection leaves it unset.
    llm_decision: str | None
    extraction_method: str
    source_block: int | None = None


@dataclass
class RedactionIssue:
    code: str
    page_number: int
    detection: "DetectedPII"
    blocking: bool = True
    superseded_by: "DetectedPII | None" = None


@dataclass
class RedactionResult:
    source_path: Path
    filename: str
    pages: list[RedactedPage]
    redactions: list[RedactionRecord] = field(default_factory=list)
    tag_mapping: dict[str, list["DetectedPII"]] = field(default_factory=dict)
    issues: list[RedactionIssue] = field(default_factory=list)
    rejected: list["DetectedPII"] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)

    @property
    def applied_redaction_count(self) -> int:
        return len(self.redactions)

    @property
    def redaction_complete(self) -> bool:
        return not any(issue.blocking for issue in self.issues)

    @property
    def safe_for_llm(self) -> bool:
        # Engine 3 supplies neither a coverage attestation nor extraction identity.
        # Successful span replacement alone cannot clear downstream submission.
        return False

    def to_text_payload(self) -> dict:
        """Allowlisted text-only view, never an audit serialization or clearance."""
        if not self.redaction_complete:
            raise RedactionValidationError("Unresolved findings block text export")
        return {
            "pages": [{"page_number": p.page_number, "text": p.text,
                       "extraction_method": p.extraction_method} for p in self.pages],
            "full_text": self.full_text,
            "safe_for_llm": self.safe_for_llm,
            "requires_coverage_review": True,
        }
