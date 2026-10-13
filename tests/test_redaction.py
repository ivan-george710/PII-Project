"""Synthetic Engine 4 tests, including legacy audit-metadata compatibility."""
from dataclasses import replace
from pathlib import Path
import json

import pytest

from app.engines.extraction.models import ExtractedPage, ExtractionResult, OCRTextBlock
from app.engines.pii_detection.models import DetectedPII, PIIDetectionResult
from app.engines.redaction import RedactionEngine, RedactionValidationError


def extraction(*texts):
    return ExtractionResult(Path("synthetic.pdf"), "synthetic.pdf", "pdf", [
        ExtractedPage(i, text, "text") for i, text in enumerate(texts, 1)])


def finding(text, value, entity="PERSON", page=1, start=None, **metadata):
    start = text.index(value) if start is None else start
    return DetectedPII(entity, value, start, start + len(value), .9,
                       "pattern", "synthetic", page, **metadata)


def run(source, *detections, rejected=()):
    return RedactionEngine().redact(source, PIIDetectionResult(
        source.source_path, source.filename, list(detections), list(rejected)))


def test_single_person_and_metadata():
    text = "Owner: Ada Example\nApproved."
    d = finding(text, "Ada Example", validation_decision="CONFIRM")
    result = run(extraction(text), d)
    assert result.full_text == "Owner: [PERSON_001]\nApproved."
    assert result.applied_redaction_count == 1
    r = result.redactions[0]
    assert (r.original_text, r.original_start, r.original_end) == (d.text, d.start, d.end)
    assert (r.entity_type, r.page_number, r.confidence) == ("PERSON", 1, .9)
    assert (r.recognizer, r.detection_method, r.validation_decision, r.llm_decision) == (
        "synthetic", "pattern", "CONFIRM", None)
    assert r.extraction_method == "text"
    assert result.pages[0].text[r.redacted_start:r.redacted_end] == r.tag
    assert result.source_path == Path("synthetic.pdf")
    assert result.filename == "synthetic.pdf"


def test_order_numbering_repetition_and_exact_preservation():
    text = "Ada Example\nEMP-00001 ada@example.invalid\nAda Example / Bea Example\n"
    a = finding(text, "Ada Example")
    b = finding(text, "Ada Example", start=text.rindex("Ada Example"))
    detections = [finding(text, "Bea Example"), b,
                  finding(text, "ada@example.invalid", "EMAIL_ADDRESS"),
                  finding(text, "EMP-00001", "EMPLOYEE_ID"), a]
    result = run(extraction(text), *detections)
    assert result.full_text == (
        "[PERSON_001]\n[EMPLOYEE_ID_001] [EMAIL_ADDRESS_001]\n"
        "[PERSON_001] / [PERSON_002]\n")
    assert len(result.tag_mapping["[PERSON_001]"]) == 2
    for record in result.redactions:
        assert result.full_text[record.redacted_start:record.redacted_end] == record.tag
    assert result == run(extraction(text), *detections)


def test_same_value_different_entity_and_no_normalization():
    text = "Ada ada Ada"
    result = run(extraction(text), finding(text, "Ada"), finding(text, "ada"),
                 finding(text, "Ada", "EMPLOYEE_ID", start=8))
    assert result.full_text == "[PERSON_001] [PERSON_002] [EMPLOYEE_ID_001]"


def test_only_detected_occurrence_changes():
    text = "Ada Example; Ada Example"
    assert run(extraction(text), finding(text, "Ada Example")).full_text == (
        "[PERSON_001]; Ada Example")


@pytest.mark.parametrize("nested", [True, False])
def test_contained_and_equal_overlaps(nested):
    text = "ada@example.invalid"
    email = finding(text, text, "EMAIL_ADDRESS")
    other = finding(text, "ada" if nested else text, "PERSON")
    result = run(extraction(text), other, email)
    assert result.full_text == "[EMAIL_ADDRESS_001]"
    assert result.issues[0].code == "superseded_overlap"
    assert result.issues[0].superseded_by == email
    assert not result.issues[0].blocking
    assert result.redaction_complete


def test_equal_span_confidence_and_stable_tie():
    text = "example"
    low = finding(text, text, "CUSTOM")
    high = replace(low, confidence=1, recognizer="high")
    result = run(extraction(text), low, high)
    assert result.redactions[0].recognizer == "high"
    tied = replace(low, recognizer="second")
    assert run(extraction(text), low, tied).redactions[0].recognizer == "synthetic"


def test_crossing_overlap_blocks_export():
    text = "abcdefghij"
    result = run(extraction(text), finding(text, "abcdef"), finding(text, "efghij"))
    assert not result.redaction_complete
    assert result.full_text == text
    assert len(result.issues) == 2
    with pytest.raises(RedactionValidationError, match="block"):
        result.to_text_payload()


def test_covering_span_resolves_overlap_chain():
    text = "abcdefghij"
    result = run(extraction(text), finding(text, "abcdef"), finding(text, "efghij"),
                 finding(text, text, "EMAIL_ADDRESS"))
    assert result.full_text == "[EMAIL_ADDRESS_001]"
    assert result.redaction_complete


def test_adjacent_spans_do_not_overlap():
    text = "AdaBea"
    assert run(extraction(text), finding(text, "Ada"), finding(text, "Bea")).full_text == (
        "[PERSON_001][PERSON_002]")


def test_multi_page_order_and_global_tags():
    source = extraction("Ada Example", "Bea Example / Ada Example")
    source.pages[1].extraction_method = "ocr"
    result = run(source, finding(source.pages[1].text, "Ada Example", page=2),
                 finding(source.pages[0].text, "Ada Example"),
                 finding(source.pages[1].text, "Bea Example", page=2))
    assert result.full_text == "[PERSON_001]\n\n[PERSON_002] / [PERSON_001]"
    assert [p.page_number for p in result.pages] == [1, 2]
    assert result.pages[1].extraction_method == "ocr"


@pytest.mark.parametrize("texts", [(), ("",), ("Public policy",)])
def test_empty_or_no_detections_never_prove_safety(texts):
    result = run(extraction(*texts))
    assert result.full_text == "\n\n".join(texts)
    assert result.redaction_complete
    assert not result.safe_for_llm
    assert result.to_text_payload()["requires_coverage_review"]


@pytest.mark.parametrize("start,end", [(-1, 2), (0, 99), (3, 2), (2, 2), (True, 3)])
def test_invalid_offsets(start, end):
    source = extraction("Ada Example")
    with pytest.raises(RedactionValidationError, match="offsets"):
        run(source, replace(finding(source.full_text, source.full_text), start=start, end=end))


def test_text_mismatch():
    with pytest.raises(RedactionValidationError, match="mismatch"):
        run(extraction("Ada Example"), replace(finding("Ada Example", "Ada"), text="Bea"))


@pytest.mark.parametrize("metadata", [dict(llm_decision="REVIEW"),
    dict(llm_decision="Review"), dict(validation_decision="AMBIGUOUS"),
    dict(validation_decision="REVIEW"), dict(llm_decision="MAYBE"),
    dict(validation_decision="CONFIRM", llm_decision="REJECT")])
@pytest.mark.parametrize("collection", ["detections", "rejected"])
def test_unresolved_decisions_block_in_both_collections(metadata, collection):
    text = "Ada Example"
    d = finding(text, text, **metadata)
    result = run(extraction(text), *([d] if collection == "detections" else []),
                 rejected=[d] if collection == "rejected" else [])
    if metadata.get("validation_decision") in {"AMBIGUOUS", "REVIEW"} or metadata.get("llm_decision") == "REVIEW":
        assert result.full_text == "[PERSON_001]"
    else:
        assert result.full_text == text
    assert not result.redaction_complete
    assert not result.safe_for_llm


def test_rejected_false_positive_unchanged():
    text = "Public policy"
    result = run(extraction(text), rejected=[finding(text, "policy", validation_decision="REJECT")])
    assert result.full_text == text
    assert len(result.rejected) == 1
    assert result.redaction_complete


def test_ambiguous_llm_confirm_and_reject():
    text = "Ada Example policy"
    result = run(extraction(text), finding(text, "Ada Example", validation_decision="AMBIGUOUS",
                 llm_decision="CONFIRM"), rejected=[finding(text, "policy",
                 validation_decision="AMBIGUOUS", llm_decision="REJECT")])
    assert result.full_text == "[PERSON_001] policy"
    assert result.redaction_complete


def test_unknown_page_and_duplicate_page():
    source = extraction("Ada")
    with pytest.raises(RedactionValidationError, match="page"):
        run(source, finding("Ada", "Ada", page=2))
    source.pages.append(source.pages[0])
    with pytest.raises(RedactionValidationError, match="page"):
        run(source)


@pytest.mark.parametrize("field,value", [("source_path", Path("other.pdf")),
                                        ("filename", "other.pdf")])
def test_source_mismatch(field, value):
    source = extraction("Ada")
    detections = PIIDetectionResult(source.source_path, source.filename, [], [])
    setattr(detections, field, value)
    with pytest.raises(RedactionValidationError, match="Source"):
        RedactionEngine().redact(source, detections)


@pytest.mark.parametrize("missing", ["extraction", "detection"])
def test_missing_results(missing):
    source = extraction()
    with pytest.raises(RedactionValidationError, match="required"):
        RedactionEngine().redact(None if missing == "extraction" else source,
            None if missing == "detection" else PIIDetectionResult(source.source_path, source.filename, [], []))


def test_mapping_excluded_and_input_unchanged():
    source = extraction("Ada Example")
    d = finding(source.full_text, source.full_text)
    result = run(source, d)
    payload = json.dumps(result.to_text_payload())
    assert d.text not in payload
    assert "tag_mapping" not in payload and "original_text" not in payload
    assert result.tag_mapping["[PERSON_001]"][0] == d
    d.text = "changed"
    assert result.tag_mapping["[PERSON_001]"][0].text == "Ada Example"
    assert source.full_text == "Ada Example"


def test_source_block_preserved_only_when_available():
    source = extraction("Ada")
    source.pages[0].blocks = [OCRTextBlock("Ada", .9, [[0, 0], [10, 10]])]
    result = run(source, finding("Ada", "Ada", source_block=0))
    assert result.redactions[0].source_block == 0
    with pytest.raises(RedactionValidationError, match="block"):
        run(source, finding("Ada", "Ada", source_block=1))


@pytest.mark.parametrize("changes", [dict(entity_type="PERSON]secret"),
    dict(confidence=float("nan")), dict(confidence=2)])
def test_invalid_tag_type_and_confidence(changes):
    with pytest.raises(RedactionValidationError):
        run(extraction("Ada"), replace(finding("Ada", "Ada"), **changes))
