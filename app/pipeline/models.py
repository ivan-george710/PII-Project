"""Internal pipeline state; only sanitized_summary crosses the review boundary."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.engines.file_intelligence.models import FileMetadata
from app.engines.extraction.models import ExtractionResult
from app.engines.pii_detection.models import PIIDetectionResult
from app.engines.redaction.models import RedactionResult
from app.engines.audit import AuditResult, ReviewItem
from app.engines.redaction.artifacts import ArtifactResult


class ProcessingStatus(str, Enum):
    PROCESSING_FAILED = "PROCESSING_FAILED"
    PROCESSED_REVIEW_REQUIRED = "PROCESSED_REVIEW_REQUIRED"
    PROCESSED_NO_KNOWN_REVIEW = "PROCESSED_NO_KNOWN_REVIEW"


@dataclass(frozen=True)
class PipelineFailure:
    stage: str
    code: str
    message: str


STAGES = {"file_intelligence", "extraction", "detection", "redaction", "audit",
          "feedback", "persistence_save", "persistence_load", "artifact_redaction", "artifact_verification", "face_detection"}


@dataclass
class PipelineResult:
    source_path: Path | None = None
    file_intelligence_result: FileMetadata | None = None
    extraction_result: ExtractionResult | None = None
    detection_result: PIIDetectionResult | None = None
    redaction_result: RedactionResult | None = None
    audit_result: AuditResult | None = None
    processing_status: ProcessingStatus = ProcessingStatus.PROCESSING_FAILED
    stage_timings: dict[str, float] = field(default_factory=dict)
    total_runtime: float = 0.0
    failure: PipelineFailure | None = None
    persisted_path: Path | None = None
    artifact_result: ArtifactResult | None = None

    @property
    def document_id(self):
        return self.audit_result.document_id if self.audit_result else None

    @property
    def review_queue(self) -> list[ReviewItem]:
        return self.audit_result.review_queue if self.audit_result else []

    @property
    def effective_detection_result(self):
        return self.audit_result.effective_detection_result if self.audit_result else None

    @property
    def internal_preview(self):
        return self.redaction_result.full_text if self.redaction_result else None

    @property
    def coverage_status(self):
        return "COVERAGE_UNVERIFIED"

    @property
    def coverage_verified(self):
        return False

    @property
    def safe_for_llm(self):
        return False

    @property
    def downstream_export_permitted(self):
        return False

    def sanitized_summary(self) -> dict:
        # No exception text, source identity, preview, tags, reviewer reasons or IDs.
        return {
            "processing_status": self.processing_status.value,
            "coverage_status": self.coverage_status,
            "coverage_verified": False,
            "safe_for_llm": False,
            "downstream_export_permitted": False,
            "failure": ({"stage": self.failure.stage, "code": self.failure.code}
                        if self.failure else None),
            "stage_timings_seconds": {s: self.stage_timings[s] for s in sorted(STAGES)
                                      if s in self.stage_timings},
            "total_runtime_seconds": self.total_runtime,
            "extraction_completed": self.extraction_result is not None,
            "detection_completed": self.detection_result is not None,
            "text_redaction_completed": self.redaction_result is not None,
            "human_review_complete": self.audit_result.human_review_complete if self.audit_result else False,
            "artifact": self.artifact_result.sanitized_summary() if self.artifact_result else None,
            "audit": self.audit_result.sanitized_summary() if self.audit_result else None,
            "visual_privacy": self.audit_result.visual_result.summary() if self.audit_result and self.audit_result.visual_result
                              else self.extraction_result.visual.summary() if self.extraction_result and self.extraction_result.visual else None,
        }
