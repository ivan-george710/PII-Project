"""Real selectable-PDF extraction and Presidio through reviewer regeneration."""
from reportlab.pdfgen import canvas

from app.engines.extraction.pdf import extract_text_pdf
from app.engines.pii_detection import PIIDetectionEngine
from app.engines.redaction import RedactionEngine
from app.engines.audit import AuditEngine, ReviewerFeedback


def test_employee_label_false_positive_and_missed_email(tmp_path):
    path = tmp_path / "synthetic-review.pdf"
    pdf = canvas.Canvas(str(path))
    lines = ["Employee: EMP-00001", "System label: John Smith", "Email: audit@example.invalid"]
    for i, text in enumerate(lines):
        pdf.drawString(50, 750 - i * 20, text)
    pdf.save()
    extraction = extract_text_pdf(path)
    detection = PIIDetectionEngine().detect(extraction)
    assert any(d.entity_type == "EMPLOYEE_ID" and d.text == "EMP-00001" for d in detection.detections)
    assert any(d.entity_type == "PERSON" and d.text == "John Smith" for d in detection.detections)
    assert not any(d.entity_type == "EMAIL_ADDRESS" and d.text == "audit@example.invalid"
                   for d in detection.detections)
    engine = AuditEngine(tmp_path / "private-audit")
    audit = engine.create_audit(extraction, detection, RedactionEngine().redact(extraction, detection))
    employee = next(r for r in audit.records if r.original_detection.entity_type == "EMPLOYEE_ID")
    label = next(r for r in audit.records if r.original_detection.text == "John Smith")
    audit = engine.apply_feedback(audit, ReviewerFeedback("CONFIRM_PII", "synthetic-reviewer", employee.detection_id))
    audit = engine.apply_feedback(audit, ReviewerFeedback("FALSE_POSITIVE", "synthetic-reviewer", label.detection_id,
                                                        reason="Known system label in this fixture"))
    start = extraction.pages[0].text.index("audit@example.invalid")
    audit = engine.apply_feedback(audit, ReviewerFeedback("MISSED_PII", "synthetic-reviewer", page_number=1,
        original_start=start, original_end=start + len("audit@example.invalid"), entity_type="EMAIL_ADDRESS"))
    assert "Employee: [EMPLOYEE_ID_001]" in audit.redaction_result.full_text
    assert "System label: John Smith" in audit.redaction_result.full_text
    assert "Email: [EMAIL_ADDRESS_001]" in audit.redaction_result.full_text
    assert [e.feedback.action.value for e in audit.feedback] == ["CONFIRM_PII", "FALSE_POSITIVE", "MISSED_PII"]
    assert audit.records[0].automated_decision == "CONFIRM"
    assert not audit.safe_for_llm
    engine.save_audit(audit)
    assert engine.load_audit(audit.document_id) == audit
