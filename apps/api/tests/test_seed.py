import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.models import ManagerAssignment, User

root = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("demo_seed", root / "demo/seed.py")
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


def test_fictional_seed_is_idempotent_and_explicit(env, monkeypatch):
    from app.config import get_settings

    values = json.loads((root / "demo/identities.json").read_text())
    with pytest.raises(ValueError):
        seed.seed(env.db, "Demo Company", values)
    monkeypatch.setenv("DEMO_ADAPTERS_ENABLED", "true")
    get_settings.cache_clear()
    first = seed.seed(env.db, "Demo Company", values)
    second = seed.seed(env.db, "Demo Company", values)
    assert first == second and not first["policy_seeded"]
    assert env.db.scalar(select(func.count()).select_from(ManagerAssignment)) == 2
    assert env.db.scalar(select(func.count()).select_from(User)) == 7
