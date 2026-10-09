import re
import time
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.models.rule import CompanyRulePolicy
from app.schemas.common import ApiError
from app.schemas.rules import (
    CreateCustomRuleRequest,
    CustomRule,
    PolicySnapshot,
    PreviewMatch,
    RuleId,
    RulePreviewRequest,
    RulePreviewResponse,
    ToggleAllRequest,
    UpdateBuiltinsRequest,
    UpdateCustomRuleRequest,
)

DEFAULT_BUILTINS = {rule.value: True for rule in RuleId}


def get_default_builtins() -> dict[str, bool]:
    return dict(DEFAULT_BUILTINS)


def get_or_create_policy(db: Session, company_id: UUID) -> CompanyRulePolicy:
    policy = (
        db.query(CompanyRulePolicy)
        .filter(CompanyRulePolicy.company_id == company_id)
        .first()
    )
    if policy is None:
        policy = CompanyRulePolicy(
            company_id=company_id,
            version=1,
            builtins=get_default_builtins(),
            custom_rules=[],
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return policy


def get_snapshot(db: Session, organization_id: UUID) -> PolicySnapshot:
    policy = get_or_create_policy(db, organization_id)
    # Ensure all 13 built-in rule keys exist in snapshot
    builtins = dict(DEFAULT_BUILTINS)
    if isinstance(policy.builtins, dict):
        builtins.update(policy.builtins)

    custom_rules = [
        CustomRule.model_validate(r) for r in (policy.custom_rules or [])
    ]
    return PolicySnapshot(
        organization_id=organization_id,
        version=policy.version,
        builtins=builtins,
        custom_rules=custom_rules,
    )


def update_builtins(
    db: Session, organization_id: UUID, req: UpdateBuiltinsRequest
) -> PolicySnapshot:
    policy = get_or_create_policy(db, organization_id)
    if policy.version != req.expected_version:
        raise ApiError(409, "POLICY_VERSION_CONFLICT", "Policy version has changed")

    builtins = dict(DEFAULT_BUILTINS)
    if isinstance(policy.builtins, dict):
        builtins.update(policy.builtins)

    for update in req.updates:
        builtins[update.rule_id.value] = update.enabled

    policy.builtins = builtins
    policy.version += 1
    db.commit()
    db.refresh(policy)
    return get_snapshot(db, organization_id)


def toggle_all(
    db: Session, organization_id: UUID, req: ToggleAllRequest
) -> PolicySnapshot:
    policy = get_or_create_policy(db, organization_id)
    if policy.version != req.expected_version:
        raise ApiError(409, "POLICY_VERSION_CONFLICT", "Policy version has changed")

    # Toggle all builtins
    builtins = {rule.value: req.enabled for rule in RuleId}
    policy.builtins = builtins

    # Toggle all existing custom rules
    custom_rules = []
    for r in policy.custom_rules or []:
        rule_data = dict(r)
        rule_data["enabled"] = req.enabled
        custom_rules.append(rule_data)
    policy.custom_rules = custom_rules

    policy.version += 1
    db.commit()
    db.refresh(policy)
    return get_snapshot(db, organization_id)


def validate_rule_pattern(kind: str, pattern: str) -> None:
    trimmed = pattern.strip()
    if not trimmed:
        raise ApiError(422, "INVALID_PATTERN", "Pattern cannot be empty or whitespace only")

    if kind == "regex":
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            raise ApiError(422, "INVALID_REGEX", f"Invalid regular expression: {e}")

        # Reject empty-string matching regexes (e.g., .*, ^$, a*)
        if compiled.match("") is not None or compiled.search("") is not None:
            raise ApiError(422, "EMPTY_MATCHING_REGEX", "Regex cannot match empty string")


def create_custom_rule(
    db: Session, organization_id: UUID, req: CreateCustomRuleRequest
) -> tuple[CustomRule, int]:
    policy = get_or_create_policy(db, organization_id)
    if policy.version != req.expected_version:
        raise ApiError(409, "POLICY_VERSION_CONFLICT", "Policy version has changed")

    current_rules = list(policy.custom_rules or [])
    if len(current_rules) >= 100:
        raise ApiError(413, "LIMIT_EXCEEDED", "Maximum 100 custom rules allowed")

    trimmed_name = req.name.strip()
    if not trimmed_name:
        raise ApiError(422, "INVALID_NAME", "Rule name cannot be whitespace only")

    for r in current_rules:
        if r.get("name", "").strip().lower() == trimmed_name.lower():
            raise ApiError(409, "RULE_NAME_EXISTS", "A custom rule with this name already exists")

    validate_rule_pattern(req.kind, req.pattern)

    new_rule = CustomRule(
        id=uuid4(),
        name=trimmed_name,
        kind=req.kind,
        pattern=req.pattern,
        case_sensitive=req.case_sensitive,
        enabled=req.enabled,
    )
    current_rules.append(new_rule.model_dump(mode="json"))
    policy.custom_rules = current_rules
    policy.version += 1
    db.commit()
    db.refresh(policy)
    return new_rule, policy.version


def update_custom_rule(
    db: Session, organization_id: UUID, rule_id: UUID, req: UpdateCustomRuleRequest
) -> tuple[CustomRule, int]:
    policy = get_or_create_policy(db, organization_id)
    if policy.version != req.expected_version:
        raise ApiError(409, "POLICY_VERSION_CONFLICT", "Policy version has changed")

    current_rules = list(policy.custom_rules or [])
    found_idx = None
    target_rule = None
    for idx, r in enumerate(current_rules):
        if str(r.get("id")) == str(rule_id):
            found_idx = idx
            target_rule = dict(r)
            break

    if target_rule is None:
        raise ApiError(404, "NOT_FOUND", "Custom rule not found")

    new_name = target_rule["name"]
    if req.name is not None:
        trimmed_name = req.name.strip()
        if not trimmed_name:
            raise ApiError(422, "INVALID_NAME", "Rule name cannot be whitespace only")
        for idx, r in enumerate(current_rules):
            if idx != found_idx and r.get("name", "").strip().lower() == trimmed_name.lower():
                raise ApiError(409, "RULE_NAME_EXISTS", "A custom rule with this name already exists")
        new_name = trimmed_name

    new_kind = req.kind if req.kind is not None else target_rule["kind"]
    new_pattern = req.pattern if req.pattern is not None else target_rule["pattern"]

    if req.pattern is not None or req.kind is not None:
        validate_rule_pattern(new_kind, new_pattern)

    new_case_sensitive = (
        req.case_sensitive
        if req.case_sensitive is not None
        else target_rule["case_sensitive"]
    )
    new_enabled = req.enabled if req.enabled is not None else target_rule["enabled"]

    updated_rule = CustomRule(
        id=UUID(str(target_rule["id"])),
        name=new_name,
        kind=new_kind,
        pattern=new_pattern,
        case_sensitive=new_case_sensitive,
        enabled=new_enabled,
    )
    current_rules[found_idx] = updated_rule.model_dump(mode="json")
    policy.custom_rules = current_rules
    policy.version += 1
    db.commit()
    db.refresh(policy)
    return updated_rule, policy.version


def delete_custom_rule(
    db: Session, organization_id: UUID, rule_id: UUID, expected_version: int
) -> tuple[UUID, int]:
    policy = get_or_create_policy(db, organization_id)
    if policy.version != expected_version:
        raise ApiError(409, "POLICY_VERSION_CONFLICT", "Policy version has changed")

    current_rules = list(policy.custom_rules or [])
    found_idx = None
    for idx, r in enumerate(current_rules):
        if str(r.get("id")) == str(rule_id):
            found_idx = idx
            break

    if found_idx is None:
        raise ApiError(404, "NOT_FOUND", "Custom rule not found")

    current_rules.pop(found_idx)
    policy.custom_rules = current_rules
    policy.version += 1
    db.commit()
    db.refresh(policy)
    return rule_id, policy.version


def preview_rule(req: RulePreviewRequest) -> RulePreviewResponse:
    validate_rule_pattern(req.kind, req.pattern)
    flags = 0 if req.case_sensitive else re.IGNORECASE

    if req.kind == "exact":
        compiled = re.compile(re.escape(req.pattern), flags=flags)
    else:
        compiled = re.compile(req.pattern, flags=flags)

    # Bounded evaluation with timeout safeguarding
    start_time = time.perf_counter()
    matches = []
    total_count = 0
    truncated = False

    for m in compiled.finditer(req.sample_text):
        if time.perf_counter() - start_time > 0.1:  # 100ms timeout
            raise ApiError(422, "RULE_TIMEOUT", "Rule evaluation timed out")
        total_count += 1
        if len(matches) < 1000:
            matches.append(PreviewMatch(start=m.start(), end=m.end()))
        else:
            truncated = True

    return RulePreviewResponse(
        matches=matches,
        count=total_count,
        truncated=truncated,
    )
