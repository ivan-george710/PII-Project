from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pii_guard import (
    BUILTIN_RULE_IDS,
    DEFAULT_BUILTIN_RULES,
    ArtifactInput,
    CustomRule,
    Finding,
    PolicySnapshot,
    ProcessingError,
    ProcessingErrorCode,
    SanitizedArtifact,
    SanitizeRequest,
    SanitizeResult,
    SourceLocation,
)
from pii_guard import CustomRuleEvaluator, PolicyEvaluator, validate_custom_rule
from pii_guard.rules.custom import CustomCandidate, MatchBudget
from pii_guard.detection.validation import DetectionCandidate
from pii_guard.models import ExtractedTextBlock
from time import monotonic


def test_builtin_rule_ids_match_issue_contract() -> None:
    assert BUILTIN_RULE_IDS == (
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "EMPLOYEE_ID",
        "US_SSN",
        "US_PASSPORT",
        "US_DRIVER_LICENSE",
        "US_ITIN",
        "US_BANK_NUMBER",
        "IBAN_CODE",
        "CREDIT_CARD",
        "MEDICAL_LICENSE",
        "FACE",
    )
    assert DEFAULT_BUILTIN_RULES == {rule_id: True for rule_id in BUILTIN_RULE_IDS}


def test_policy_snapshot_accepts_exact_builtin_set(
    builtins_all_enabled: dict[str, bool],
) -> None:
    policy = PolicySnapshot(
        organization_id=uuid4(),
        version=1,
        builtins=builtins_all_enabled,
        custom_rules=[],
    )

    assert set(policy.builtins) == set(BUILTIN_RULE_IDS)


def test_policy_snapshot_rejects_missing_builtin(
    builtins_all_enabled: dict[str, bool],
) -> None:
    builtins_all_enabled.pop("FACE")

    with pytest.raises(ValidationError):
        PolicySnapshot(
            organization_id=uuid4(),
            version=1,
            builtins=builtins_all_enabled,
            custom_rules=[],
        )


def test_policy_snapshot_rejects_unknown_builtin(
    builtins_all_enabled: dict[str, bool],
) -> None:
    payload = {
        "organization_id": str(uuid4()),
        "version": 1,
        "builtins": {**builtins_all_enabled, "UNKNOWN": True},
        "custom_rules": [],
    }

    with pytest.raises(ValidationError):
        PolicySnapshot.model_validate(payload)


def test_policy_snapshot_rejects_boolean_strings(
    builtins_all_enabled: dict[str, bool],
) -> None:
    payload = {
        "organization_id": str(uuid4()),
        "version": 1,
        "builtins": {**builtins_all_enabled, "FACE": "false"},
        "custom_rules": [],
    }

    with pytest.raises(ValidationError):
        PolicySnapshot.model_validate(payload)


def test_policy_snapshot_rejects_integer_strings(
    builtins_all_enabled: dict[str, bool],
) -> None:
    payload = {
        "organization_id": str(uuid4()),
        "version": "1",
        "builtins": builtins_all_enabled,
        "custom_rules": [],
    }

    with pytest.raises(ValidationError):
        PolicySnapshot.model_validate(payload)


def test_policy_snapshot_accepts_all_rules_disabled(
    builtins_all_enabled: dict[str, bool],
) -> None:
    policy = PolicySnapshot(
        organization_id=uuid4(),
        version=1,
        builtins={rule_id: False for rule_id in builtins_all_enabled},
        custom_rules=[],
    )

    assert all(enabled is False for enabled in policy.builtins.values())


def test_custom_rule_trims_name_and_enforces_limits() -> None:
    rule = CustomRule(
        id=uuid4(),
        name="  Finance code  ",
        kind="regex",
        pattern=r"FIN-\d+",
        case_sensitive=True,
        enabled=False,
    )

    assert rule.name == "Finance code"

    with pytest.raises(ValidationError):
        CustomRule(
            id=uuid4(),
            name="x" * 81,
            kind="exact",
            pattern="value",
            case_sensitive=True,
            enabled=True,
        )


def test_policy_snapshot_rejects_too_many_custom_rules(
    builtins_all_enabled: dict[str, bool],
) -> None:
    custom_rules = [
        CustomRule(
            id=uuid4(),
            name=f"Rule {index}",
            kind="exact",
            pattern=f"value-{index}",
            case_sensitive=False,
            enabled=True,
        )
        for index in range(101)
    ]

    with pytest.raises(ValidationError):
        PolicySnapshot(
            organization_id=uuid4(),
            version=1,
            builtins=builtins_all_enabled,
            custom_rules=custom_rules,
        )


def test_policy_snapshot_rejects_duplicate_custom_rule_ids(
    builtins_all_enabled: dict[str, bool],
) -> None:
    rule_id = uuid4()
    custom_rules = [
        CustomRule(
            id=rule_id,
            name="Rule A",
            kind="exact",
            pattern="alpha",
            case_sensitive=False,
            enabled=True,
        ),
        CustomRule(
            id=rule_id,
            name="Rule B",
            kind="exact",
            pattern="beta",
            case_sensitive=False,
            enabled=True,
        ),
    ]

    with pytest.raises(ValidationError):
        PolicySnapshot(
            organization_id=uuid4(),
            version=1,
            builtins=builtins_all_enabled,
            custom_rules=custom_rules,
        )


def test_artifact_input_requires_basename(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        ArtifactInput(
            id=uuid4(),
            filename="../secret.pdf",
            source_path=tmp_path / "secret.pdf",
            declared_mime="application/pdf",
        )


def test_sanitize_request_requires_text_or_artifact(
    policy_snapshot: PolicySnapshot,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError):
        SanitizeRequest(
            submission_id=uuid4(),
            text="   ",
            artifacts=[],
            policy=policy_snapshot,
            output_dir=tmp_path,
        )


def test_sanitize_request_rejects_more_than_five_artifacts(
    policy_snapshot: PolicySnapshot,
    tmp_path: Path,
) -> None:
    artifacts = [
        ArtifactInput(
            id=uuid4(),
            filename=f"file-{index}.pdf",
            source_path=tmp_path / f"file-{index}.pdf",
            declared_mime="application/pdf",
        )
        for index in range(6)
    ]

    with pytest.raises(ValidationError):
        SanitizeRequest(
            submission_id=uuid4(),
            text="",
            artifacts=artifacts,
            policy=policy_snapshot,
            output_dir=tmp_path,
        )


def test_source_location_validates_text_span_and_bbox_bounds() -> None:
    location = SourceLocation(
        artifact_id=None,
        kind="message",
        page_number=None,
        slide_number=None,
        source_ref=None,
        start=0,
        end=5,
        bbox=None,
    )

    assert location.start == 0

    with pytest.raises(ValidationError):
        SourceLocation(
            artifact_id=None,
            kind="message",
            page_number=None,
            slide_number=None,
            source_ref=None,
            start=5,
            end=5,
            bbox=None,
        )

    with pytest.raises(ValidationError):
        SourceLocation(
            artifact_id=uuid4(),
            kind="face",
            page_number=1,
            slide_number=None,
            source_ref="page:1",
            start=None,
            end=None,
            bbox=(0.8, 0.8, 0.3, 0.3),
        )

    with pytest.raises(ValidationError):
        SourceLocation.model_validate(
            {
                "artifact_id": None,
                "kind": "message",
                "page_number": None,
                "slide_number": None,
                "source_ref": None,
                "start": "0",
                "end": 5,
                "bbox": None,
            }
        )


def test_finding_and_sanitize_result_public_contract(tmp_path: Path) -> None:
    finding = Finding(
        id=uuid4(),
        rule_id="EMAIL_ADDRESS",
        category="contact",
        confidence=0.91,
        recognizer="Presidio",
        location=SourceLocation(
            artifact_id=None,
            kind="message",
            page_number=None,
            slide_number=None,
            source_ref=None,
            start=7,
            end=25,
            bbox=None,
        ),
        action="redacted",
    )
    artifact = SanitizedArtifact(
        artifact_id=uuid4(),
        filename="safe.pdf",
        mime_type="application/pdf",
        output_path=tmp_path / "safe.pdf",
        size_bytes=1,
        sha256="a" * 64,
        format_changed=False,
    )
    result = SanitizeResult(
        submission_id=uuid4(),
        policy_version=1,
        sanitized_text="[REDACTED]",
        artifacts=[artifact],
        findings=[finding],
        warnings=[],
    )

    dumped = result.model_dump(mode="json")

    assert dumped["findings"][0]["rule_id"] == "EMAIL_ADDRESS"
    assert "text" not in dumped["findings"][0]


def test_processing_error_carries_safe_context() -> None:
    submission_id = uuid4()
    artifact_id = uuid4()
    error = ProcessingError(
        ProcessingErrorCode.UNSUPPORTED_FILE,
        "Unsupported file type",
        submission_id=submission_id,
        artifact_id=artifact_id,
    )

    assert error.code is ProcessingErrorCode.UNSUPPORTED_FILE
    assert error.message == "Unsupported file type"
    assert error.submission_id == submission_id
    assert error.artifact_id == artifact_id


def _rule(pattern: str, *, kind: str = "exact", case_sensitive: bool = True,
          enabled: bool = True) -> CustomRule:
    return CustomRule(id=uuid4(), name="Synthetic rule", kind=kind, pattern=pattern,
                      case_sensitive=case_sensitive, enabled=enabled)


def _policy(*rules: CustomRule, enabled: bool = True) -> PolicySnapshot:
    return PolicySnapshot(organization_id=uuid4(), version=7,
        builtins={rule:enabled for rule in BUILTIN_RULE_IDS}, custom_rules=list(rules))


def _location(start: int, end: int, *, identity=None, ref=None, kind="message", bbox=None) -> SourceLocation:
    return SourceLocation(artifact_id=identity, kind=kind, page_number=1 if identity else None,
        slide_number=None, source_ref=ref, start=start, end=end, bbox=bbox)


def _candidate(start=0, end=9, *, location=None, score=0.95) -> DetectionCandidate:
    candidate = DetectionCandidate(rule_id="EMPLOYEE_ID", category="employee_identifier",
        confidence=score, recognizer_confidence=score, recognizer="CadenceEmployeeIdRecognizer",
        location=location or _location(start,end))
    candidate._matched_text = "EMP-12345"
    return candidate


@pytest.mark.parametrize("pattern", ["a+b[1](x)?", "cost $5.00", "a.*b", "^SECRET$", "C:\\private\\file"])
def test_custom_exact_is_literal(pattern: str) -> None:
    with CustomRuleEvaluator([_rule(pattern)]) as evaluator:
        matches = evaluator.match(text=f"before {pattern} after")
    assert len(matches) == 1
    assert matches[0].matched_text == pattern
    assert matches[0].location.start == 7


@pytest.mark.parametrize("kind", ["exact","regex"])
@pytest.mark.parametrize("case_sensitive,expected", [(True,1),(False,2)])
def test_custom_case_sensitivity(kind: str, case_sensitive: bool, expected: int) -> None:
    with CustomRuleEvaluator([_rule("Secret",kind=kind,case_sensitive=case_sensitive)]) as evaluator:
        matches = evaluator.match(text="Secret secret")
    assert len(matches) == expected


@pytest.mark.parametrize("kind", ["exact","regex"])
def test_custom_unicode_casefold_expansion_preserves_offsets(kind: str) -> None:
    text = "\U0001f600 Stra\u00dfe\nSTRASSE"
    with CustomRuleEvaluator([_rule("STRASSE",kind=kind,case_sensitive=False)]) as evaluator:
        matches = evaluator.match(text=text)
    assert [(m.location.start,m.location.end) for m in matches] == [(2,8),(9,16)]
    assert [m.matched_text for m in matches] == ["Stra\u00dfe","STRASSE"]
    assert all(text[m.location.start:m.location.end] == m.matched_text for m in matches)


def test_custom_unicode_multiline_exact_and_regex() -> None:
    text = "\U0001f600 e\u0301\nline.one\nline.two end"
    rules = [_rule("line.one\nline.two"),_rule(r"line\.one\nline\.two",kind="regex")]
    with CustomRuleEvaluator(rules) as evaluator:
        matches = evaluator.match(text=text)
    assert len(matches) == 2
    assert all(m.location.start == text.index("line.one") for m in matches)
    assert all(m.matched_text == "line.one\nline.two" for m in matches)


@pytest.mark.parametrize("pattern", ["(","[", "a*", "x?", "^$", "a|", "(?=secret)", "(?<=x)", r"\b", "(?:a{0})"])
def test_invalid_or_empty_matching_regex_rejected(pattern: str) -> None:
    with pytest.raises(ProcessingError) as error:
        validate_custom_rule(_rule(pattern,kind="regex",enabled=False))
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY
    assert pattern not in error.value.message


def test_custom_overlapping_matches_and_disabled_rules_still_run() -> None:
    rule = _rule("aba",enabled=False)
    with CustomRuleEvaluator([rule]) as evaluator:
        matches = evaluator.match(text="ababa")
    assert [(m.location.start,m.location.end) for m in matches] == [(0,3),(2,5)]
    assert all(m.rule_id == f"custom:{rule.id}" for m in matches)


@pytest.mark.parametrize("operation", ["validate", "match"])
def test_worker_watchdog_bounds_validation_and_cleans_process(operation: str) -> None:
    from pii_guard.rules.custom import _RegexWorker, REGEX_TIMEOUT_SECONDS
    worker = _RegexWorker(uuid4())
    original = worker.connection
    waits = []
    class NoReply:
        def send(self, value): original.send(value)
        def poll(self, timeout):
            waits.append(timeout)
            return False
        def close(self): original.close()
    worker.connection = NoReply()
    with pytest.raises(ProcessingError) as error:
        worker.request(operation,_rule("x",kind="regex"),"x")
    assert error.value.code == ProcessingErrorCode.PROCESSING_TIMEOUT
    assert waits and 0 <= waits[0] <= REGEX_TIMEOUT_SECONDS == 0.100
    assert not worker.process.is_alive()


def test_regex_engine_receives_100ms_total_iteration_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import pii_guard.rules.custom as module
    calls = []
    class Match:
        def span(self): return (0,1)
    class Pattern:
        def finditer(self, text, *, overlapped, timeout):
            calls.append((overlapped,timeout))
            return iter([Match()])
    monkeypatch.setattr(module.regex,"compile",lambda *args:Pattern())
    class Connection:
        def __init__(self):
            self.requests = iter([("validate","x","regex",True,""),("match","x","regex",True,"x")])
            self.responses = []
        def recv(self):
            try: return next(self.requests)
            except StopIteration: raise EOFError
        def send(self, value): self.responses.append(value)
        def close(self): pass
    connection = Connection()
    module._worker_main(connection)
    assert calls == [(True,0.100)]
    assert connection.responses[-1] == ("ok",[(0,1)])


@pytest.mark.integration
def test_real_catastrophic_regex_times_out_and_terminates_worker() -> None:
    with CustomRuleEvaluator([_rule(r"(a|aa)+$",kind="regex")]) as evaluator:
        started = monotonic()
        with pytest.raises(ProcessingError) as error:
            evaluator.match(text="a" * 2000 + "!")
        elapsed = monotonic() - started
        assert error.value.code == ProcessingErrorCode.PROCESSING_TIMEOUT
        assert elapsed < 1.5  # Includes OS scheduling and process termination, not just regex work.
        assert not evaluator._worker.process.is_alive()


def test_exactly_10000_custom_matches_allowed() -> None:
    with CustomRuleEvaluator([_rule("X")]) as evaluator:
        matches = evaluator.match(text="X" * 10000)
    assert len(matches) == 10000


def test_10001_custom_matches_fail_without_partial_success() -> None:
    with CustomRuleEvaluator([_rule("X")]) as evaluator:
        with pytest.raises(ProcessingError) as error:
            evaluator.match(text="X" * 10001)
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY


def test_submission_budget_combines_builtin_and_custom_matches() -> None:
    policy = _policy(_rule("X"))
    candidates = [_candidate(index,index+1) for index in range(10000)]
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(policy).evaluate(candidates,text="X")
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY


def test_shared_budget_across_custom_units_and_calls() -> None:
    budget = MatchBudget()
    with CustomRuleEvaluator([_rule("X")]) as evaluator:
        evaluator.match(text="X" * 10000,budget=budget)
        source = ExtractedTextBlock(text="X",extraction_method="native_text",
            location=_location(0,1,identity=uuid4(),ref="docx:p:0",kind="native_text"))
        with pytest.raises(ProcessingError):
            evaluator.match(blocks=[source],budget=budget)
    assert budget.count == 10001


@pytest.mark.parametrize("enabled", [True,False])
def test_all_on_and_all_off_policy(enabled: bool) -> None:
    rule = _rule("EMP-12345",enabled=enabled)
    result = PolicyEvaluator(_policy(rule,enabled=enabled)).evaluate([_candidate()],text="EMP-12345")
    assert len(result.findings) == 2
    assert {f.action for f in result.findings} == {"redacted" if enabled else "allowed_disabled"}
    assert len(result.redaction_targets) == (2 if enabled else 0)
    assert result.policy_version == 7


def test_enabled_precedence_disabled_overlaps_remain_events() -> None:
    rule = _rule("EMP-12345",enabled=False)
    result = PolicyEvaluator(_policy(rule)).evaluate([_candidate()],text="EMP-12345")
    assert [f.action for f in result.findings] == ["redacted","allowed_disabled"]
    assert len(result.redaction_targets) == 1
    assert result.redaction_targets[0].location.start == 0
    assert result.redaction_targets[0].location.end == 9
    assert result.redaction_targets[0].finding_id == result.findings[0].id


def test_duplicates_collapse_distinct_rule_and_contained_spans_preserved() -> None:
    rule = _rule("EMP-12345")
    result = PolicyEvaluator(_policy(rule)).evaluate([_candidate(),_candidate(score=0.96),_candidate(end=5)],text="EMP-12345")
    assert len(result.findings) == 3
    assert result.findings[0].confidence == 0.96
    assert len(result.redaction_targets) == 3


def test_no_raw_content_in_public_serialization() -> None:
    secret = "EMP-12345"
    result = PolicyEvaluator(_policy(_rule(secret))).evaluate([_candidate()],text=secret)
    dumped = result.model_dump_json()
    assert secret not in dumped
    assert "redaction_targets" not in dumped
    assert all("matched_text" not in f.model_dump_json() for f in result.findings)


def test_policy_snapshot_immutable_against_nested_mutation() -> None:
    rule = _rule("EMP-12345")
    policy = _policy(rule)
    evaluator = PolicyEvaluator(policy)
    policy.version = 99
    policy.builtins["EMPLOYEE_ID"] = False
    rule.enabled = False
    policy.custom_rules[0].enabled = False
    policy.custom_rules[0].pattern = "changed"
    result = evaluator.evaluate([_candidate()],text="EMP-12345")
    assert result.policy_version == 7
    assert len(result.findings) == 2
    assert all(f.action == "redacted" for f in result.findings)
    with pytest.raises(ProcessingError):
        evaluator.evaluate()


def test_unknown_custom_id_fails_closed() -> None:
    unknown = CustomCandidate(rule_id=f"custom:{uuid4()}",recognizer="CustomExactRecognizer",location=_location(0,5))
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(_policy()).evaluate([_candidate(),unknown])
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY


def test_mutated_malformed_policy_and_candidate_rejected() -> None:
    policy = _policy()
    policy.builtins["EMPLOYEE_ID"] = "false"
    with pytest.raises(ProcessingError):
        PolicyEvaluator(policy)
    candidate = _candidate()
    candidate.category = "SECRET"
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(_policy()).evaluate([candidate])
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY
    assert "SECRET" not in str(error.value)


@pytest.mark.parametrize("kind", ["native_text","ocr"])
def test_custom_policy_preserves_artifact_sources_and_coordinates(kind: str) -> None:
    text = "\U0001f600 EMP-12345"
    identity = uuid4()
    bbox = (0.1,0.2,0.3,0.4) if kind == "ocr" else None
    source = ExtractedTextBlock(text=text,extraction_method=kind,
        location=_location(0,len(text),identity=identity,ref=f"pdf:page:1:{kind}",kind=kind,bbox=bbox))
    result = PolicyEvaluator(_policy(_rule("EMP-12345"))).evaluate(blocks=[source])
    location = result.findings[0].location
    assert (location.start,location.end) == (2,11)
    assert location.artifact_id == identity
    assert location.source_ref == source.location.source_ref
    assert location.bbox == bbox
    assert location.page_number == 1
    assert result.redaction_targets[0].location == location


def test_invalid_disabled_regex_fails_even_without_content() -> None:
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(_policy(_rule("a*",kind="regex",enabled=False))).evaluate([_candidate()])
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY


@pytest.mark.integration
def test_disabled_custom_timeout_fails_whole_policy_evaluation() -> None:
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(_policy(_rule(r"(a|aa)+$",kind="regex",enabled=False))).evaluate([_candidate()],text="a" * 2000 + "!")
    assert error.value.code == ProcessingErrorCode.PROCESSING_TIMEOUT


@pytest.mark.parametrize("rule_id", BUILTIN_RULE_IDS)
@pytest.mark.parametrize("enabled", [True,False])
def test_each_builtin_policy_toggle_resolves(rule_id: str, enabled: bool) -> None:
    from pii_guard.rules.builtins import BUILTIN_RULE_CATEGORIES
    location = _location(0,3)
    if rule_id == "FACE":
        location = SourceLocation(artifact_id=uuid4(),kind="face",page_number=1,slide_number=None,
            source_ref="image",start=None,end=None,bbox=(0.1,0.2,0.3,0.4))
    candidate = DetectionCandidate(rule_id=rule_id,category=BUILTIN_RULE_CATEGORIES[rule_id],
        confidence=0.99,recognizer_confidence=0.99,recognizer="Synthetic",location=location)
    result = PolicyEvaluator(_policy(enabled=enabled)).evaluate([candidate])
    assert result.findings[0].action == ("redacted" if enabled else "allowed_disabled")
    assert len(result.redaction_targets) == int(enabled)


@pytest.mark.parametrize("pattern,case_sensitive", [("(?i)secret",True),("(?i:secret)",True),("(?-i:secret)",False)])
def test_regex_inline_flags_cannot_override_case_sensitive(pattern: str, case_sensitive: bool) -> None:
    with pytest.raises(ProcessingError) as error:
        validate_custom_rule(_rule(pattern,kind="regex",case_sensitive=case_sensitive))
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY


def test_regex_multiline_anchors_and_nonempty_lookaround() -> None:
    with CustomRuleEvaluator([_rule(r"(?m)^secret$",kind="regex"),_rule(r"(?<=x)secret",kind="regex")]) as evaluator:
        matches = evaluator.match(text="before\nsecret\nxsecret")
    assert [(m.location.start,m.location.end) for m in matches] == [(7,13),(15,21)]


def test_same_text_different_sources_not_deduplicated() -> None:
    identity = uuid4()
    sources = [ExtractedTextBlock(text="SECRET",extraction_method="native_text",
        location=_location(0,6,identity=identity,ref=ref,kind="native_text")) for ref in ("first","second")]
    result = PolicyEvaluator(_policy(_rule("SECRET"))).evaluate(blocks=[*sources,sources[0]])
    assert len(result.findings) == 2
    assert {f.location.source_ref for f in result.findings} == {"first","second"}


def test_duplicate_candidates_do_not_exhaust_budget() -> None:
    result = PolicyEvaluator(_policy()).evaluate([_candidate()] * 10001)
    assert len(result.findings) == 1


def test_conflicting_duplicate_source_geometry_fails_closed() -> None:
    identity = uuid4()
    first = _candidate(location=_location(0,9,identity=identity,ref="ocr",kind="ocr",bbox=(0.1,0.1,0.2,0.2)))
    second = _candidate(location=_location(0,9,identity=identity,ref="ocr",kind="ocr",bbox=(0.2,0.1,0.2,0.2)))
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(_policy()).evaluate([first,second])
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY


def test_worker_closed_after_success_and_invalid_policy() -> None:
    with CustomRuleEvaluator([_rule("SECRET")]) as evaluator:
        assert evaluator.match(text="SECRET")
    assert not evaluator._worker.process.is_alive()
    with pytest.raises(ProcessingError):
        evaluator.match(text="SECRET")


def test_custom_rules_cannot_span_extraction_blocks() -> None:
    identity = uuid4()
    sources = [ExtractedTextBlock(text=text,extraction_method="native_text",
        location=_location(0,len(text),identity=identity,ref=str(index),kind="native_text"))
        for index,text in enumerate(("SEC","RET"))]
    assert not PolicyEvaluator(_policy(_rule("SECRET"))).evaluate(blocks=sources).findings


def test_snapshot_custom_candidate_input_supported() -> None:
    rule = _rule("SECRET",enabled=False)
    with CustomRuleEvaluator([rule]) as matcher:
        candidates = matcher.match(text="SECRET")
    result = PolicyEvaluator(_policy(rule)).evaluate(candidates)
    assert len(result.findings) == 1
    assert result.findings[0].action == "allowed_disabled"


def test_custom_conflicting_duplicate_geometry_fails_closed() -> None:
    identity = uuid4()
    blocks = [ExtractedTextBlock(text="SECRET", extraction_method="ocr",
        location=_location(0, 6, identity=identity, ref="same-block", kind="ocr", bbox=box))
        for box in ((0.1, 0.1, 0.2, 0.2), (0.2, 0.1, 0.2, 0.2))]
    submission_id = uuid4()
    with CustomRuleEvaluator([_rule("SECRET")], submission_id=submission_id) as evaluator:
        with pytest.raises(ProcessingError) as error:
            evaluator.match(blocks=blocks)
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY
    assert error.value.submission_id == submission_id
    assert error.value.artifact_id == identity


def test_distinct_face_regions_remain_separate_policy_events() -> None:
    # Synthetic candidates exercise policy consumption, not face detection.
    identity = uuid4()
    candidates = [DetectionCandidate(rule_id="FACE", category="biometric",
        confidence=0.99, recognizer_confidence=0.99, recognizer="Synthetic",
        location=SourceLocation(artifact_id=identity, kind="face", page_number=1,
            slide_number=None, source_ref="image", start=None, end=None, bbox=box))
        for box in ((0.1, 0.1, 0.2, 0.2), (0.2, 0.1, 0.2, 0.2))]
    result = PolicyEvaluator(_policy()).evaluate([*candidates, candidates[0]])
    assert len(result.findings) == len(result.redaction_targets) == 2
    assert [finding.location.bbox for finding in result.findings] == [c.location.bbox for c in candidates]


@pytest.mark.parametrize("rule_id", ["FACE", "EMPLOYEE_ID", "custom"])
def test_rule_location_kind_mismatch_fails_closed(rule_id: str) -> None:
    rule = _rule("SECRET")
    face_location = SourceLocation(artifact_id=uuid4(), kind="face", page_number=1,
        slide_number=None, source_ref="image", start=None, end=None, bbox=(0.1, 0.1, 0.2, 0.2))
    if rule_id == "custom":
        candidate = CustomCandidate(rule_id=f"custom:{rule.id}", recognizer="Synthetic", location=face_location)
    else:
        candidate = DetectionCandidate(rule_id=rule_id,
            category="biometric" if rule_id == "FACE" else "employee_identifier",
            confidence=0.99, recognizer_confidence=0.99, recognizer="Synthetic",
            location=_location(0, 6) if rule_id == "FACE" else face_location)
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(_policy(rule)).evaluate([candidate])
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY


def test_mocked_regex_timeout_after_match_returns_no_partial_result(monkeypatch: pytest.MonkeyPatch) -> None:
    import pii_guard.rules.custom as module

    class Match:
        def span(self): return (0, 1)

    class Pattern:
        def finditer(self, text, *, overlapped, timeout):
            assert timeout == 0.100
            yield Match()
            raise TimeoutError

    class Connection:
        def __init__(self):
            self.requests = iter([("validate", "x", "regex", True, ""), ("match", "x", "regex", True, "xx")])
            self.responses = []
        def recv(self):
            try: return next(self.requests)
            except StopIteration: raise EOFError
        def send(self, value): self.responses.append(value)
        def close(self): pass

    monkeypatch.setattr(module.regex, "compile", lambda *args: Pattern())
    connection = Connection()
    module._worker_main(connection)
    assert connection.responses == [("ready", None), ("ok", None), ("timeout", None)]


def test_mocked_policy_timeout_discards_accepted_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    import pii_guard.rules.custom as module
    submission_id = uuid4()

    class Worker:
        def __init__(self, submission_id): self.submission_id = submission_id
        def request(self, operation, rule, text=""):
            if operation == "validate": return []
            raise ProcessingError(ProcessingErrorCode.PROCESSING_TIMEOUT,
                "Custom rule execution exceeded 100ms.", submission_id=self.submission_id)
        def close(self): pass

    monkeypatch.setattr(module, "_RegexWorker", Worker)
    evaluator = PolicyEvaluator(_policy(_rule("SECRET", enabled=False)), submission_id=submission_id)
    with pytest.raises(ProcessingError) as error:
        evaluator.evaluate([_candidate()], text="SECRET")
    assert error.value.code == ProcessingErrorCode.PROCESSING_TIMEOUT
    assert error.value.submission_id == submission_id
    assert "SECRET" not in str(error.value)
    with pytest.raises(ProcessingError):
        evaluator.evaluate()


def test_disabled_rules_share_submission_match_limit() -> None:
    rules = [_rule("X", enabled=False), _rule("X", enabled=False)]
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(_policy(*rules, enabled=False)).evaluate(text="X" * 5001)
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY


def test_conflicting_source_text_rejected_even_without_matches() -> None:
    identity = uuid4()
    location = _location(0, 6, identity=identity, ref="same-block", kind="native_text")
    blocks = [ExtractedTextBlock(text=text, extraction_method="native_text", location=location)
              for text in ("before", "after!")]
    with pytest.raises(ProcessingError) as error:
        PolicyEvaluator(_policy(_rule("SECRET"))).evaluate(blocks=blocks)
    assert error.value.code == ProcessingErrorCode.INVALID_POLICY
    assert error.value.artifact_id == identity
    assert "before" not in str(error.value)
    assert "after!" not in str(error.value)


def test_mocked_watchdog_rejects_success_received_after_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    import pii_guard.rules.custom as module
    # No process or clock scheduling: a successful reply arrives after 101ms.
    worker = object.__new__(module._RegexWorker)
    worker.submission_id = uuid4()
    closed = []
    worker.close = lambda: closed.append(True)
    times = iter([0.0, 0.001, 0.101])
    monkeypatch.setattr(module, "monotonic", lambda: next(times))

    class Connection:
        def send(self, value): pass
        def poll(self, timeout):
            assert timeout == pytest.approx(0.099)
            return True
        def recv(self): return ("ok", [(0, 1)])

    worker.connection = Connection()
    with pytest.raises(ProcessingError) as error:
        worker.request("match", _rule("X"), "X")
    assert error.value.code == ProcessingErrorCode.PROCESSING_TIMEOUT
    assert closed == [True]
