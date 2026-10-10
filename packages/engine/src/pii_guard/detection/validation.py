from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Annotated

from pydantic import Field, PrivateAttr, StrictInt, field_validator

from pii_guard.models import EngineBaseModel, SourceLocation
from pii_guard.rules.builtins import BUILTIN_RULE_CATEGORIES, TEXT_RULE_IDS, RuleId


DEFAULT_THRESHOLDS = {
    rule: (0.90 if rule == "EMPLOYEE_ID" else 0.70 if rule in {"EMAIL_ADDRESS", "PHONE_NUMBER"}
           else 0.75 if rule == "PERSON" else 0.80)
    for rule in TEXT_RULE_IDS
}


class DetectionConfig(EngineBaseModel):
    language: str = "en"
    spacy_model: Annotated[str, Field(min_length=1)] = "en_core_web_sm"
    thresholds: dict[RuleId, Annotated[float, Field(ge=0, le=1, allow_inf_nan=False, strict=True)]] = Field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    context_validated_score: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False, strict=True)] = 0.85

    @field_validator("language")
    @classmethod
    def english_only(cls, value: str) -> str:
        if value != "en":
            raise ValueError("Only English text detection is configured")
        return value

    @field_validator("thresholds")
    @classmethod
    def all_text_rules(cls, value: dict) -> dict:
        if set(value) != TEXT_RULE_IDS:
            raise ValueError("Thresholds must contain every built-in text rule exactly once")
        return value


class RecognizerCandidate(EngineBaseModel):
    """Private, validated provider output; never a final Finding."""

    rule_id: RuleId
    start: Annotated[StrictInt, Field(ge=0)]
    end: Annotated[StrictInt, Field(gt=0)]
    score: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    recognizer: Annotated[str, Field(min_length=1)]


class DetectionCandidate(EngineBaseModel):
    """Processing-only candidate. Matched content is excluded from dumps and repr."""

    rule_id: RuleId
    category: str
    confidence: Annotated[float, Field(ge=0, le=1)]
    recognizer_confidence: Annotated[float, Field(ge=0, le=1)]
    recognizer: str
    location: SourceLocation
    _matched_text: str = PrivateAttr(default="")

    @property
    def matched_text(self) -> str:
        return self._matched_text


@dataclass(frozen=True)
class RejectedCandidate:
    candidate: DetectionCandidate
    reason: str


@dataclass(frozen=True)
class DetectionBatch:
    accepted: tuple[DetectionCandidate, ...] = ()
    rejected: tuple[RejectedCandidate, ...] = field(default=(), repr=False)


CONTEXT = {
    "PHONE_NUMBER": r"\b(?:phone|telephone|mobile|call|contact)\b",
    "US_SSN": r"\b(?:ssn|social security)\b",
    "US_PASSPORT": r"\bpassport\b",
    "US_DRIVER_LICENSE": r"\b(?:driver'?s? licen[cs]e|driving licen[cs]e|dl)\b",
    "US_ITIN": r"\b(?:itin|individual taxpayer|taxpayer identification)\b",
    "US_BANK_NUMBER": r"\b(?:bank|account|acct|checking)\b",
}


def _format_valid(rule: str, value: str) -> bool:
    if rule == "EMPLOYEE_ID":
        return re.fullmatch(r"EMP-[0-9]{5}", value) is not None
    if rule == "PERSON":
        return any(c.isalpha() for c in value) and not any(c.isdigit() for c in value)
    if rule == "EMAIL_ADDRESS":
        return re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) is not None
    if rule == "PHONE_NUMBER":
        import phonenumbers
        try:
            return phonenumbers.is_valid_number(phonenumbers.parse(value, "US"))
        except phonenumbers.NumberParseException:
            return False
    if rule == "US_SSN":
        if not re.fullmatch(r"[0-9]{3}([- .]?)[0-9]{2}\1[0-9]{4}", value):
            return False
        digits = re.sub(r"[- .]", "", value)
        from presidio_analyzer.predefined_recognizers import UsSsnRecognizer
        return 0 < int(digits[:3]) < 900 and not UsSsnRecognizer().invalidate_result(value)
    if rule == "US_PASSPORT":
        return re.fullmatch(r"(?:[0-9]{9}|[A-Z][0-9]{8})", value) is not None
    if rule == "US_DRIVER_LICENSE":
        return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 -]{3,18}[A-Za-z0-9]", value) is not None and any(c.isdigit() for c in value)
    if rule == "US_ITIN":
        if not re.fullmatch(r"9[0-9]{2}[- ]?[0-9]{2}[- ]?[0-9]{4}", value):
            return False
        digits = re.sub(r"[- ]", "", value)
        return int(digits[3:5]) in {*range(50, 66), *range(70, 89), *range(90, 93), *range(94, 100)}
    if rule == "US_BANK_NUMBER":
        return re.fullmatch(r"[0-9]{8,17}", value) is not None
    # Reuse Presidio's domain checksum validators, rather than inventing new ones.
    from presidio_analyzer.predefined_recognizers import CreditCardRecognizer, IbanRecognizer, MedicalLicenseRecognizer
    if rule == "CREDIT_CARD":
        return bool(re.fullmatch(r"[0-9][0-9 -]{11,25}[0-9]", value)) and CreditCardRecognizer().validate_result(value) is True
    if rule == "IBAN_CODE":
        return bool(re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9 ]{11,30}", value)) and IbanRecognizer().validate_result(value) is True
    if rule == "MEDICAL_LICENSE":
        return bool(re.fullmatch(r"[ABCDEFGHJKLMPRSTUX][A-Z9][0-9]{7}", value)) and MedicalLicenseRecognizer().validate_result(value) is True
    return False


def validate_candidates(text: str, location: SourceLocation,
                        raw: list[RecognizerCandidate], config: DetectionConfig) -> DetectionBatch:
    accepted = {}
    rejected = []
    for match in raw:
        if match.rule_id not in TEXT_RULE_IDS or not 0 <= match.start < match.end <= len(text):
            raise ValueError("Invalid recognizer source span or rule")
        value = text[match.start:match.end]
        source = location.model_dump()
        source.update(start=match.start + (location.start or 0), end=match.end + (location.start or 0))
        candidate = DetectionCandidate(rule_id=match.rule_id, category=BUILTIN_RULE_CATEGORIES[match.rule_id],
            confidence=match.score, recognizer_confidence=match.score, recognizer=match.recognizer,
            location=SourceLocation.model_validate(source))
        candidate._matched_text = value
        reason = None
        if match.score == 0:
            reason = "recognizer_invalidated"
        elif not _format_valid(match.rule_id, value):
            reason = "invalid_format"
        elif ((match.start > 0 and (text[match.start-1].isalnum() or text[match.start-1] == "_"))
              or (match.end < len(text) and (text[match.end].isalnum() or text[match.end] == "_"))):
            reason = "invalid_boundary"
        elif match.rule_id == "EMPLOYEE_ID" and ((match.start > 0 and text[match.start-1] == "-") or (match.end < len(text) and text[match.end] == "-")):
            reason = "invalid_boundary"
        if reason is None and match.rule_id in CONTEXT:
            nearby = text[max(0,match.start-80):match.start] + " " + text[match.end:match.end+40]
            if not re.search(CONTEXT[match.rule_id], nearby, re.IGNORECASE) and match.rule_id != "PHONE_NUMBER":
                reason = "missing_context"
            elif re.search(CONTEXT[match.rule_id], nearby, re.IGNORECASE):
                candidate.confidence = max(match.score, config.context_validated_score)
        if reason is None and candidate.confidence < config.thresholds[match.rule_id]:
            reason = "below_threshold"
        if reason:
            rejected.append(RejectedCandidate(candidate, reason))
            continue
        key = (candidate.rule_id, candidate.location.start, candidate.location.end)
        previous = accepted.get(key)
        if previous is None or (candidate.confidence, candidate.recognizer) > (previous.confidence, previous.recognizer):
            accepted[key] = candidate
    return DetectionBatch(tuple(sorted(accepted.values(), key=lambda c: (c.location.start, c.location.end, c.rule_id))), tuple(rejected))
