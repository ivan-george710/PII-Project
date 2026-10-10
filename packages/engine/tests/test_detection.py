from __future__ import annotations

import builtins
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pii_guard import DetectionConfig, Finding, ProcessingError, ProcessingErrorCode, TextDetector
from pii_guard.detection.validation import RecognizerCandidate, DEFAULT_THRESHOLDS
from pii_guard.models import ExtractedTextBlock, SourceLocation
from pii_guard.rules.builtins import TEXT_RULE_IDS


EXAMPLES = {
    "PERSON": ("Patient Jane Smith arrived.", "Jane Smith", "12345"),
    "EMAIL_ADDRESS": ("Email alex@example.com today.", "alex@example.com", "alex@@example.com"),
    "PHONE_NUMBER": ("Phone +1 202-555-0123 today.", "+1 202-555-0123", "123"),
    "EMPLOYEE_ID": ("Employee EMP-12345 arrived.", "EMP-12345", "EMP-123456"),
    "US_SSN": ("SSN 321-54-6789 recorded.", "321-54-6789", "000-45-6789"),
    "US_PASSPORT": ("Passport 123456789 recorded.", "123456789", "12345678"),
    "US_DRIVER_LICENSE": ("Driver license A1234567 recorded.", "A1234567", "ABCD!"),
    "US_ITIN": ("ITIN 912-70-1234 recorded.", "912-70-1234", "912-00-1234"),
    "US_BANK_NUMBER": ("Bank account 123456789012 recorded.", "123456789012", "1234"),
    "IBAN_CODE": ("IBAN GB82WEST12345698765432 recorded.", "GB82WEST12345698765432", "GB00WEST12345698765432"),
    "CREDIT_CARD": ("Card 4111111111111111 recorded.", "4111111111111111", "4111111111111112"),
    "MEDICAL_LICENSE": ("DEA AB1234563 recorded.", "AB1234563", "AB1234564"),
}


class FakeBackend:
    supported_rule_ids = TEXT_RULE_IDS

    def __init__(self, matches: list[RecognizerCandidate]) -> None:
        self.matches = matches
        self.seen = []

    def recognize(self, text: str) -> list[RecognizerCandidate]:
        self.seen.append(text)
        return self.matches


def raw(rule: str, text: str, value: str, score: float = 0.99, name: str = "TestRecognizer") -> RecognizerCandidate:
    start = text.index(value)
    return RecognizerCandidate(rule_id=rule, start=start, end=start+len(value), score=score, recognizer=name)


@pytest.mark.parametrize("rule", sorted(TEXT_RULE_IDS))
def test_each_rule_positive_validation(rule: str) -> None:
    text, value, _ = EXAMPLES[rule]
    result = TextDetector(backend=FakeBackend([raw(rule,text,value)])).detect_message(text)
    assert len(result.accepted) == 1
    candidate = result.accepted[0]
    assert candidate.rule_id == rule
    assert candidate.matched_text == value
    assert text[candidate.location.start:candidate.location.end] == value


@pytest.mark.parametrize("rule", sorted(TEXT_RULE_IDS))
def test_each_rule_negative_format(rule: str) -> None:
    positive, value, invalid = EXAMPLES[rule]
    text = positive.replace(value, invalid)
    result = TextDetector(backend=FakeBackend([raw(rule,text,invalid)])).detect_message(text)
    assert not result.accepted
    assert result.rejected[0].reason == "invalid_format"


@pytest.mark.parametrize("rule", sorted(TEXT_RULE_IDS))
def test_thresholds_are_inclusive_and_configurable(rule: str) -> None:
    text, value, _ = EXAMPLES[rule]
    thresholds = dict(DEFAULT_THRESHOLDS)
    thresholds[rule] = 0.99
    config = DetectionConfig(thresholds=thresholds, context_validated_score=0)
    assert TextDetector(config, backend=FakeBackend([raw(rule,text,value,0.99)])).detect_message(text).accepted
    result = TextDetector(config, backend=FakeBackend([raw(rule,text,value,0.98)])).detect_message(text)
    assert not result.accepted
    assert result.rejected[0].reason == "below_threshold"


def test_default_thresholds_exact() -> None:
    config = DetectionConfig()
    assert config.thresholds["EMPLOYEE_ID"] == 0.9
    assert config.thresholds["PERSON"] == 0.75
    assert config.thresholds["PHONE_NUMBER"] == config.thresholds["EMAIL_ADDRESS"] == 0.7
    assert all(config.thresholds[r] == 0.8 for r in TEXT_RULE_IDS - {"EMPLOYEE_ID","PERSON","PHONE_NUMBER","EMAIL_ADDRESS"})
    with pytest.raises(ValidationError):
        DetectionConfig(thresholds={"EMPLOYEE_ID":0.9})
    with pytest.raises(ValidationError):
        DetectionConfig(thresholds={**config.thresholds, "EMPLOYEE_ID":1.1})


@pytest.mark.parametrize("value", ["EMP-12345", "(EMP-38104)", "staff:\nEMP-40522"])
def test_actual_employee_recognizer_positive(value: str) -> None:
    from pii_guard.detection.recognizers import EmployeeIdRecognizer
    results = EmployeeIdRecognizer().analyze(value, ["EMPLOYEE_ID"])
    assert len(results) == 1
    assert value[results[0].start:results[0].end].startswith("EMP-")
    assert results[0].score >= 0.9


@pytest.mark.parametrize("value", ["emp-12345", "EMP-1234", "EMP-123456", "XEMP-12345", "EMP-12345X", "EMP-12345_more", "EMP-12345-6789", "X-EMP-12345", "EMP-\u0661\u0662\u0663\u0664\u0665"])
def test_actual_employee_recognizer_negative(value: str) -> None:
    from pii_guard.detection.recognizers import EmployeeIdRecognizer
    assert not EmployeeIdRecognizer().analyze(value, ["EMPLOYEE_ID"])


def block(text: str, *, kind: str = "native_text", ref: str = "pdf:page:2:native_text", identity=None) -> ExtractedTextBlock:
    return ExtractedTextBlock(text=text, extraction_method=kind, confidence=0.7 if kind == "ocr" else None,
        location=SourceLocation(artifact_id=identity or uuid4(), kind=kind, page_number=2,
        slide_number=None, source_ref=ref, start=0, end=len(text), bbox=(0.1,0.2,0.3,0.4) if kind == "ocr" else None))


@pytest.mark.parametrize("kind", ["native_text", "ocr"])
def test_block_unicode_multiline_offsets_and_locations(kind: str) -> None:
    text = "\U0001f600 e\u0301\nEmployee EMP-12345\nend"
    source = block(text, kind=kind, ref=f"pdf:page:2:{kind}")
    backend = FakeBackend([raw("EMPLOYEE_ID",text,"EMP-12345")])
    candidate = TextDetector(backend=backend).detect_block(source).accepted[0]
    assert candidate.location.start == text.index("EMP-12345")
    assert candidate.location.end == text.index("EMP-12345") + 9
    assert candidate.location.artifact_id == source.location.artifact_id
    assert candidate.location.page_number == 2
    assert candidate.location.source_ref == source.location.source_ref
    assert candidate.location.bbox == source.location.bbox
    assert source.location.start == 0
    assert candidate.location is not source.location


def test_blocks_are_not_concatenated_or_merged_by_text() -> None:
    text = "EMP-12345"
    identity = uuid4()
    first = block(text, ref="first", identity=identity)
    second = block(text, ref="second", identity=identity)
    backend = FakeBackend([raw("EMPLOYEE_ID",text,text)])
    result = TextDetector(backend=backend).detect(text=text, blocks=[first,second,first])
    assert backend.seen == [text,text,text,text]
    assert len(result.accepted) == 3
    assert result.accepted[0].location.kind == "message"
    assert [c.location.source_ref for c in result.accepted[1:]] == ["first","second"]


def test_overlaps_and_duplicate_rule_spans() -> None:
    text = "Passport and driver license 123456789."
    matches = [raw("US_PASSPORT",text,"123456789",0.99,"A"), raw("US_PASSPORT",text,"123456789",0.98,"B"),
               raw("US_DRIVER_LICENSE",text,"123456789"), raw("US_DRIVER_LICENSE",text,"123456",0.9)]
    result = TextDetector(backend=FakeBackend(matches)).detect_message(text)
    # Partial arbitrary substring is rejected; distinct rules on the same span survive.
    assert {c.rule_id for c in result.accepted} == {"US_PASSPORT","US_DRIVER_LICENSE"}
    assert len(result.accepted) == 2
    assert next(c for c in result.accepted if c.rule_id == "US_PASSPORT").recognizer == "A"


def test_same_rule_contained_legitimate_person_matches_preserved() -> None:
    text = "Jane Smith arrived."
    result = TextDetector(backend=FakeBackend([raw("PERSON",text,"Jane Smith"),raw("PERSON",text,"Jane")])).detect_message(text)
    assert len(result.accepted) == 2


def test_context_and_original_score_retained_privately() -> None:
    text = "Passport 123456789"
    result = TextDetector(backend=FakeBackend([raw("US_PASSPORT",text,"123456789",0.05)])).detect_message(text)
    assert result.accepted[0].confidence == 0.85
    assert result.accepted[0].recognizer_confidence == 0.05
    bare = "123456789"
    result = TextDetector(backend=FakeBackend([raw("US_PASSPORT",bare,bare)])).detect_message(bare)
    assert not result.accepted
    assert result.rejected[0].reason == "missing_context"


def test_candidates_no_actions_or_matched_text_in_serialization() -> None:
    text = "EMP-12345"
    candidate = TextDetector(backend=FakeBackend([raw("EMPLOYEE_ID",text,text)])).detect_message(text).accepted[0]
    assert not hasattr(candidate, "action")
    assert text not in candidate.model_dump_json()
    assert text not in repr(candidate)
    # Only serialization is exercised: policy evaluation is not invoked here.
    finding = Finding(id=uuid4(), rule_id=candidate.rule_id, category=candidate.category,
        confidence=candidate.confidence, recognizer=candidate.recognizer, location=candidate.location, action="allowed_disabled")
    assert text not in finding.model_dump_json()
    with pytest.raises(ValidationError):
        Finding.model_validate({**finding.model_dump(),"matched_text":text})


def test_missing_recognizer_is_failure() -> None:
    backend = FakeBackend([])
    backend.supported_rule_ids = TEXT_RULE_IDS - {"PERSON"}
    with pytest.raises(ProcessingError) as error:
        TextDetector(backend=backend)
    assert error.value.code == ProcessingErrorCode.EXTRACTION_FAILED


def test_missing_model_no_automatic_download(monkeypatch: pytest.MonkeyPatch) -> None:
    from presidio_analyzer.nlp_engine import SpacyNlpEngine
    def forbidden(*args, **kwargs):
        pytest.fail("Missing model must not invoke automatic loading/download")
    monkeypatch.setattr(SpacyNlpEngine, "load", forbidden)
    with pytest.raises(ProcessingError):
        TextDetector(DetectionConfig(spacy_model="pii_guard_missing_model"))


def test_missing_dependency_is_processing_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == "presidio_analyzer":
            raise ImportError("unavailable")
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,"__import__",missing)
    with pytest.raises(ProcessingError) as error:
        TextDetector()
    assert error.value.code == ProcessingErrorCode.EXTRACTION_FAILED


def test_detection_failure_safe_and_source_linked() -> None:
    class Broken(FakeBackend):
        def recognize(self,text):
            raise RuntimeError("SECRET")
    identity = uuid4()
    submission = uuid4()
    with pytest.raises(ProcessingError) as error:
        TextDetector(backend=Broken([]), submission_id=submission).detect_block(block("EMP-12345",identity=identity))
    assert "SECRET" not in str(error.value)
    assert error.value.artifact_id == identity
    assert error.value.submission_id == submission


def test_invalid_provider_offset_fails_instead_of_clean_result() -> None:
    backend = FakeBackend([RecognizerCandidate(rule_id="PERSON",start=0,end=100,score=1,recognizer="Broken")])
    with pytest.raises(ProcessingError):
        TextDetector(backend=backend).detect_message("Jane")


@pytest.fixture(scope="module")
def real_detector():
    import spacy
    if not spacy.util.is_package("en_core_web_sm"):
        pytest.skip("Install en_core_web_sm to run trained-model Presidio integration")
    return TextDetector()


@pytest.mark.integration
@pytest.mark.presidio
@pytest.mark.parametrize("rule", sorted(TEXT_RULE_IDS))
def test_real_presidio_positive_and_negative_each_rule(real_detector, rule: str) -> None:
    text, value, invalid = EXAMPLES[rule]
    positive = real_detector.detect_message(text)
    assert any(c.rule_id == rule and c.matched_text == value for c in positive.accepted)
    negative = real_detector.detect_message(text.replace(value, invalid))
    assert not any(c.rule_id == rule and c.matched_text == invalid for c in negative.accepted)


@pytest.mark.integration
@pytest.mark.presidio
def test_real_presidio_unicode_message_and_extraction_blocks(real_detector) -> None:
    text = "\U0001f600 e\u0301\nEmployee EMP-12345\nEmail alex@example.com"
    sources = [block(text), block(text,kind="ocr",ref="ocr")]
    result = real_detector.detect(text=text, blocks=sources)
    ids = [c for c in result.accepted if c.rule_id == "EMPLOYEE_ID"]
    assert len(ids) == 3
    assert all(c.location.start == text.index("EMP-12345") for c in ids)
    assert ids[-1].location.bbox == sources[-1].location.bbox


@pytest.mark.integration
@pytest.mark.presidio
def test_real_presidio_keeps_overlap_across_patterns(real_detector, monkeypatch: pytest.MonkeyPatch) -> None:
    from presidio_analyzer import Pattern, PatternRecognizer
    recognizer = PatternRecognizer(supported_entity="PERSON", name="OverlapRegression",
        patterns=[Pattern("full",r"Jane Smith",0.95),Pattern("first",r"Jane",0.95)])
    monkeypatch.setattr(real_detector.backend,"recognizers",real_detector.backend.recognizers + [recognizer])
    result = real_detector.detect_message("Jane Smith arrived.")
    assert {c.matched_text for c in result.accepted if c.rule_id == "PERSON"} == {"Jane Smith","Jane"}


@pytest.mark.integration
@pytest.mark.presidio
def test_real_presidio_on_actual_native_pdf_block(real_detector, tmp_path: Path) -> None:
    from reportlab.pdfgen import canvas
    from pii_guard.extraction import extract_pdf
    path = tmp_path / "pii.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72,720,"Employee EMP-12345")
    pdf.save()
    class ForbiddenOCR:
        def recognize_image(self,*args,**kwargs):
            pytest.fail("Native PDF must not require OCR")
    identity = uuid4()
    extracted = extract_pdf(path,artifact_id=identity,filename=path.name,ocr_provider=ForbiddenOCR())
    result = real_detector.detect(blocks=extracted.blocks)
    match = next(c for c in result.accepted if c.rule_id == "EMPLOYEE_ID")
    assert match.location.artifact_id == identity
    assert match.location.page_number == 1
    assert match.location.source_ref == "pdf:page:1:native_text"
    assert match.location.start == 9


def test_no_cross_block_employee_match() -> None:
    backend = FakeBackend([])
    result = TextDetector(backend=backend).detect(blocks=[block("EMP-",ref="prefix"),block("12345",ref="suffix")])
    assert backend.seen == ["EMP-","12345"]
    assert not result.accepted


@pytest.mark.integration
@pytest.mark.presidio
def test_presidio_component_failure_is_explicit(real_detector, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args,**kwargs):
        raise RuntimeError("SECRET SOURCE CONTENT")
    monkeypatch.setattr(real_detector.backend.analyzer.nlp_engine,"process_text",broken)
    with pytest.raises(ProcessingError) as error:
        real_detector.detect_message("EMP-12345")
    assert error.value.code == ProcessingErrorCode.EXTRACTION_FAILED
    assert "SECRET" not in str(error.value)


def test_model_without_ner_is_explicit_failure(tmp_path: Path) -> None:
    import spacy
    directory = tmp_path / "blank-model"
    spacy.blank("en").to_disk(directory)
    with pytest.raises(ProcessingError):
        TextDetector(DetectionConfig(spacy_model=str(directory)))


def test_config_snapshot_and_invalid_boolean_threshold() -> None:
    config = DetectionConfig()
    with pytest.raises(ValidationError):
        DetectionConfig(thresholds={**config.thresholds,"PERSON":True})
    text = "EMP-12345"
    detector = TextDetector(config,backend=FakeBackend([raw("EMPLOYEE_ID",text,text,0.95)]))
    config.thresholds["EMPLOYEE_ID"] = 1.0
    assert detector.detect_message(text).accepted


def test_zero_score_never_promoted_and_rejections_remain_private() -> None:
    text = "Passport 123456789"
    result = TextDetector(backend=FakeBackend([raw("US_PASSPORT",text,"123456789",0)])).detect_message(text)
    assert not result.accepted
    rejection = result.rejected[0]
    assert rejection.reason == "recognizer_invalidated"
    assert "123456789" not in repr(result)
    assert "123456789" not in rejection.candidate.model_dump_json()


@pytest.mark.integration
@pytest.mark.presidio
def test_real_detector_runs_for_all_off_supplied_policy(real_detector) -> None:
    from pii_guard import PolicySnapshot, SanitizeRequest, BUILTIN_RULE_IDS
    request = SanitizeRequest(submission_id=uuid4(),text="Employee EMP-12345",artifacts=[],output_dir=Path("unused"),
        policy=PolicySnapshot(organization_id=uuid4(),version=1,builtins={rule:False for rule in BUILTIN_RULE_IDS},custom_rules=[]))
    result = real_detector.detect(text=request.text)
    assert any(c.rule_id == "EMPLOYEE_ID" for c in result.accepted)
    assert all(not hasattr(c,"action") for c in result.accepted)
