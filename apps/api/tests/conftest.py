from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.sessions import csrf_token
from app.auth.workos import get_gateway
from app.config import get_settings
from app.db.base import Base
from app.db.models import Organization, User
from app.db.session import get_db
from app.main import app


class FakeGateway:
    def __init__(self):
        self.sessions = {}
        self.revoked = []
        self.verifier = None

    def authorization_url(self, state, challenge):
        self.state = state
        self.challenge = challenge
        return "https://signin.workos.com/authorize?state=" + state

    def exchange(self, code, verifier):
        self.verifier = verifier
        return code

    def authenticate(self, cookie):
        if cookie not in self.sessions:
            raise ValueError("Invalid test session")
        return self.sessions[cookie]

    def revoke(self, session_id):
        self.revoked.append(session_id)


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PUBLIC_APP_URL", "http://localhost:5173")
    monkeypatch.setenv(
        "WORKOS_REDIRECT_URI", "http://localhost:5173/api/v1/auth/callback"
    )
    monkeypatch.setenv("WORKOS_COOKIE_PASSWORD", Fernet.generate_key().decode())
    monkeypatch.setenv("WORKOS_API_KEY", "sk_test_fixture")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_fixture")
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
            workos_user_id="user_" + str(uuid4()),
            organization_id=org.id,
            email=name.replace(" ", "").lower() + "@example.com",
            display_name=name,
            role=role,
        )
        users.append(user)
        db.add(user)
    db.commit()
    gateway = FakeGateway()
    for u in users:
        gateway.sessions[str(u.id)] = SimpleNamespace(
            user={"id": u.workos_user_id},
            organization_id=None,
            session_id="session_" + str(u.id),
        )
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_gateway] = lambda: gateway
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client, db=db, users=users, companies=companies, gateway=gateway
        )
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()
    get_settings.cache_clear()


def login_as(env, user):
    cookie = str(user.id)
    env.client.cookies.set("wos-session", cookie)
    return {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": csrf_token(
            "session_" + cookie,
            get_settings().workos_cookie_password.get_secret_value(),
        ),
    }
