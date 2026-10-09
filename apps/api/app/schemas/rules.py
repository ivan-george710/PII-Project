from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictBool, StrictInt

from app.schemas.common import Schema


class RuleId(str, Enum):
    PERSON = "PERSON"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    EMPLOYEE_ID = "EMPLOYEE_ID"
    US_SSN = "US_SSN"
    US_PASSPORT = "US_PASSPORT"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    US_ITIN = "US_ITIN"
    US_BANK_NUMBER = "US_BANK_NUMBER"
    IBAN_CODE = "IBAN_CODE"
    CREDIT_CARD = "CREDIT_CARD"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    FACE = "FACE"


class CustomRule(Schema):
    id: UUID
    name: str = Field(min_length=1, max_length=80)
    kind: Literal["exact", "regex"]
    pattern: str = Field(min_length=1, max_length=512)
    case_sensitive: StrictBool
    enabled: StrictBool


class PolicySnapshot(Schema):
    organization_id: UUID
    version: StrictInt = Field(ge=1)
    builtins: dict[RuleId, StrictBool]
    custom_rules: list[CustomRule] = Field(default_factory=list, max_length=100)


class BuiltinRuleUpdate(Schema):
    rule_id: RuleId
    enabled: StrictBool


class UpdateBuiltinsRequest(Schema):
    expected_version: StrictInt = Field(ge=1)
    updates: list[BuiltinRuleUpdate] = Field(min_length=1, max_length=13)


class ToggleAllRequest(Schema):
    expected_version: StrictInt = Field(ge=1)
    enabled: StrictBool


class CreateCustomRuleRequest(Schema):
    expected_version: StrictInt = Field(ge=1)
    name: str = Field(min_length=1, max_length=80)
    kind: Literal["exact", "regex"]
    pattern: str = Field(min_length=1, max_length=512)
    case_sensitive: StrictBool
    enabled: StrictBool


class UpdateCustomRuleRequest(Schema):
    expected_version: StrictInt = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=80)
    kind: Literal["exact", "regex"] | None = None
    pattern: str | None = Field(default=None, min_length=1, max_length=512)
    case_sensitive: StrictBool | None = None
    enabled: StrictBool | None = None


class CustomRuleMutationResponse(Schema):
    rule: CustomRule
    policy_version: StrictInt = Field(ge=1)


class DeleteCustomRuleResponse(Schema):
    deleted_id: UUID
    policy_version: StrictInt = Field(ge=1)


class RulePreviewRequest(Schema):
    kind: Literal["exact", "regex"]
    pattern: str = Field(min_length=1, max_length=512)
    case_sensitive: StrictBool
    sample_text: str = Field(max_length=10000)


class PreviewMatch(Schema):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class RulePreviewResponse(Schema):
    matches: list[PreviewMatch] = Field(default_factory=list, max_length=1000)
    count: int = Field(ge=0)
    truncated: StrictBool
