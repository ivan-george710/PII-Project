from pathlib import Path

from presidio_analyzer import AnalyzerEngine

from app.engines.extraction.models import ExtractionResult
from .models import DetectedPII, PIIDetectionResult
from .recognizers import EmployeeIdRecognizer
from .validation import validate_detection


class PIIDetectionEngine:
    def __init__(self) -> None:
        self.analyzer = AnalyzerEngine()

        self.employee_id_recognizer = EmployeeIdRecognizer()

        self.analyzer.registry.add_recognizer(
            self.employee_id_recognizer
        )

    def detect(
        self,
        extraction_result: ExtractionResult,
    ) -> PIIDetectionResult:

        detections: list[DetectedPII] = []
        rejected: list[DetectedPII] = []

        for page in extraction_result.pages:
            if not page.text.strip():
                continue

            results = self.analyzer.analyze(
                text=page.text,
                language="en",
            )

            for result in results:
                detected_text = page.text[result.start:result.end]

                detection = DetectedPII(
    entity_type=result.entity_type,
    text=detected_text,
    start=result.start,
    end=result.end,
    confidence=result.score,
    detection_method=self._get_detection_method(result),
    recognizer=self._get_recognizer_name(result),
    page_number=page.page_number,
)

                is_valid, _ = validate_detection(detection)

                if is_valid:
                    detections.append(detection)
                else:
                    rejected.append(detection)

        return PIIDetectionResult(
    source_path=extraction_result.source_path,
    filename=extraction_result.filename,
    detections=detections,
    rejected=rejected,
)

    @staticmethod
    def _get_recognizer_name(result) -> str:
        metadata = result.recognition_metadata or {}

        return metadata.get(
            "recognizer_name",
            "unknown",
        )

    @staticmethod
    def _get_detection_method(result) -> str:
        recognizer_name = PIIDetectionEngine._get_recognizer_name(result)

        if recognizer_name == "SpacyRecognizer":
            return "nlp"

        if recognizer_name == "CadenceEmployeeIdRecognizer":
            return "custom_pattern"

        return "pattern"