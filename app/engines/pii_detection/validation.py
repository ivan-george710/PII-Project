"""Explicit PII policy and bounded, conservative candidate validation."""
import re
from enum import Enum

from .models import DetectedPII

DETECTOR_POLICY_VERSION = "1.1"


class ValidationDecision(str, Enum):
    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    AMBIGUOUS = "AMBIGUOUS"


PII_ENTITY_TYPES = frozenset({
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "EMPLOYEE_ID", "US_SSN",
    "US_PASSPORT", "US_DRIVER_LICENSE", "US_ITIN", "US_BANK_NUMBER",
    "IBAN_CODE", "CREDIT_CARD", "MEDICAL_LICENSE",
})

# General business/role vocabulary, also used for concatenated OCR labels.
# This is not a list of names or document-specific span exceptions.
BUSINESS_WORDS = frozenset({
    "policy", "owner", "author", "head", "of", "and", "the", "enterprise", "risk",
    "framework", "change", "system", "approval", "process", "regulatory", "deadline",
    "deadlines", "management", "financial", "group", "chief", "officer", "committee",
    "bank", "account", "number", "department", "compliance", "delivery", "offshore",
    "speak", "up", "unsupported", "component", "components", "on", "control",
    "controls", "review", "business", "operations", "human", "resources",
})
NAME_PARTICLES = frozenset({"de", "del", "da", "di", "van", "von", "der", "la", "le"})
BUSINESS_ACRONYMS = frozenset({"NED", "RCSA"})
DRIVER_LICENSE_CONTEXT = (
    "driver license", "driver's license", "drivers license", "driving license",
    "dl number", "license number", "licence number",
)
BANK_ACCOUNT_CONTEXT = (
    "bank account", "account number", "account no", "account #", "iban", "banking",
)


def _business_label(value: str) -> bool:
    compact = "".join(c.lower() for c in value if c.isalpha())
    if not compact:
        return False
    # Word segmentation recognizes OCR labels without changing source offsets.
    reachable = {0}
    for position in range(len(compact)):
        if position in reachable:
            reachable.update(position + len(word) for word in BUSINESS_WORDS
                             if compact.startswith(word, position))
    return len(compact) in reachable


def _name_tokens(value: str) -> list[str]:
    # Validation-only spacing of an initial joined to its following surname.
    value = re.sub(r"\b([A-Z])\.(?=[^\W\d_])", r"\1. ", value)
    return value.split()


def _looks_like_person_name(value: str) -> bool:
    tokens = _name_tokens(value)
    if len(tokens) < 2:
        return False
    for token in tokens:
        if token.lower() in NAME_PARTICLES:
            continue
        letters = token.replace(".", "").replace("-", "").replace("'", "").replace("’", "")
        if (not letters.isalpha() or not letters[0].isupper()
                or len(letters) > 25 or (len(letters) > 1 and not letters[1:].islower())):
            return False
    # Two capitalized words are insufficient when business vocabulary is present.
    return not any(token.lower().strip(".") in BUSINESS_WORDS for token in tokens)


def _adjacent(detection, context, context_start):
    # Engine supplies the exact relative offset: repeated values cannot borrow
    # context from their first occurrence. Direct callers may omit context.
    start = context_start if context_start is not None else context.find(detection.text)
    if start < 0 or context[start:start+len(detection.text)] != detection.text:
        return "", ""
    return context[max(0,start-80):start], context[start+len(detection.text):start+len(detection.text)+80]


def _explicit_business_number(left, right):
    # Adjacent field evidence, never a remote business word elsewhere on a page.
    money = re.search(r"\b(?:revenue|turnover|profit|budget|amount|balance)\s*(?:amount)?\s*[:=]\s*$", left, re.I)
    unit = re.match(r"\s*(?:dollars|USD|EUR|GBP)\b", right, re.I)
    code = re.search(r"\b(?:project|release|internal)\s+code\s*[:=]?\s*[A-Z]{2,8}-$", left, re.I)
    return bool((money and unit) or code)


def validate_detection(detection: DetectedPII, context: str = "", *, context_start=None) -> tuple[ValidationDecision, str]:
    if detection.entity_type not in PII_ENTITY_TYPES:
        return ValidationDecision.REJECT, "entity_type_not_in_pii_policy"
    left, right = _adjacent(detection, context, context_start)
    if detection.entity_type == "EMPLOYEE_ID":
        if re.fullmatch(r"EMP-[0-9]{5}", detection.text):
            if (left and (left[-1].isalnum() or left[-1] in "_-")) or (right and (right[0].isalnum() or right[0] in "_-")):
                return ValidationDecision.AMBIGUOUS, "employee_id_partial_span"
            return ValidationDecision.CONFIRM, "documented_employee_id_format"
        return ValidationDecision.REJECT, "invalid_employee_id_format"
    if detection.entity_type == "PERSON":
        value = detection.text.strip()
        if _business_label(value) or value in BUSINESS_ACRONYMS:
            return ValidationDecision.REJECT, "business_label_or_acronym"
        if "@" in value:
            return ValidationDecision.REJECT, "person_span_contains_email"
        if not value or all(c.isdigit() or c.isspace() for c in value):
            return ValidationDecision.REJECT, "not_a_person_name"
        # An institutional suffix inside the candidate is positive non-person
        # evidence. Nearby institutions alone do not invalidate a person's name.
        if re.search(r"\b(?:committee|department|team|holdings|limited|corporation|inc|ltd)\.?$", value, re.I):
            return ValidationDecision.REJECT, "institutional_person_span"
        if detection.confidence < .5:
            return ValidationDecision.AMBIGUOUS, "low_confidence_person"
        if _looks_like_person_name(value) and "\n" not in value:
            return ValidationDecision.CONFIRM, "valid_person_name_structure"
        # Single tokens, contaminated spans, unusual casing and OCR concatenations
        # remain contextual findings. Never invent a cleaned source span.
        return ValidationDecision.AMBIGUOUS, "person_requires_contextual_review"
    if detection.entity_type == "EMAIL_ADDRESS":
        value = detection.text
        # Conservative unquoted mailbox syntax; unusual RFC forms stay REVIEW.
        if ".." in value or value.startswith(".") or ".@" in value:
            return ValidationDecision.REJECT, "invalid_email_dot_structure"
        if re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", value):
            if (left and left[-1] in "@._") or (right and right[0] in "@_"):
                return ValidationDecision.AMBIGUOUS, "email_partial_span"
            return ValidationDecision.CONFIRM, "valid_email_structure"
        return ValidationDecision.AMBIGUOUS, "email_format_requires_review"
    if detection.entity_type in {"PHONE_NUMBER", "US_BANK_NUMBER", "US_DRIVER_LICENSE", "US_PASSPORT"}:
        if _explicit_business_number(left, right):
            return ValidationDecision.REJECT, "explicit_business_numeric_field"
    if detection.entity_type == "PHONE_NUMBER":
        digits = re.sub(r"\D", "", detection.text)
        if not 7 <= len(digits) <= 15:
            return ValidationDecision.AMBIGUOUS, "phone_length_requires_review"
        if not re.fullmatch(r"[+()\d .\-]+(?:\s*(?:ext\.?|x)\s*\d+)?", detection.text, re.I):
            return ValidationDecision.AMBIGUOUS, "phone_format_requires_review"
        # Existing recognizer evidence retained; no lower score threshold.
        return ValidationDecision.CONFIRM, "plausible_phone_structure"
    if detection.entity_type in {"US_DRIVER_LICENSE", "US_BANK_NUMBER"}:
        phrases = (DRIVER_LICENSE_CONTEXT if detection.entity_type == "US_DRIVER_LICENSE"
                   else BANK_ACCOUNT_CONTEXT)
        has_context = any(phrase in context.lower() for phrase in phrases)
        return (ValidationDecision.AMBIGUOUS,
                "identifier_requires_contextual_review" if has_context
                else "identifier_without_supporting_context")
    # Remaining policy entities retain Presidio's original evidence/confidence.
    return ValidationDecision.CONFIRM, "accepted_by_pii_policy"
