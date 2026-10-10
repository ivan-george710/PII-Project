from __future__ import annotations

import multiprocessing as mp
import re
from collections.abc import Iterable
from dataclasses import dataclass
from time import monotonic
from typing import Annotated
from uuid import UUID

import regex
from pydantic import Field, PrivateAttr, TypeAdapter

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import CustomRule, EngineBaseModel, ExtractedTextBlock, SourceLocation


REGEX_TIMEOUT_SECONDS = 0.100
MAX_SUBMISSION_MATCHES = 10000
CUSTOM_CATEGORY = "custom"


class CustomCandidate(EngineBaseModel):
    """Private processing output; raw matched content never enters event JSON."""

    rule_id: str
    category: str = CUSTOM_CATEGORY
    confidence: Annotated[float, Field(ge=0, le=1)] = 1.0
    recognizer: str
    location: SourceLocation
    _matched_text: str = PrivateAttr(default="")

    @property
    def matched_text(self) -> str:
        return self._matched_text


def candidate_key(candidate: object) -> tuple:
    location = candidate.location
    return (candidate.rule_id, location.artifact_id, location.kind,
            location.page_number, location.slide_number, location.source_ref,
            location.start, location.end,
            location.bbox if location.kind == "face" else None)


@dataclass
class MatchBudget:
    """One submission-wide budget, counting distinct accepted matches."""

    submission_id: UUID | None = None

    def __post_init__(self) -> None:
        self._keys: dict[tuple, tuple | None] = {}

    @property
    def count(self) -> int:
        return len(self._keys)

    def add(self, candidate: object) -> None:
        key = candidate_key(candidate)
        geometry = candidate.location.bbox
        if key in self._keys and self._keys[key] != geometry:
            raise ProcessingError(ProcessingErrorCode.INVALID_POLICY,
                "Conflicting locations for duplicate source spans.",
                submission_id=self.submission_id,
                artifact_id=candidate.location.artifact_id)
        self._keys[key] = geometry
        if len(self._keys) > MAX_SUBMISSION_MATCHES:
            raise ProcessingError(ProcessingErrorCode.INVALID_POLICY,
                "Submission match limit exceeded.", submission_id=self.submission_id,
                artifact_id=candidate.location.artifact_id)


def _worker_main(connection) -> None:
    """All attacker-supplied pattern parsing/compilation stays killable."""
    compiled = {}
    connection.send(("ready", None))
    try:
        while True:
            operation, pattern, kind, case_sensitive, text = connection.recv()
            try:
                flags = regex.VERSION1
                if not case_sensitive:
                    flags |= regex.IGNORECASE | regex.FULLCASE
                key = (pattern, kind, case_sensitive)
                if operation == "validate":
                    expression = regex.escape(pattern) if kind == "exact" else pattern
                    if kind == "regex":
                        # A conservative consumed-width check also rejects zero-width
                        # lookarounds which would not match the empty input itself.
                        from re import _parser
                        parsed = _parser.parse(pattern, 0 if case_sensitive else re.IGNORECASE)
                        if parsed.getwidth()[0] == 0:
                            connection.send(("invalid", None))
                            continue
                        if bool(parsed.state.flags & re.IGNORECASE) == case_sensitive:
                            raise ValueError("Conflicting case-sensitivity flags")
                        def check_case_flags(tree):
                            for operation, arguments in tree:
                                if operation == _parser.SUBPATTERN:
                                    _, added, removed, child = arguments
                                    if (case_sensitive and added & re.IGNORECASE) or (not case_sensitive and removed & re.IGNORECASE):
                                        raise ValueError("Conflicting case-sensitivity flags")
                                    check_case_flags(child)
                                elif operation == _parser.BRANCH:
                                    for branch in arguments[1]:
                                        check_case_flags(branch)
                                elif operation in {_parser.MAX_REPEAT, _parser.MIN_REPEAT, _parser.POSSESSIVE_REPEAT}:
                                    check_case_flags(arguments[2])
                                elif operation in {_parser.ASSERT, _parser.ASSERT_NOT}:
                                    check_case_flags(arguments[1])
                                elif operation == _parser.ATOMIC_GROUP:
                                    check_case_flags(arguments)
                                elif operation == _parser.GROUPREF_EXISTS:
                                    check_case_flags(arguments[1])
                                    if arguments[2] is not None:
                                        check_case_flags(arguments[2])
                        check_case_flags(parsed)
                    compiled[key] = regex.compile(expression, flags)
                    connection.send(("ok", None))
                else:
                    spans = []
                    for match in compiled[key].finditer(text, overlapped=True,
                                                       timeout=REGEX_TIMEOUT_SECONDS):
                        start, end = match.span()
                        if start == end:
                            connection.send(("invalid", None))
                            break
                        spans.append((start, end))
                        if len(spans) > MAX_SUBMISSION_MATCHES:
                            connection.send(("limit", None))
                            break
                    else:
                        connection.send(("ok", spans))
            except TimeoutError:
                connection.send(("timeout", None))
            except Exception:
                connection.send(("invalid", None))
    except (EOFError, BrokenPipeError, OSError):
        pass
    finally:
        connection.close()


class _RegexWorker:
    def __init__(self, submission_id: UUID | None) -> None:
        self.submission_id = submission_id
        context = mp.get_context("spawn")
        self.connection, child = context.Pipe()
        self.process = context.Process(target=_worker_main, args=(child,), daemon=True)
        try:
            self.process.start()
            child.close()
            # Startup/imports are separate from the 100ms pattern execution budget.
            if not self.connection.poll(5) or self.connection.recv()[0] != "ready":
                raise TimeoutError
        except Exception as exc:
            child.close()
            self.close()
            raise ProcessingError(ProcessingErrorCode.PROCESSING_TIMEOUT,
                "Custom rule evaluator could not start.", submission_id=submission_id) from exc

    def request(self, operation: str, rule: CustomRule, text: str = "") -> list[tuple[int, int]]:
        try:
            started = monotonic()
            self.connection.send((operation, rule.pattern, rule.kind, rule.case_sensitive, text))
            remaining = max(0.0, REGEX_TIMEOUT_SECONDS - (monotonic() - started))
            if not self.connection.poll(remaining):
                raise TimeoutError
            status, payload = self.connection.recv()
            if monotonic() - started > REGEX_TIMEOUT_SECONDS or status == "timeout":
                raise TimeoutError
            if status != "ok":
                message = "Submission match limit exceeded." if status == "limit" else "Invalid custom rule expression."
                raise ProcessingError(ProcessingErrorCode.INVALID_POLICY, message,
                                      submission_id=self.submission_id)
            return payload or []
        except ProcessingError:
            self.close()
            raise
        except TimeoutError as exc:
            self.close()
            raise ProcessingError(ProcessingErrorCode.PROCESSING_TIMEOUT,
                "Custom rule execution exceeded 100ms.", submission_id=self.submission_id) from exc
        except Exception as exc:
            self.close()
            raise ProcessingError(ProcessingErrorCode.INVALID_POLICY,
                "Custom rule evaluation failed.", submission_id=self.submission_id) from exc

    def close(self) -> None:
        self.connection.close()
        if self.process.pid is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=1)


class CustomRuleEvaluator:
    """Scoped worker for literal and regex matching; disabled rules also run."""

    def __init__(self, rules: Iterable[CustomRule], *, submission_id: UUID | None = None) -> None:
        self.submission_id = submission_id
        self._worker = None
        try:
            adapter = TypeAdapter(Annotated[list[CustomRule], Field(max_length=100)])
            self._rules = tuple(adapter.validate_python([rule.model_dump(warnings=False) for rule in rules]))
            if len({rule.id for rule in self._rules}) != len(self._rules):
                raise ValueError("Duplicate custom rule IDs")
            if self._rules:
                self._worker = _RegexWorker(submission_id)
                for rule in self._rules:
                    self._worker.request("validate", rule)
        except ProcessingError:
            self.close()
            raise
        except Exception as exc:
            self.close()
            raise ProcessingError(ProcessingErrorCode.INVALID_POLICY, "Invalid custom rules.",
                                  submission_id=submission_id) from exc
        self._closed = False

    def __enter__(self) -> CustomRuleEvaluator:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def close(self) -> None:
        if self._worker is not None:
            self._worker.close()
        self._closed = True

    def match(self, *, text: str = "", blocks: Iterable[ExtractedTextBlock] = (),
              budget: MatchBudget | None = None) -> tuple[CustomCandidate, ...]:
        budget = budget if budget is not None else MatchBudget(self.submission_id)
        candidates = {}
        try:
            if self._closed:
                raise ValueError("Closed evaluator")
            units = []
            if text:
                units.append((text, SourceLocation(artifact_id=None, kind="message", page_number=None,
                    slide_number=None, source_ref=None, start=0, end=len(text), bbox=None)))
            sources = {}
            for block in blocks:
                validated = ExtractedTextBlock.model_validate(block.model_dump())
                location = validated.location
                source_key = (location.artifact_id, location.kind, location.page_number,
                              location.slide_number, location.source_ref)
                previous = sources.get(source_key)
                if previous is not None:
                    if previous.text != validated.text or previous.location != location:
                        raise ProcessingError(ProcessingErrorCode.INVALID_POLICY,
                            "Conflicting extraction source units.",
                            submission_id=self.submission_id, artifact_id=location.artifact_id)
                    continue
                sources[source_key] = validated
                units.append((validated.text, validated.location))
            for content, location in units:
                for rule in self._rules:
                    try:
                        spans = self._worker.request("match", rule, content)
                    except ProcessingError as exc:
                        exc.artifact_id = location.artifact_id
                        raise
                    for start, end in spans:
                        if not 0 <= start < end <= len(content):
                            raise ValueError("Invalid source span")
                        source = location.model_dump()
                        source.update(start=start, end=end)
                        candidate = CustomCandidate(rule_id=f"custom:{rule.id}",
                            recognizer=f"Custom{rule.kind.title()}Recognizer", location=SourceLocation.model_validate(source))
                        candidate._matched_text = content[start:end]
                        budget.add(candidate)
                        candidates[candidate_key(candidate)] = candidate
            return tuple(candidates.values())
        except ProcessingError:
            self.close()
            raise
        except Exception as exc:
            self.close()
            raise ProcessingError(ProcessingErrorCode.INVALID_POLICY, "Custom rule evaluation failed.",
                                  submission_id=self.submission_id) from exc


def validate_custom_rule(rule: CustomRule) -> None:
    """Shared engine/save/preview validation hook with bounded compilation."""
    with CustomRuleEvaluator([rule]):
        pass
