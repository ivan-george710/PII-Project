from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import Field, StrictInt

from pii_guard.detection.validation import DetectionCandidate
from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import EngineBaseModel, ExtractedTextBlock, Finding, PolicySnapshot, SourceLocation
from pii_guard.rules.builtins import BUILTIN_RULE_CATEGORIES
from pii_guard.rules.custom import (
    CUSTOM_CATEGORY, CustomCandidate, CustomRuleEvaluator, MatchBudget, candidate_key,
)


class RedactionTarget(EngineBaseModel):
    """An enabled finding's original source region, for later rendering only."""

    finding_id: UUID
    location: SourceLocation


class PolicyEvaluation(EngineBaseModel):
    organization_id: UUID
    policy_version: Annotated[StrictInt, Field(ge=1)]
    findings: tuple[Finding, ...]
    redaction_targets: tuple[RedactionTarget, ...] = Field(exclude=True, repr=False)


class PolicyEvaluator:
    """One immutable policy snapshot and one complete evaluation per run."""

    def __init__(self, policy: PolicySnapshot, *, submission_id: UUID | None = None) -> None:
        self.submission_id = submission_id
        self._evaluated = False
        try:
            snapshot = PolicySnapshot.model_validate(policy.model_dump(warnings=False))
            self._snapshot_json = snapshot.model_dump_json()
            enabled = dict(snapshot.builtins)
            enabled.update({f"custom:{rule.id}": rule.enabled for rule in snapshot.custom_rules})
            self._enabled = MappingProxyType(enabled)
        except Exception as exc:
            raise ProcessingError(ProcessingErrorCode.INVALID_POLICY, "Invalid policy snapshot.",
                                  submission_id=submission_id) from exc

    def evaluate(self, candidates: Iterable[DetectionCandidate | CustomCandidate] = (), *,
                 text: str = "", blocks: Iterable[ExtractedTextBlock] = ()) -> PolicyEvaluation:
        try:
            if self._evaluated:
                raise ValueError("A policy evaluator is scoped to one complete submission")
            self._evaluated = True
            snapshot = PolicySnapshot.model_validate_json(self._snapshot_json)
            budget = MatchBudget(self.submission_id)
            accepted = {}

            def accept(candidate: DetectionCandidate | CustomCandidate) -> None:
                if isinstance(candidate, DetectionCandidate):
                    validated = DetectionCandidate.model_validate(candidate.model_dump(warnings=False))
                    if validated.rule_id not in BUILTIN_RULE_CATEGORIES or validated.category != BUILTIN_RULE_CATEGORIES[validated.rule_id]:
                        raise ValueError("Invalid built-in candidate category")
                    if (validated.rule_id == "FACE") != (validated.location.kind == "face"):
                        raise ValueError("Candidate rule and source kind disagree")
                elif isinstance(candidate, CustomCandidate):
                    validated = CustomCandidate.model_validate(candidate.model_dump(warnings=False))
                    if not validated.rule_id.startswith("custom:") or validated.category != CUSTOM_CATEGORY:
                        raise ValueError("Invalid custom candidate category")
                    if validated.location.kind == "face":
                        raise ValueError("Custom text rules require text source spans")
                else:
                    raise ValueError("Invalid candidate contract")
                if validated.rule_id not in self._enabled:
                    raise ValueError("Candidate rule is absent from the snapshot")
                key = candidate_key(validated)
                previous = accepted.get(key)
                if previous is not None and previous.location != validated.location:
                    raise ValueError("Conflicting locations for duplicate source spans")
                budget.add(validated)
                if previous is None or (validated.confidence, validated.recognizer) > (previous.confidence, previous.recognizer):
                    accepted[key] = validated

            for candidate in candidates:
                accept(candidate)
            # Every custom rule is validated and evaluated, including disabled ones.
            with CustomRuleEvaluator(snapshot.custom_rules, submission_id=self.submission_id) as custom:
                for candidate in custom.match(text=text, blocks=blocks, budget=budget):
                    accept(candidate)
            findings = []
            targets = []
            for candidate in accepted.values():
                enabled = self._enabled[candidate.rule_id]
                finding = Finding(id=uuid4(), rule_id=candidate.rule_id, category=candidate.category,
                    confidence=candidate.confidence, recognizer=candidate.recognizer,
                    location=SourceLocation.model_validate(candidate.location.model_dump()),
                    action="redacted" if enabled else "allowed_disabled")
                findings.append(finding)
                if enabled:
                    targets.append(RedactionTarget(finding_id=finding.id,
                        location=SourceLocation.model_validate(finding.location.model_dump())))
            # Targets contain enabled regions only: disabled overlaps never subtract
            # coverage. Public events remain separate; merging belongs to rendering.
            return PolicyEvaluation(organization_id=snapshot.organization_id,
                policy_version=snapshot.version, findings=tuple(findings), redaction_targets=tuple(targets))
        except ProcessingError:
            raise
        except Exception as exc:
            raise ProcessingError(ProcessingErrorCode.INVALID_POLICY, "Policy evaluation failed.",
                                  submission_id=self.submission_id) from exc
