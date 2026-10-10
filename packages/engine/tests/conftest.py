from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from pii_guard.models import ArtifactInput, CustomRule, PolicySnapshot
from pii_guard.rules import BUILTIN_RULE_IDS


@pytest.fixture
def builtins_all_enabled() -> dict[str, bool]:
    return {rule_id: True for rule_id in BUILTIN_RULE_IDS}


@pytest.fixture
def policy_snapshot(builtins_all_enabled: dict[str, bool]) -> PolicySnapshot:
    return PolicySnapshot(
        organization_id=uuid4(),
        version=1,
        builtins=builtins_all_enabled,
        custom_rules=[],
    )


@pytest.fixture
def custom_rule() -> CustomRule:
    return CustomRule(
        id=uuid4(),
        name="Customer phrase",
        kind="exact",
        pattern="Project Blue",
        case_sensitive=False,
        enabled=True,
    )


@pytest.fixture
def artifact_input(tmp_path: Path) -> ArtifactInput:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.7\n")
    return ArtifactInput(
        id=uuid4(),
        filename="source.pdf",
        source_path=source,
        declared_mime="application/pdf",
    )
