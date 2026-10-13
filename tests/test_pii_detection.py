from pathlib import Path
from types import SimpleNamespace

import pytest

from app.engines.extraction.models import (
    ExtractedPage,
    ExtractionResult,
)

from app.engines.pii_detection import PIIDetectionEngine
from app.engines.pii_detection.models import DetectedPII, PIIDetectionResult, DetectionProcessingError
from app.engines.pii_detection.validation import validate_detection, ValidationDecision, PII_ENTITY_TYPES
from app.engines.pii_detection.recognizers import EmployeeIdRecognizer
from app.engines.extraction.models import OCRTextBlock
from app.engines.redaction import RedactionEngine, RedactionValidationError


class FakeAnalyzer:
    def __init__(self, candidates=None, error=None):
        self.candidates = candidates or {}
        self.calls, self.error = [], error

    def analyze(self, text, language):
        self.calls.append((text, language))
        if self.error:
            raise self.error
        return self.candidates.get(text, [])


def source(*texts):
    return ExtractionResult(Path("synthetic.pdf"), "synthetic.pdf", "pdf", [
        ExtractedPage(i, text, "text") for i, text in enumerate(texts, 1)])


def raw(text, value, entity="PERSON", start=None, score=.85, recognizer="SpacyRecognizer"):
    start = text.index(value) if start is None else start
    return SimpleNamespace(start=start, end=start + len(value), entity_type=entity,
                           score=score, recognition_metadata={"recognizer_name": recognizer})


def detected(value, entity="PERSON"):
    return DetectedPII(entity, value, 0, len(value), .85, "nlp", "synthetic", 1)


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
    assert result.disposition_count == result.raw_candidate_count


@pytest.mark.parametrize("value", ["Miriam T. Achebe", "Tobias Lindqvist", "Anthony P. Brightwell",
                                    "Miriam T.Achebe", "Ana García"])
def test_single_person_original_offsets(value):
    text = "Owner: " + value + "\nApproved"
    result = PIIDetectionEngine(analyzer=FakeAnalyzer({text: [raw(text, value)]})).detect(source(text))
    d = result.detections[0]
    assert (d.text, d.start, d.end, d.page_number) == (value, 7, 7 + len(value), 1)
    assert (d.confidence, d.validation_decision, d.final_decision) == (.85, "CONFIRM", "CONFIRM")
    assert d.validation_reason and d.llm_decision is None


def test_multiple_people_ids_and_repeated_values_no_loss():
    text = "Miriam T. Achebe, Tobias Lindqvist EMP-38104 EMP-40522 EMP-38104"
    candidates = [raw(text, "Miriam T. Achebe"), raw(text, "Tobias Lindqvist"),
                  raw(text, "EMP-38104", "EMPLOYEE_ID"),
                  raw(text, "EMP-40522", "EMPLOYEE_ID"),
                  raw(text, "EMP-38104", "EMPLOYEE_ID", start=text.rindex("EMP-38104"))]
    analyzer = FakeAnalyzer({text: list(reversed(candidates))})
    engine = PIIDetectionEngine(analyzer=analyzer)
    result = engine.detect(source(text))
    assert len(result.detections) == result.raw_candidate_count == result.disposition_count == 5
    assert [d.start for d in result.detections] == sorted(d.start for d in result.detections)
    assert result == engine.detect(source(text))
    assert result.diagnostics == {"raw_candidates": 5, "confirmed": 5, "rejected": 0,
                                  "review": 0, "pages_analyzed": 1}


@pytest.mark.parametrize("entity,value", [("EMAIL_ADDRESS", "ada@example.com"),
    ("PHONE_NUMBER", "+1 (212) 555-0188"), ("US_SSN", "123-45-6789"),
    ("US_PASSPORT", "123456789"), ("US_ITIN", "912-70-1234"),
    ("IBAN_CODE", "GB82WEST12345698765432"), ("CREDIT_CARD", "4111111111111111"),
    ("MEDICAL_LICENSE", "AB1234567")])
def test_supported_policy_entities(entity, value):
    text = "Identifier: " + value
    result = PIIDetectionEngine(analyzer=FakeAnalyzer({text: [raw(text, value, entity)]})).detect(source(text))
    assert result.detections[0].entity_type == entity
    assert result.detections[0].confidence == .85


@pytest.mark.parametrize("value", ["Policyowner", "NED", "RCSA", "Changeandsystemapprovalprocess",
    "Regulatorydeadlines", "HeadofEnterpriseRiskFramework", "Risk Management", "Bank Account"])
def test_invalid_person_business_terms_reject(value):
    result = PIIDetectionEngine(analyzer=FakeAnalyzer({value: [raw(value, value)]})).detect(source(value))
    assert result.rejected[0].final_decision == "REJECT"


@pytest.mark.parametrize("value", ["Brightwell", "Raghavan", "Sorokina", "LI",
    "MIRIAM ACHEBE", "Policyowner:MiriamT.Achebe"])
def test_ambiguous_names_preserve_source_span(value):
    result = PIIDetectionEngine(analyzer=FakeAnalyzer({value: [raw(value, value)]})).detect(source(value))
    d = result.review[0]
    assert (d.text, d.start, d.end, d.validation_decision, d.final_decision) == (
        value, 0, len(value), "AMBIGUOUS", "REVIEW")
    assert not result.rejected and not result.safe_for_llm


@pytest.mark.parametrize("entity,value", [("PERSON", "Brightwell"),
    ("US_BANK_NUMBER", "123456789"), ("US_DRIVER_LICENSE", "A1234567")])
def test_ambiguous_candidates_become_review_without_adjudication(entity, value):
    text = "Identifier: " + value
    result = PIIDetectionEngine(analyzer=FakeAnalyzer({text: [raw(text, value, entity)]})).detect(source(text))
    d = result.review[0]
    assert result.disposition_count == result.raw_candidate_count == 1
    assert d.validation_decision == "AMBIGUOUS"
    assert d.final_decision == "REVIEW"
    assert d.validation_reason
    assert d.llm_decision is None and d.llm_reason is None
    assert not result.detections and not result.rejected
    redacted = RedactionEngine().redact(source(text), result)
    assert not redacted.redaction_complete
    with pytest.raises(RedactionValidationError):
        redacted.to_text_payload()


def test_empty_candidates_empty_page_and_empty_document():
    analyzer = FakeAnalyzer()
    engine = PIIDetectionEngine(analyzer=analyzer)
    result = engine.detect(source("Public policy", "", "  \n"))
    assert result.raw_candidate_count == result.disposition_count == 0
    assert result.pages_analyzed == [1]
    assert analyzer.calls == [("Public policy", "en")]
    assert engine.detect(source()).diagnostics["raw_candidates"] == 0
    assert not result.safe_for_llm


def test_multi_page_all_candidates_and_local_offsets():
    first, last = "Owner: Miriam T. Achebe", "EMP-38104 Brightwell"
    analyzer = FakeAnalyzer({first: [raw(first, "Miriam T. Achebe")],
        last: [raw(last, "EMP-38104", "EMPLOYEE_ID"), raw(last, "Brightwell")]})
    result = PIIDetectionEngine(analyzer=analyzer).detect(source(first, "", last))
    assert result.disposition_count == result.raw_candidate_count == 3
    assert [(d.page_number, d.start) for d in result.detections] == [(1, 7), (3, 0)]
    assert result.review[0].page_number == 3
    assert result.pages_analyzed == [1, 3]


def test_validation_context_bounded(monkeypatch):
    import app.engines.pii_detection.engine as module
    contexts = []
    original = module.validate_detection

    def observing_validation(detection, context, **kwargs):
        contexts.append(context)
        return original(detection, context, **kwargs)

    monkeypatch.setattr(module, "validate_detection", observing_validation)
    text = "x" * 500 + " Brightwell " + "y" * 500
    engine = PIIDetectionEngine(analyzer=FakeAnalyzer({text: [raw(text, "Brightwell")]}))
    result = engine.detect(source(text, text))
    assert len(result.review) == 2
    assert all(len(context) == 400 + len("Brightwell") for context in contexts)


def test_default_analyzer_initialized_once_custom_recognizer_once(monkeypatch):
    import app.engines.pii_detection.engine as module
    registrations, constructors = [], []
    analyzer = FakeAnalyzer()
    analyzer.registry = SimpleNamespace(add_recognizer=registrations.append)
    monkeypatch.setattr(module, "AnalyzerEngine", lambda: constructors.append(True) or analyzer)
    engine = PIIDetectionEngine()
    engine.detect(source("Public policy", "Public text"))
    assert len(constructors) == 1
    assert len(registrations) == 4
    assert isinstance(registrations[0], EmployeeIdRecognizer)


@pytest.mark.parametrize("text,expected", [("(EMP-38104), EMP-40522;\nEMP-38104", 3),
    ("EMP-3810 EMP-381045 XEMP-38104 emp-38104 EMP -38104 EMP- 38104", 2)])
def test_real_employee_recognizer_documented_format(text, expected):
    results = EmployeeIdRecognizer().analyze(text, entities=["EMPLOYEE_ID"])
    assert len(results) == expected
    assert all(text[r.start:r.end] in {"EMP-38104", "EMP-40522", "EMP-3810", "EMP-381045"} for r in results)


def test_real_government_identifier_recognizer():
    from presidio_analyzer.predefined_recognizers import UsSsnRecognizer
    # Format-valid synthetic value, never associated with a real person.
    text = "SSN: 219-09-9999"
    matches = UsSsnRecognizer().analyze(text, entities=["US_SSN"])
    assert matches
    assert all(text[m.start:m.end] == "219-09-9999" for m in matches)
    result = PIIDetectionEngine(analyzer=FakeAnalyzer({text: matches})).detect(source(text))
    assert result.disposition_count == len(matches)
    assert all(d.entity_type == "US_SSN" for d in result.detections)


@pytest.mark.parametrize("entity", ["URL", "DATE_TIME", "ORGANIZATION"])
def test_nonpolicy_entities_are_rejected(entity):
    decision, reason = validate_detection(detected("Business example", entity))
    assert decision == ValidationDecision.REJECT
    assert reason == "entity_type_not_in_pii_policy"


@pytest.mark.parametrize("entity", ["US_DRIVER_LICENSE", "US_BANK_NUMBER"])
@pytest.mark.parametrize("context", ["identifier: 123456789", "Bank account / driver license: 123456789"])
def test_sensitive_numeric_identifiers_not_discarded_without_context(entity, context):
    decision, _ = validate_detection(detected("123456789", entity), context)
    assert decision == ValidationDecision.AMBIGUOUS


def test_explicit_entity_policy_and_legacy_model_construction():
    assert PII_ENTITY_TYPES == {"PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "EMPLOYEE_ID",
        "US_SSN", "US_PASSPORT", "US_DRIVER_LICENSE", "US_ITIN", "US_BANK_NUMBER",
        "IBAN_CODE", "CREDIT_CARD", "MEDICAL_LICENSE", "LOCATION", "NRP", "IP_ADDRESS", "UK_NHS", "CREDENTIAL", "AU_ABN", "AU_ACN", "AU_TFN", "AU_MEDICARE", "ADDRESS", "DATE_OF_BIRTH", "MAC_ADDRESS", "IN_AADHAAR", "IN_PAN", "IN_PASSPORT", "IN_VOTER", "IN_VEHICLE_REGISTRATION"}
    legacy = PIIDetectionResult(Path("x.pdf"), "x.pdf", [], [])
    assert legacy.review == []
    assert detected("Miriam T. Achebe").final_decision is None


@pytest.mark.parametrize("changes", [dict(start=-1), dict(end=100), dict(start=4, end=2),
    dict(start=2, end=2), dict(start=True), dict(score=float("nan")),
    dict(entity_type="PERSON]"), dict(recognition_metadata={"recognizer_name": []})])
def test_invalid_analyzer_candidates_fail_closed(changes):
    text = "Brightwell"
    candidate = raw(text, text)
    candidate.__dict__.update(changes)
    with pytest.raises(DetectionProcessingError):
        PIIDetectionEngine(analyzer=FakeAnalyzer({text: [candidate]})).detect(source(text))


def test_analyzer_failures_are_not_zero_candidates():
    with pytest.raises(DetectionProcessingError, match="page 1.*RuntimeError") as exc:
        PIIDetectionEngine(analyzer=FakeAnalyzer(error=RuntimeError("private page text"))).detect(source("Sensitive example"))
    assert "private" not in str(exc.value)


def test_analyzer_failure_after_successful_page_returns_no_partial_result():
    class FailingSecondPage(FakeAnalyzer):
        def analyze(self, text, language):
            if text == "second":
                raise RuntimeError("failed")
            return [raw(text, text)]
    with pytest.raises(DetectionProcessingError, match="page 2"):
        PIIDetectionEngine(analyzer=FailingSecondPage()).detect(
            source("Miriam T. Achebe", "second"))


def test_invalid_extraction_pages():
    with pytest.raises(DetectionProcessingError, match="required"):
        PIIDetectionEngine(analyzer=FakeAnalyzer()).detect(None)
    extraction = source("a", "b")
    extraction.pages[1].page_number = 1
    with pytest.raises(DetectionProcessingError, match="page"):
        PIIDetectionEngine(analyzer=FakeAnalyzer()).detect(extraction)


def test_ocr_blocks_reliable_mapping_and_cross_block_span():
    text = "Miriam T. Achebe\nEMP-38104"
    extraction = source(text)
    extraction.pages[0].blocks = [OCRTextBlock("Miriam T. Achebe", .9, [[0, 0], [1, 1]]),
                                 OCRTextBlock("EMP-38104", .9, [[0, 1], [1, 2]])]
    candidates = [raw(text, "Miriam T. Achebe"), raw(text, "EMP-38104", "EMPLOYEE_ID"),
                  raw(text, text)]
    engine = PIIDetectionEngine(analyzer=FakeAnalyzer({text: candidates}))
    result = engine.detect(extraction)
    assert [d.source_block for d in result.detections] == [0, 1]
    assert result.review[0].source_block is None
    extraction.pages[0].blocks[0].text = "Different OCR text"
    assert all(d.source_block is None for d in engine.detect(extraction).detections)


def test_overlaps_and_duplicate_candidates_are_all_accounted():
    text = "miriam@example.com"
    candidates = [raw(text, text, "EMAIL_ADDRESS"), raw(text, "example.com", "URL"),
                  raw(text, text, "EMAIL_ADDRESS")]
    result = PIIDetectionEngine(analyzer=FakeAnalyzer({text: candidates})).detect(source(text))
    assert result.disposition_count == result.raw_candidate_count == 3
    assert len(result.detections) == 2 and len(result.rejected) == 1
    redacted = RedactionEngine().redact(source(text), result)
    assert redacted.full_text == "[EMAIL_ADDRESS_001]"
    assert len(redacted.issues) == 1 and not redacted.issues[0].blocking


def test_synthetic_end_to_end_decisions_and_audit_mapping():
    text = "Owner: Miriam T. Achebe\nPolicyowner\nChair: Brightwell"
    analyzer = FakeAnalyzer({text: [raw(text, "Miriam T. Achebe"), raw(text, "Policyowner"),
                                    raw(text, "Brightwell")]})
    result = PIIDetectionEngine(analyzer=analyzer).detect(source(text))
    assert result.diagnostics["raw_candidates"] == result.disposition_count == 3
    assert (len(result.detections), len(result.rejected), len(result.review)) == (1, 1, 1)
    redacted = RedactionEngine().redact(source(text), result)
    assert redacted.full_text == "Owner: [PERSON_001]\nPolicyowner\nChair: [PERSON_002]"
    assert redacted.tag_mapping["[PERSON_001]"][0] == result.detections[0]
    assert redacted.issues[0].code == "review_required"
    assert not redacted.redaction_complete
    with pytest.raises(RedactionValidationError):
        redacted.to_text_payload()


def test_final_disposition_conflict_blocks_engine4():
    item = detected("Miriam T. Achebe")
    item.validation_decision = "CONFIRM"
    item.final_decision = "REJECT"
    result = PIIDetectionResult(Path("synthetic.pdf"), "synthetic.pdf", [item], [])
    redacted = RedactionEngine().redact(source(item.text), result)
    assert not redacted.redaction_complete

def test_deprecated_fields_retained_but_never_populated():
    from dataclasses import fields
    metadata = {field.name: field.metadata for field in fields(DetectedPII)}
    assert metadata["llm_decision"]["deprecated"]
    assert metadata["llm_reason"]["deprecated"]
    text = "Miriam T. Achebe EMP-00001 Brightwell"
    analyzer = FakeAnalyzer({text: [raw(text, "Miriam T. Achebe"),
        raw(text, "EMP-00001", "EMPLOYEE_ID"), raw(text, "Brightwell")]})
    result = PIIDetectionEngine(analyzer=analyzer).detect(source(text))
    assert all(d.llm_decision is None and d.llm_reason is None
               for d in result.detections + result.rejected + result.review)


def test_detection_without_generative_dependencies_in_fresh_process():
    # Installed NLP libraries can probe optional packages. Prove the actual
    # default analyzer works when the generative stack is entirely unavailable.
    import subprocess
    import sys
    code = """
import importlib.abc
import sys
class UnavailableGenerativeStack(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "transformers", "accelerate", "tokenizers", "safetensors"}:
            raise ModuleNotFoundError("Optional generative dependency unavailable", name=fullname)
sys.meta_path.insert(0, UnavailableGenerativeStack())
from pathlib import Path
from app.engines.extraction.models import ExtractionResult, ExtractedPage
from app.engines.pii_detection import PIIDetectionEngine
source = ExtractionResult(Path("synthetic.pdf"), "synthetic.pdf", "pdf",
    [ExtractedPage(1, "Email: ada@example.com EMP-00001", "text")])
result = PIIDetectionEngine().detect(source)
assert {"EMAIL_ADDRESS", "EMPLOYEE_ID"} <= {d.entity_type for d in result.detections}
assert result.disposition_count == result.raw_candidate_count
assert not any(name.split(".")[0] in {"transformers", "torch", "accelerate", "tokenizers", "safetensors"}
               for name in sys.modules)
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    

def test_custom_manager_rules_confirm_exact_and_regex_matches():
    engine=PIIDetectionEngine(analyzer=FakeAnalyzer(),custom_rules=[
        {'name':'Demo secret','pattern':'DemoOnly123!'},
        {'name':'Staff code','pattern':r'STAFF-\d{4}','is_regex':True},
    ])
    result=engine.detect(source('Secret DemoOnly123! belongs to STAFF-2048.'))
    assert result.raw_candidate_count==2
    assert {value.entity_type for value in result.detections}=={'CUSTOM_BLOCKED'}
    assert all(value.validation_decision==ValidationDecision.CONFIRM for value in result.detections)


def test_invalid_or_expensive_manager_regex_does_not_silently_release():
    for pattern,text in [('[','Sensitive content'),('(a+)+$', 'a'*10000+'!')]:
        engine=PIIDetectionEngine(analyzer=FakeAnalyzer(),custom_rules=[{'name':'Invalid','pattern':pattern,'is_regex':True}])
        with pytest.raises(DetectionProcessingError):engine.detect(source(text))
