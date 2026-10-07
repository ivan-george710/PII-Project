from pathlib import Path

from app.engines.extraction.models import (
    ExtractedPage,
    ExtractionResult,
)

from app.engines.pii_detection import PIIDetectionEngine


def test_detect_cadence_pii():
    text = (
        "Policyowner: Miriam T. Achebe "
        "(EMP-38104), "
        "Author: Tobias Lindqvist "
        "(EMP-40522), "
        "t.lindqvist@cadencefg.com, "
        "+1 (212) 555-0188"
    )

    extraction_result = ExtractionResult(
        source_path=Path("test.pdf"),
        filename="test.pdf",
        file_type="pdf",
        pages=[
            ExtractedPage(
                page_number=1,
                text=text,
                extraction_method="text",
            )
        ],
    )

    result = PIIDetectionEngine().detect(
        extraction_result
    )

    detected = {
        (item.entity_type, item.text)
        for item in result.detections
    }

    assert ("EMPLOYEE_ID", "EMP-38104") in detected
    assert ("EMPLOYEE_ID", "EMP-40522") in detected
    assert ("EMAIL_ADDRESS", "t.lindqvist@cadencefg.com") in detected
    assert ("PHONE_NUMBER", "+1 (212) 555-0188") in detected
    