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


def test_local_provisioning_keeps_roles_and_revokes_on_password_reset(env):
    from conftest import login_as
    from app.auth.sessions import COOKIE
    from app.auth.passwords import verify_password
    from app.db.models import AuthSession
    from sqlalchemy import select

    spec = importlib.util.spec_from_file_location(
        "provision", root / "scripts/provision-company.py"
    )
    provisioner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(provisioner)
    user = env.users[0]
    login_as(env, user)
    identity = {
        "email": user.email,
        "display_name": user.display_name,
        "role": "manager",
    }
    original_hash = user.password_hash
    provisioner.provision(env.db, user.organization_id, "Demo", identity, env.password)
    assert user.password_hash == original_hash
    new_password = "new-fictional-password-123"
    provisioner.provision(
        env.db,
        user.organization_id,
        "Demo",
        identity,
        new_password,
        reset_password=True,
    )
    assert verify_password(new_password, user.password_hash)
    assert env.db.scalar(select(AuthSession)) is None
    assert env.client.get("/api/v1/auth/me").status_code == 401
    identity["role"] = "employee"
    with pytest.raises(ValueError):
        provisioner.provision(
            env.db, user.organization_id, "Demo", identity, env.password
        )
