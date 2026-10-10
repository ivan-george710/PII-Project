from __future__ import annotations

from typing import Literal, TypeAlias


RuleId: TypeAlias = Literal[
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
]

BUILTIN_RULE_IDS: tuple[str, ...] = (
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

TEXT_RULE_IDS: frozenset[str] = frozenset(
    rule_id for rule_id in BUILTIN_RULE_IDS if rule_id != "FACE"
)

FACE_RULE_ID = "FACE"

BUILTIN_RULE_CATEGORIES: dict[str, str] = {
    "PERSON": "identity",
    "EMAIL_ADDRESS": "contact",
    "PHONE_NUMBER": "contact",
    "EMPLOYEE_ID": "employee_identifier",
    "US_SSN": "government_identifier",
    "US_PASSPORT": "government_identifier",
    "US_DRIVER_LICENSE": "government_identifier",
    "US_ITIN": "government_identifier",
    "US_BANK_NUMBER": "financial",
    "IBAN_CODE": "financial",
    "CREDIT_CARD": "financial",
    "MEDICAL_LICENSE": "professional_identifier",
    "FACE": "biometric",
}

DEFAULT_BUILTIN_RULES: dict[str, bool] = {
    rule_id: True for rule_id in BUILTIN_RULE_IDS
}
