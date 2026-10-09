from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.passwords import hash_password
from app.auth.sessions import COOKIE, create_session, csrf_token
from app.config import get_settings
from app.db.base import Base
from app.db.models import Organization, User
from app.db.session import get_db
from app.main import app

TEST_PASSWORD = "fictional-test-password-123"
TEST_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PUBLIC_APP_URL", "http://localhost:5173")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-only-not-production-123")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = sessionmaker(engine, expire_on_commit=False)()
    companies = [Organization(name="Demo"), Organization(name="Other")]
    db.add_all(companies)
    db.flush()
    users = []
    for name, role, org in [
        ("Manager", "manager", companies[0]),
        ("Employee", "employee", companies[0]),
        ("Second manager", "manager", companies[0]),
        ("Foreign", "employee", companies[1]),
    ]:
        user = User(
            organization_id=org.id,
            email=name.replace(" ", "").lower() + "@example.org",
            display_name=name,
            role=role,
            password_hash=TEST_HASH,
        )
        users.append(user)
        db.add(user)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            db=db,
            users=users,
            companies=companies,
            password=TEST_PASSWORD,
        )
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()
    get_settings.cache_clear()


def login_as(env, user):
    token = create_session(env.db, user)
    env.db.commit()
    env.client.cookies.set(COOKIE, token)
    return {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": csrf_token(
            token, get_settings().session_secret.get_secret_value()
        ),
    }
