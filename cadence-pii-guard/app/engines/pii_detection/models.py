from dataclasses import dataclass
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


@dataclass
class PIIDetectionResult:
    source_path: Path
    filename: str
    detections: list[DetectedPII]
    rejected: list[DetectedPII]