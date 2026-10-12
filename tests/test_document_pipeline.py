"""Pipeline contracts, failure boundaries and real native-PDF integration."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from reportlab.pdfgen import canvas

from app.pipeline import DocumentPipeline, ProcessingStatus
from app.engines.file_intelligence.models import FileMetadata
from app.engines.extraction import ExtractionEngine, ExtractionResult, ExtractedPage
from app.engines.extraction.ocr import OCREngine
from app.engines.pii_detection.models import DetectedPII, PIIDetectionResult
from app.engines.redaction import RedactionEngine
from app.engines.audit import AuditEngine, ReviewerFeedback
from app.engines.redaction.artifacts import ArtifactResult
from app.engines.visual_detection.models import VisualInspection
from app.engines.extraction.office import source_hash


def stub_artifacts():
    return SimpleNamespace(redact=lambda *a: ArtifactResult(format="pdf", redaction_completed=True,
        verification_completed=True, reopened=True, supported_content_verified=True, known_review_complete=True),
        verify=lambda e,r,a:a)


def fixture_pipeline(tmp_path, *, empty=False):
    path = tmp_path / "private-source.pdf"
    path.write_bytes(b"synthetic input for injected engines")
    text = "Ada Example | Brightwell | missing@example.invalid"
    extraction = ExtractionResult(path, path.name, "pdf", [ExtractedPage(1, text, "text")])
    metadata = FileMetadata(path, path.name, ".pdf", "application/pdf", "pdf", "text")
    def finding(value, decision):
        start = text.index(value)
        return DetectedPII("PERSON", value, start, start + len(value), .9, "pattern", "Synthetic", 1,
            validation_decision="AMBIGUOUS" if decision == "REVIEW" else decision,
            validation_reason="private reason", final_decision=decision)
    detection = PIIDetectionResult(path, path.name,
        [] if empty else [finding("Ada Example", "CONFIRM")], [],
        [] if empty else [finding("Brightwell", "REVIEW")], 0 if empty else 2, [1])
    calls = []
    def invoke(name, value, *args):
        calls.append((name, args))
        return value
    pipeline = DocumentPipeline(
        file_intelligence=SimpleNamespace(analyze=lambda *a: invoke("file_intelligence", metadata, *a)),
        extraction=SimpleNamespace(extract=lambda *a: invoke("extraction", extraction, *a)),
        detection=SimpleNamespace(detect=lambda *a: invoke("detection", detection, *a)),
        redaction=SimpleNamespace(redact=lambda *a: invoke("redaction", RedactionEngine().redact(*a), *a)),
        # This contract fixture deliberately contains no real PDF bytes. Inject
        # its visual result just like its classification/extraction results.
        visual_detection=SimpleNamespace(inspect=lambda e:VisualInspection(source_hash(e.source_path))),
        audit=AuditEngine(tmp_path / "private-audit"), artifacts=stub_artifacts())
    create = pipeline.audit.create_audit
    pipeline.audit.create_audit = lambda *a: invoke("audit", create(*a), *a)
    return pipeline, path, extraction, detection, calls


def test_order_actual_outputs_counts_and_sanitization(tmp_path):
    p, path, extraction, detection, calls = fixture_pipeline(tmp_path)
    result = p.process(path)
    assert [c[0] for c in calls] == ["file_intelligence", "extraction", "detection", "redaction", "audit"]
    assert calls[1][1] == (path,)
    assert calls[2][1][0] is extraction
    assert calls[3][1][0] is extraction and calls[3][1][1] is detection
    assert calls[4][1][2] is result.redaction_result
    assert result.processing_status == ProcessingStatus.PROCESSED_REVIEW_REQUIRED
    assert len(result.review_queue) == 1
    assert result.audit_result.counts["raw_detection_count"] == 2
    assert result.audit_result.counts["applied_redactions"] == 1
    assert set(result.stage_timings) == {c[0] for c in calls} | {"artifact_redaction", "artifact_verification", "face_detection"}
    assert all(t >= 0 for t in result.stage_timings.values())
    assert result.total_runtime >= sum(result.stage_timings.values())
    summary = json.dumps(result.sanitized_summary())
    for secret in (str(path), path.name, "Ada", "Brightwell", "missing@", "private reason", result.document_id):
        assert secret not in summary
    assert not result.safe_for_llm and not result.downstream_export_permitted
    assert result.coverage_status == "COVERAGE_UNVERIFIED"


@pytest.mark.parametrize("stage,method", [("file_intelligence", "analyze"), ("extraction", "extract"),
    ("detection", "detect"), ("redaction", "redact"), ("audit", "create_audit")])
def test_stage_failure_stops_downstream_and_hides_exception(tmp_path, stage, method, capsys):
    p, path, _, _, calls = fixture_pipeline(tmp_path)
    def fail(*args):
        raise RuntimeError("SECRET vendor error private@example.com")
    setattr(getattr(p, stage), method, fail)
    result = p.process(path)
    stages = ["file_intelligence", "extraction", "detection", "redaction", "audit"]
    assert [c[0] for c in calls] == stages[:stages.index(stage)]
    assert result.failure.stage == stage
    assert result.processing_status == ProcessingStatus.PROCESSING_FAILED
    assert stage in result.stage_timings
    assert "SECRET" not in json.dumps(result.sanitized_summary())
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stage,method", [("file_intelligence", "analyze"), ("extraction", "extract"),
    ("detection", "detect"), ("redaction", "redact"), ("audit", "create_audit")])
def test_invalid_engine_result_is_failure(tmp_path, stage, method):
    p, path, *_ = fixture_pipeline(tmp_path)
    setattr(getattr(p, stage), method, lambda *a: None)
    assert p.process(path).failure.stage == stage


@pytest.mark.parametrize("kind", ["image"])
def test_recognized_unimplemented_format(tmp_path, kind):
    p, path, *_ = fixture_pipeline(tmp_path)
    m = p.file_intelligence.analyze(str(path))
    p.file_intelligence.analyze = lambda _: replace(m, file_type=kind)
    p.extraction.extract = Mock(side_effect=AssertionError("must not extract"))
    result = p.process(path)
    assert result.failure.stage == "extraction"
    assert result.failure.code == "UNSUPPORTED_EXTRACTION"
    p.extraction.extract.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "unsupported", "corrupt"])
def test_real_bad_input(tmp_path, kind):
    path = tmp_path / ("bad.pdf" if kind == "corrupt" else "bad.txt")
    if kind != "missing":
        path.write_bytes(b"%PDF-1.7\ninvalid" if kind == "corrupt" else b"plain unsupported text")
    detector = Mock()
    result = DocumentPipeline(detection=detector).process(path)
    assert result.failure.stage == "file_intelligence"
    detector.detect.assert_not_called()
    assert str(path) not in json.dumps(result.sanitized_summary())


def test_invalid_offsets_stop_at_redaction(tmp_path):
    p, path, _, detection, calls = fixture_pipeline(tmp_path)
    detection.detections[0].end = 100000
    result = p.process(path)
    assert result.failure.stage == "redaction"
    assert "audit" not in [c[0] for c in calls]


def test_zero_candidates_no_known_review_not_safe(tmp_path):
    p, path, *_ = fixture_pipeline(tmp_path, empty=True)
    result = p.process(path)
    assert result.processing_status == ProcessingStatus.PROCESSED_NO_KNOWN_REVIEW
    assert result.redaction_result.redaction_complete
    assert result.audit_result.human_review_complete
    assert result.review_queue == [] and not result.safe_for_llm
    assert not result.coverage_verified and not result.downstream_export_permitted


def test_feedback_three_actions_immutable_no_upstream_reruns(tmp_path):
    p, path, extraction, _, calls = fixture_pipeline(tmp_path)
    original = p.process(path)
    snapshot = deepcopy(original)
    calls.clear()
    review = next(r for r in original.audit_result.records if r.effective_decision == "REVIEW")
    confirmed = next(r for r in original.audit_result.records if r.effective_decision == "CONFIRM")
    updated = p.apply_feedback(original, ReviewerFeedback("CONFIRM_PII", "reviewer", review.detection_id))
    assert updated.processing_status == ProcessingStatus.PROCESSED_NO_KNOWN_REVIEW
    assert "Brightwell" not in updated.internal_preview
    updated = p.apply_feedback(updated, ReviewerFeedback("FALSE_POSITIVE", "reviewer", confirmed.detection_id))
    assert "Ada Example" in updated.internal_preview
    value = "missing@example.invalid"
    start = extraction.pages[0].text.index(value)
    updated = p.apply_feedback(updated, ReviewerFeedback("MISSED_PII", "reviewer", page_number=1,
        original_start=start, original_end=start + len(value), entity_type="EMAIL_ADDRESS"))
    assert value not in updated.internal_preview and "[EMAIL_ADDRESS_001]" in updated.internal_preview
    assert updated.audit_result.revision == 3 and len(updated.audit_result.feedback) == 3
    assert updated.detection_result == original.detection_result
    assert updated.audit_result.original_detection_result == original.detection_result
    assert original == snapshot
    assert all(c[0] == "audit" for c in calls)  # Engine 5 validates its immutable baseline.
    assert not updated.safe_for_llm and not updated.coverage_verified


def test_explicit_persistence_reload_without_reruns(tmp_path):
    p, path, *_ = fixture_pipeline(tmp_path)
    result = p.process(path)
    assert not (tmp_path / "private-audit").exists()
    saved = p.save_audit(result)
    assert saved.failure is None and saved.persisted_path.exists()
    assert result.persisted_path is None
    loaded = p.load_audit(result.document_id)
    assert loaded.audit_result == result.audit_result
    assert loaded.detection_result == result.detection_result
    assert loaded.file_intelligence_result is None
    assert set(loaded.stage_timings) == {"persistence_load", "artifact_redaction", "artifact_verification"}
    assert not loaded.safe_for_llm


@pytest.mark.parametrize("operation", ["feedback", "persistence_save", "persistence_load"])
def test_feedback_and_persistence_failure(tmp_path, operation):
    p, path, *_ = fixture_pipeline(tmp_path)
    result = p.process(path)
    before = deepcopy(result)
    method = {"feedback": "apply_feedback", "persistence_save": "save_audit", "persistence_load": "load_audit"}[operation]
    setattr(p.audit, method, Mock(side_effect=RuntimeError("SECRET PII")))
    failed = (p.apply_feedback(result, ReviewerFeedback("CONFIRM_PII", "reviewer", "D000001"))
              if operation == "feedback" else p.save_audit(result) if operation == "persistence_save"
              else p.load_audit(result.document_id))
    assert failed.failure.stage == operation
    assert failed.processing_status == ProcessingStatus.PROCESSING_FAILED
    assert result == before
    assert "SECRET" not in json.dumps(failed.sanitized_summary())


def test_scanned_pdf_routes_to_mocked_ocr_once(tmp_path, monkeypatch):
    p, path, extraction, *_ = fixture_pipeline(tmp_path, empty=True)
    metadata = replace(p.file_intelligence.analyze(str(path)), extraction_strategy="ocr")
    p.file_intelligence.analyze = Mock(return_value=metadata)
    monkeypatch.setattr(OCREngine, "__init__", lambda self: None)
    ocr = Mock(return_value=extraction)
    monkeypatch.setattr(OCREngine, "extract_pdf", ocr)
    pipeline = DocumentPipeline(file_intelligence=p.file_intelligence, detection=p.detection, audit=p.audit, artifacts=stub_artifacts(),visual_detection=p.visual_detection)
    result = pipeline.process(path)
    assert result.failure is None
    ocr.assert_called_once_with(path)
    p.file_intelligence.analyze.assert_called_once_with(str(path))


def test_real_native_pdf_all_engines_and_feedback(tmp_path, monkeypatch):
    path = tmp_path / "native.pdf"
    pdf = canvas.Canvas(str(path))
    for i, line in enumerate(["Employee: EMP-00001", "Owner: John Smith", "Email: audit@example.com", "Risk Management"]):
        pdf.drawString(50, 750 - i * 20, line)
    pdf.save()
    ocr = Mock(side_effect=AssertionError("Native PDF must not invoke OCR"))
    monkeypatch.setattr(OCREngine, "extract_pdf", ocr)
    pipeline = DocumentPipeline(audit=AuditEngine(tmp_path / "native-private-audit"))
    result = pipeline.process(path)
    assert result.failure is None
    assert result.file_intelligence_result.extraction_strategy == "text"
    assert all(page.extraction_method == "text" for page in result.extraction_result.pages)
    types = {d.entity_type for d in result.detection_result.detections}
    assert {"EMPLOYEE_ID", "EMAIL_ADDRESS", "PERSON"} <= types
    assert not any(d.text == "Risk Management" for d in result.detection_result.detections)
    assert "[EMPLOYEE_ID_001]" in result.internal_preview
    person = next(r for r in result.audit_result.records if r.original_detection.text == "John Smith")
    corrected = pipeline.apply_feedback(result, ReviewerFeedback("FALSE_POSITIVE", "fixture-reviewer", person.detection_id))
    assert "John Smith" in corrected.internal_preview
    assert len(corrected.audit_result.feedback) == 1
    assert not result.audit_result.feedback
    assert not corrected.safe_for_llm
    ocr.assert_not_called()


def test_mocked_ocr_render_failure_stops_detection(tmp_path, monkeypatch):
    p, path, *_ = fixture_pipeline(tmp_path)
    metadata = replace(p.file_intelligence.analyze(str(path)), extraction_strategy="ocr")
    p.file_intelligence.analyze = lambda _: metadata
    monkeypatch.setattr(OCREngine, "__init__", lambda self: None)
    monkeypatch.setattr(OCREngine, "extract_pdf", Mock(side_effect=RuntimeError("SECRET renderer contents")))
    detector = Mock()
    result = DocumentPipeline(file_intelligence=p.file_intelligence, detection=detector).process(path)
    assert result.failure.stage == "extraction"
    detector.detect.assert_not_called()
    assert "SECRET" not in json.dumps(result.sanitized_summary())


def test_crossing_spans_reach_overlap_review_queue(tmp_path):
    p, path, extraction, detection, _ = fixture_pipeline(tmp_path, empty=True)
    text = extraction.pages[0].text
    for start, end in [(0, 7), (4, 11)]:
        detection.detections.append(DetectedPII("PERSON", text[start:end], start, end, .9, "pattern", "Synthetic", 1,
            validation_decision="CONFIRM", final_decision="CONFIRM"))
    detection.raw_candidate_count = 2
    result = p.process(path)
    assert result.failure is None
    assert not result.redaction_result.redaction_complete
    assert result.review_queue[0].category == "unresolved_overlap"
    assert result.processing_status == ProcessingStatus.PROCESSED_REVIEW_REQUIRED
    assert not result.safe_for_llm
