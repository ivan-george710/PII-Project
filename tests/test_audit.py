"""Synthetic audit/review tests: no OCR or generative inference."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.engines.extraction.models import ExtractionResult, ExtractedPage, OCRTextBlock
from app.engines.pii_detection.models import DetectedPII, PIIDetectionResult
from app.engines.redaction import RedactionEngine
from app.engines.audit import (AuditEngine, ReviewerFeedback, ReviewAction, AuditValidationError,
                               FeedbackConflictError, AuditStorageError)


def source(*texts):
    return ExtractionResult(Path("synthetic.pdf"), "synthetic.pdf", "pdf", [
        ExtractedPage(i, text, "text") for i, text in enumerate(texts, 1)])


def finding(text, value, entity="PERSON", decision="CONFIRM", page=1, **extra):
    start = text.index(value)
    return DetectedPII(entity, value, start, start + len(value), .9, "pattern", "Synthetic", page,
        validation_decision="AMBIGUOUS" if decision == "REVIEW" else decision,
        validation_reason="fixture", final_decision=decision, **extra)


def audit_for(extraction, *detections, engine=None):
    engine = engine or AuditEngine()
    detection = PIIDetectionResult(extraction.source_path, extraction.filename,
        [d for d in detections if d.final_decision == "CONFIRM"],
        [d for d in detections if d.final_decision == "REJECT"],
        [d for d in detections if d.final_decision == "REVIEW"], len(detections))
    redaction = RedactionEngine().redact(extraction, detection)
    return engine.create_audit(extraction, detection, redaction)


def feedback(action, detection_id=None, **kwargs):
    return ReviewerFeedback(action, "reviewer-1", detection_id, **kwargs)


def test_creation_counts_traceability_and_stability():
    text = "Ada Example | policy | Brightwell"
    extraction = source(text)
    detections = [finding(text, "Ada Example"), finding(text, "policy", decision="REJECT"),
                  finding(text, "Brightwell", decision="REVIEW")]
    audit = audit_for(extraction, *detections)
    assert audit == audit_for(extraction, *detections)
    assert len(audit.records) == audit.counts["raw_detection_count"] == 3
    assert (audit.counts["confirmed"], audit.counts["rejected"], audit.counts["review"]) == (1, 1, 1)
    assert [r.redaction_status for r in audit.records] == ["APPLIED", "REJECTED", "REVIEW_REQUIRED"]
    r = audit.records[0]
    assert r.tag == "[PERSON_001]" and r.original_detection == detections[0]
    assert r.effective_detection.confidence == .9
    assert r.original_detection.validation_reason == "fixture"
    assert r.original_detection.recognizer == "Synthetic"
    assert r.document_id == audit.document_id
    assert audit.redaction_result.pages[0].text[r.redacted_start:r.redacted_end] == r.tag
    assert len(AuditEngine().get_review_queue(audit)) == 1
    assert not audit.human_review_complete and not audit.safe_for_llm


def test_multi_page_and_source_blocks():
    extraction = source("Ada Example", "EMP-00001")
    extraction.pages[1].extraction_method = "ocr"
    extraction.pages[1].blocks = [OCRTextBlock("EMP-00001", .9, [[0, 0], [1, 1]])]
    audit = audit_for(extraction, finding("Ada Example", "Ada Example"),
        finding("EMP-00001", "EMP-00001", "EMPLOYEE_ID", page=2, source_block=0))
    assert [r.effective_detection.page_number for r in audit.records] == [1, 2]
    assert audit.records[1].effective_detection.source_block == 0
    assert audit.records[1].extraction_method == "ocr"


def test_superseded_overlap_has_covering_tag_and_identity():
    text = "ada@example.com"
    audit = audit_for(source(text), finding(text, "ada"), finding(text, text, "EMAIL_ADDRESS"))
    loser = next(r for r in audit.records if r.redaction_status == "SUPERSEDED")
    winner = next(r for r in audit.records if r.redaction_status == "APPLIED")
    assert loser.tag == winner.tag == "[EMAIL_ADDRESS_001]"
    assert loser.superseded_by == winner.detection_id
    assert audit.counts["applied_redactions"] == audit.counts["superseded_overlaps"] == 1
    assert audit.human_review_complete


def test_crossing_overlap_is_one_queue_group_and_stays_blocked_after_confirm():
    text = "abcdefghij"
    audit = audit_for(source(text), finding(text, "abcdef"), finding(text, "efghij"))
    assert len(audit.review_queue) == 1
    assert len(audit.review_queue[0].detection_ids) == 2
    assert audit.counts["unresolved_overlap_findings"] == 2
    corrected = AuditEngine().apply_feedback(audit, feedback("CONFIRM_PII", audit.records[0].detection_id))
    assert not corrected.redaction_result.redaction_complete
    assert not corrected.downstream_export_permitted


def test_equal_duplicates_not_dropped_and_initial_winner_preserved():
    text = "Ada Example"
    first = finding(text, text)
    second = replace(first, recognizer="A-first-alphabetically")
    audit = audit_for(source(text), first, second, deepcopy(first))
    assert len(audit.records) == 3
    assert audit.counts["superseded_overlaps"] == 2
    applied = next(r for r in audit.records if r.redaction_status == "APPLIED")
    assert applied.original_detection.recognizer == "Synthetic"


def test_false_positive_restores_original_text_and_preserves_automated_history():
    text = "Owner: Ada Example"
    audit = audit_for(source(text), finding(text, "Ada Example"))
    snapshot = deepcopy(audit)
    corrected = AuditEngine().apply_feedback(audit, feedback("FALSE_POSITIVE", audit.records[0].detection_id))
    assert corrected.redaction_result.full_text == text
    assert corrected.records[0].automated_decision == "CONFIRM"
    assert corrected.records[0].effective_decision == "REJECT"
    assert corrected.records[0].corrected
    assert corrected.feedback[0].previous_decision == "CONFIRM"
    assert corrected.feedback[0].new_decision == "REJECT"
    assert audit == snapshot
    assert corrected.original_redaction_result.full_text == "Owner: [PERSON_001]"


def test_confirm_review_and_rejected_findings():
    text = "Brightwell | Ada Example"
    audit = audit_for(source(text), finding(text, "Brightwell", decision="REVIEW"),
                      finding(text, "Ada Example", decision="REJECT"))
    engine = AuditEngine()
    for record in audit.records:
        audit = engine.apply_feedback(audit, feedback("CONFIRM_PII", record.detection_id))
    assert audit.redaction_result.full_text == "[PERSON_001] | [PERSON_002]"
    assert audit.human_review_complete and audit.redaction_result.redaction_complete
    assert not audit.coverage_verified and not audit.downstream_export_permitted and not audit.safe_for_llm
    assert len(audit.feedback) == 2


def test_missed_pii_uses_source_slice_human_provenance_and_repeated_tags():
    text = "ada@example.com; ada@example.com"
    audit = audit_for(source(text))
    engine = AuditEngine()
    first = feedback("MISSED_PII", page_number=1, original_start=0, original_end=15,
                     entity_type="EMAIL_ADDRESS")
    corrected = engine.apply_feedback(audit, first)
    corrected = engine.apply_feedback(corrected, replace(first, original_start=17, original_end=32))
    assert corrected.redaction_result.full_text == "[EMAIL_ADDRESS_001]; [EMAIL_ADDRESS_001]"
    assert corrected.counts["raw_detection_count"] == 0
    assert corrected.counts["effective_finding_count"] == corrected.counts["human_added"] == 2
    record = corrected.records[0]
    assert record.original_detection.text == text[:15]
    assert record.effective_detection.detection_method == "human_review"
    assert record.effective_detection.recognizer == "HumanReview"
    assert record.automated_decision is None
    assert record.effective_detection.confidence == 0.0  # uncalibrated human provenance


@pytest.mark.parametrize("changes", [dict(page_number=0), dict(page_number=2), dict(page_number=True),
    dict(original_start=-1), dict(original_end=99), dict(original_start=2, original_end=1),
    dict(original_start=1, original_end=1), dict(original_start=True), dict(entity_type="PERSON]"),
    dict(entity_type="")])
def test_invalid_missed_span_blocks_correction_without_mutation(changes):
    audit = audit_for(source("Ada Example"))
    snap = deepcopy(audit)
    request = feedback("MISSED_PII", page_number=1, original_start=0, original_end=11, entity_type="PERSON")
    with pytest.raises(AuditValidationError):
        AuditEngine().apply_feedback(audit, replace(request, **changes))
    assert audit == snap


def test_duplicate_feedback_idempotent_and_conflicts_explicit():
    engine = AuditEngine()
    audit = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example"))
    target = audit.records[0].detection_id
    request = feedback("FALSE_POSITIVE", target, reason="synthetic review")
    rejected = engine.apply_feedback(audit, request)
    assert engine.apply_feedback(rejected, request) == rejected
    with pytest.raises(FeedbackConflictError):
        engine.apply_feedback(rejected, feedback("CONFIRM_PII", target))
    with pytest.raises(FeedbackConflictError):
        engine.apply_feedback(rejected, feedback("CONFIRM_PII", target, expected_decision="CONFIRM"))
    confirmed = engine.apply_feedback(rejected, feedback("CONFIRM_PII", target, expected_decision="REJECT"))
    assert confirmed.redaction_result.full_text == "[PERSON_001]"
    assert [e.new_decision for e in confirmed.feedback] == ["REJECT", "CONFIRM"]


def test_duplicate_missed_feedback_and_existing_detection():
    engine = AuditEngine()
    audit = audit_for(source("Ada Example"))
    request = feedback("MISSED_PII", page_number=1, original_start=0, original_end=11, entity_type="PERSON")
    corrected = engine.apply_feedback(audit, request)
    assert engine.apply_feedback(corrected, request) == corrected
    automated = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example"))
    with pytest.raises(AuditValidationError, match="already exists"):
        engine.apply_feedback(automated, request)


@pytest.mark.parametrize("changes", [dict(reviewer_id=""), dict(action="APPROVE_DOCUMENT"),
    dict(timestamp="2026-10-12T09:00:00"), dict(timestamp="invalid"), dict(detection_id="../../x"),
    dict(timestamp=0), dict(timestamp=""), dict(expected_decision=[]),
    dict(detection_id="D999999"), dict(original_start=0)])
def test_invalid_feedback_identity_action_timestamp_target(changes):
    audit = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example"))
    request = feedback("FALSE_POSITIVE", audit.records[0].detection_id)
    with pytest.raises(AuditValidationError):
        AuditEngine().apply_feedback(audit, replace(request, **changes))


def test_timestamp_and_reviewer_supplied_are_internal_only():
    audit = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example", decision="REVIEW"))
    corrected = AuditEngine().apply_feedback(audit, ReviewerFeedback("CONFIRM_PII", "ada@example.com",
        audit.records[0].detection_id, reason="Ada Example", timestamp="2026-10-12T12:00:00+05:30"))
    event = corrected.feedback[0]
    assert event.feedback.reviewer_id == "ada@example.com"
    assert event.feedback.timestamp == "2026-10-12T06:30:00+00:00"
    serialized = json.dumps(corrected.sanitized_summary())
    for value in ["Ada Example", "ada@example.com", "synthetic.pdf", corrected.document_id]:
        assert value not in serialized
    assert "reason" not in serialized


def test_original_caller_inputs_never_mutated_or_aliased():
    extraction = source("Ada Example")
    detection = PIIDetectionResult(extraction.source_path, extraction.filename,
                                   [finding(extraction.full_text, extraction.full_text)], [], [], 1)
    redacted = RedactionEngine().redact(extraction, detection)
    snapshot = deepcopy((extraction, detection, redacted))
    audit = AuditEngine().create_audit(extraction, detection, redacted)
    corrected = AuditEngine().apply_feedback(audit, feedback("FALSE_POSITIVE", audit.records[0].detection_id))
    assert (extraction, detection, redacted) == snapshot
    extraction.pages[0].text = "changed"
    detection.detections[0].text = "changed"
    assert corrected.extraction.full_text == "Ada Example"
    assert corrected.original_detection_result.detections[0].text == "Ada Example"


def test_persistence_reload_and_revision_conflict(tmp_path):
    engine = AuditEngine(tmp_path / "private-audits")
    original = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example"), engine=engine)
    path = engine.save_audit(original)
    assert path.is_file()
    assert engine.save_audit(original) == path
    assert engine.load_audit(original.document_id) == original
    corrected = engine.apply_feedback(original, feedback("FALSE_POSITIVE", original.records[0].detection_id))
    with pytest.raises(AuditStorageError, match="expected revision"):
        engine.save_audit(corrected)
    engine.save_audit(corrected, expected_revision=0)
    assert engine.load_audit(original.document_id) == corrected
    assert (path.parent / ".gitignore").read_text() == "*\n!.gitignore\n"
    with pytest.raises(AuditStorageError):
        engine.save_audit(original, expected_revision=0)


def test_missed_feedback_reload(tmp_path):
    engine = AuditEngine(tmp_path / "private-audits")
    audit = audit_for(source("ada@example.com"))
    corrected = engine.apply_feedback(audit, feedback("MISSED_PII", page_number=1, original_start=0,
        original_end=15, entity_type="EMAIL_ADDRESS"))
    engine.save_audit(corrected)
    assert engine.load_audit(corrected.document_id) == corrected


def test_corrupt_storage_and_tampered_history_fail_closed(tmp_path):
    engine = AuditEngine(tmp_path / "private-audits")
    audit = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example"))
    corrected = engine.apply_feedback(audit, feedback("FALSE_POSITIVE", audit.records[0].detection_id))
    path = engine.save_audit(corrected)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["feedback"][0]["new_decision"] = "CONFIRM"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(AuditValidationError):
        engine.load_audit(audit.document_id)
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(AuditStorageError):
        engine.load_audit(audit.document_id)


def test_atomic_write_failure_preserves_previous_snapshot(tmp_path, monkeypatch):
    import app.engines.audit.storage as storage
    engine = AuditEngine(tmp_path / "private-audits")
    audit = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example"))
    path = engine.save_audit(audit)
    original = path.read_bytes()
    corrected = engine.apply_feedback(audit, feedback("FALSE_POSITIVE", audit.records[0].detection_id))
    real_replace = storage.os.replace

    def failing_replace(source, destination):
        if str(destination).endswith(".json"):
            raise OSError("simulated disk failure")
        return real_replace(source, destination)

    monkeypatch.setattr(storage.os, "replace", failing_replace)
    with pytest.raises(AuditStorageError):
        engine.save_audit(corrected, expected_revision=0)
    assert path.read_bytes() == original
    assert not list(path.parent.glob(".audit-*.tmp"))


def test_public_storage_and_path_traversal_rejected(tmp_path):
    audit = audit_for(source())
    with pytest.raises(AuditStorageError):
        AuditEngine(tmp_path / "public" / "audits").save_audit(audit)
    with pytest.raises(AuditStorageError):
        AuditEngine(tmp_path / "private").load_audit("../x")


def test_mismatched_redaction_counts_and_snapshot_mutations_fail_closed():
    extraction = source("Ada Example")
    detection = PIIDetectionResult(extraction.source_path, extraction.filename,
                                   [finding(extraction.full_text, extraction.full_text)], [], [], 1)
    redacted = RedactionEngine().redact(extraction, detection)
    bad = deepcopy(redacted)
    bad.pages[0].text = "unsafe altered output"
    with pytest.raises(AuditValidationError, match="does not match"):
        AuditEngine().create_audit(extraction, detection, bad)
    with pytest.raises(AuditValidationError, match="accounting"):
        AuditEngine().create_audit(extraction, replace(detection, raw_candidate_count=0), redacted)
    audit = AuditEngine().create_audit(extraction, detection, redacted)
    audit.extraction.pages[0].text = "tampered"
    with pytest.raises(AuditValidationError):
        AuditEngine().apply_feedback(audit, feedback("FALSE_POSITIVE", audit.records[0].detection_id))


def test_unknown_metadata_becomes_validation_review_issue():
    extraction = source("Ada Example")
    item = finding(extraction.full_text, extraction.full_text)
    item.validation_decision = "UNSUPPORTED"
    audit = audit_for(extraction, item)
    assert audit.records[0].redaction_status == "VALIDATION_ISSUE"
    assert audit.review_queue[0].category == "unknown_decision"
    corrected = AuditEngine().apply_feedback(audit, feedback("CONFIRM_PII", audit.records[0].detection_id))
    assert corrected.redaction_result.redaction_complete
    assert not corrected.safe_for_llm


def test_empty_document_and_missing_inputs():
    audit = audit_for(source())
    assert not audit.records and not audit.review_queue
    assert audit.human_review_complete and not audit.coverage_verified
    assert not audit.safe_for_llm and not audit.downstream_export_permitted
    with pytest.raises(AuditValidationError):
        AuditEngine().create_audit(None, None, None)


def test_summary_rejects_injected_arbitrary_count_values():
    audit = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example"))
    audit.counts["confirmed"] = "Ada Example"
    with pytest.raises(AuditValidationError):
        audit.sanitized_summary()


def test_safety_properties_cannot_be_manually_enabled():
    audit = audit_for(source())
    for field in ["safe_for_llm", "downstream_export_permitted", "coverage_verified"]:
        with pytest.raises(AttributeError):
            setattr(audit, field, True)


def test_saved_traceability_tamper_rejected(tmp_path):
    engine = AuditEngine(tmp_path / "private-audits")
    audit = audit_for(source("Ada Example"), finding("Ada Example", "Ada Example"))
    path = engine.save_audit(audit)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["records"][0]["original_detection"]["text"] == "Ada Example"
    data["records"][0]["tag"] = "[ALTERED_001]"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(AuditValidationError):
        engine.load_audit(audit.document_id)


def test_document_identity_independent_of_current_directory(tmp_path, monkeypatch):
    extraction = source("Ada Example")
    item = finding(extraction.full_text, extraction.full_text)
    first = audit_for(extraction, item)
    monkeypatch.chdir(tmp_path)
    second = audit_for(extraction, item)
    assert first.document_id == second.document_id
    assert [r.detection_id for r in first.records] == [r.detection_id for r in second.records]


def test_storage_alias_cannot_restrict_project_root(tmp_path, monkeypatch):
    import app.engines.audit.storage as storage
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)
    audit = audit_for(source())
    with pytest.raises(AuditStorageError):
        AuditEngine(tmp_path / "private" / "..").save_audit(audit)


def test_new_automated_baseline_cannot_erase_saved_history(tmp_path):
    engine = AuditEngine(tmp_path / "private-audits")
    extraction = source("Ada Example")
    original = audit_for(extraction, finding(extraction.full_text, extraction.full_text))
    engine.save_audit(original)
    changed = audit_for(extraction, finding(extraction.full_text, extraction.full_text, decision="REJECT"))
    assert changed.document_id == original.document_id
    with pytest.raises(AuditStorageError, match="baseline differs"):
        engine.save_audit(changed, expected_revision=0)
    assert engine.load_audit(original.document_id) == original
