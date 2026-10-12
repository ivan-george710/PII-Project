"""Real PDF extraction, deterministic detection, and redaction integration.

The first test limits candidates to one email to isolate Engine 4 integration.
The second verifies full candidate accounting without claiming complete PII recall.
"""
import pytest
from reportlab.pdfgen import canvas
from presidio_analyzer import AnalyzerEngine

from app.engines.extraction.pdf import extract_text_pdf
from app.engines.pii_detection.engine import PIIDetectionEngine
from app.engines.pii_detection.recognizers import EmployeeIdRecognizer
from app.engines.redaction import RedactionEngine


@pytest.fixture(scope="module")
def analyzer():
    analyzer = AnalyzerEngine()
    analyzer.registry.add_recognizer(EmployeeIdRecognizer())
    return analyzer


def detection_engine(analyzer):
    return PIIDetectionEngine(analyzer=analyzer)


def pdf_source(tmp_path, text):
    path = tmp_path / "synthetic.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(50, 750, text)
    pdf.save()
    return extract_text_pdf(path)


def test_pdf_presidio_single_entity_redaction(tmp_path, analyzer):
    source = pdf_source(tmp_path, "Email: ada@example.com")

    class EmailOnlyAnalyzer:
        def analyze(self, **kwargs):
            return analyzer.analyze(**kwargs, entities=["EMAIL_ADDRESS"])

    detected = detection_engine(EmailOnlyAnalyzer()).detect(source)
    assert len(detected.detections) == 1
    result = RedactionEngine().redact(source, detected)
    assert result.full_text == "Email: [EMAIL_ADDRESS_001]"
    assert result.redaction_complete
    assert not result.safe_for_llm


def test_full_candidates_do_not_establish_pipeline_safety(tmp_path, analyzer):
    source = pdf_source(tmp_path, "Owner: Ada Example EMP-00001 ada@example.com")
    candidates = analyzer.analyze(text=source.full_text, language="en")
    detected = detection_engine(analyzer).detect(source)
    result = RedactionEngine().redact(source, detected)
    # Assess redaction only against records actually delivered by Engine 3.
    for record in result.redactions:
        page = result.pages[record.page_number - 1]
        assert page.text[record.redacted_start:record.redacted_end] == record.tag
    missing = len(candidates) - detected.disposition_count
    print(f"Presidio candidates={len(candidates)}, Engine 3 omitted={missing}, "
          f"applied redactions={result.applied_redaction_count}, "
          f"redaction_complete={result.redaction_complete}, safe_for_llm={result.safe_for_llm}")
    assert not result.safe_for_llm
    assert missing == 0
    assert detected.raw_candidate_count == len(candidates)
    assert result.applied_redaction_count >= 2
