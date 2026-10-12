from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DetectedPII:
    entity_type: str
    text: str
    start: int
    end: int
    confidence: float
    detection_method: str
    recognizer: str
    page_number: int
    source_block: int | None = None

    validation_decision: str | None = None
    validation_reason: str | None = None
    # Deprecated: retained only for historical audit/cache and Engine 4 compatibility.
    # The deterministic engine never populates these fields.
    llm_decision: str | None = field(default=None, metadata={"deprecated": True})
    llm_reason: str | None = field(default=None, metadata={"deprecated": True})
    final_decision: str | None = None


@dataclass
class PIIDetectionResult:
    source_path: Path
    filename: str
    detections: list[DetectedPII]
    rejected: list[DetectedPII]
    review: list[DetectedPII] = field(default_factory=list)
    raw_candidate_count: int = 0
    pages_analyzed: list[int] = field(default_factory=list)

    @property
    def disposition_count(self) -> int:
        return len(self.detections) + len(self.rejected) + len(self.review)

    @property
    def diagnostics(self) -> dict[str, int]:
        """Aggregate counts only: no sensitive text or source filenames."""
        return {"raw_candidates": self.raw_candidate_count,
                "confirmed": len(self.detections), "rejected": len(self.rejected),
                "review": len(self.review), "pages_analyzed": len(self.pages_analyzed)}

    @property
    def safe_for_llm(self) -> bool:
        # Complete disposition is not evidence of complete PII recall.
        return False


class DetectionProcessingError(RuntimeError):
    """An analysis/input failure prevents a usable complete detection result."""
