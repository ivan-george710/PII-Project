from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect, select

from app.config import get_settings


def test_provider_migration_preserves_company_users_and_assignments(
    tmp_path, monkeypatch
):
    api = Path(__file__).resolve().parents[1]
    database = "sqlite:///" + str(tmp_path / "legacy.db")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database)
    get_settings.cache_clear()
    cfg = Config(str(api / "alembic.ini"))
    cfg.set_main_option("script_location", str(api / "migrations"))
    command.upgrade(cfg, "0001_company_identity")
    engine = create_engine(database)
    old = MetaData()
    old.reflect(engine)
    org, manager, employee = uuid4().hex, uuid4().hex, uuid4().hex
    now = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(
            old.tables["organizations"].insert(),
            {
                "id": org,
                "name": "Existing",
                "workos_organization_id": "org_old",
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            old.tables["users"].insert(),
            [
                {
                    "id": user,
                    "organization_id": org,
                    "workos_user_id": "user_" + str(user),
                    "email": email,
                    "display_name": role,
                    "role": role,
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                }
                for user, email, role in [
                    (manager, "MANAGER@example.org", "manager"),
                    (employee, "employee@example.org", "employee"),
                ]
            ],
        )
        conn.execute(
            old.tables["manager_assignments"].insert(),
            {
                "employee_id": employee,
                "manager_id": manager,
                "organization_id": org,
                "updated_at": now,
            },
        )
    command.upgrade(cfg, "head")
    command.check(cfg)
    new = MetaData()
    new.reflect(engine)
    with engine.connect() as conn:
        users = conn.execute(select(new.tables["users"])).mappings().all()
        assignments = (
            conn.execute(select(new.tables["manager_assignments"])).mappings().all()
        )
    assert {row["id"] for row in users} == {manager, employee}
    assert {row["email"] for row in users} == {
        "manager@example.org",
        "employee@example.org",
    }
    assert all(row["password_hash"] is None for row in users)
    assert (
        assignments[0]["manager_id"] == manager
        and assignments[0]["employee_id"] == employee
    )
    assert "workos_user_id" not in new.tables["users"].c
    assert "workos_organization_id" not in new.tables["organizations"].c
    assert any(
        "role" in c["sqltext"] for c in inspect(engine).get_check_constraints("users")
    )
    engine.dispose()
    get_settings.cache_clear()
