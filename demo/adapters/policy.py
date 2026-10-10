"""Supplied versioned company policy adapter for independent feature testing."""

from uuid import UUID

from app.config import get_settings
from app.schemas.rules import CustomRule, PolicySnapshot, RuleId


def get_demo_policy(organization_id: UUID, version: int = 1) -> PolicySnapshot:
    settings = get_settings()
    if (
        settings.app_env not in ("development", "test")
        or not settings.demo_adapters_enabled
    ):
        raise ValueError("Synthetic policy requires an explicit development/test flag")

    builtins = {rule.value: True for rule in RuleId}
    custom_rules = [
        CustomRule(
            id=UUID("00000000-0000-4000-8000-000000000001"),
            name="Project Phoenix",
            kind="exact",
            pattern="Project Phoenix",
            case_sensitive=False,
            enabled=True,
        )
    ]
    return PolicySnapshot(
        organization_id=organization_id,
        version=version,
        builtins=builtins,  # type: ignore
        custom_rules=custom_rules,
    )
