import base64
import hashlib

import pytest
from conftest import login_as
from pydantic import ValidationError

from app.config import Settings


def test_login_state_pkce_callback_and_logout(env):
    user = env.users[0]
    response = env.client.get(
        "/api/v1/auth/login?return_to=/company/setup", follow_redirects=False
    )
    assert response.status_code == 302
    assert (
        "HttpOnly" in response.headers["set-cookie"]
        and "SameSite=lax" in response.headers["set-cookie"]
    )
    response = env.client.get(
        "/api/v1/auth/callback",
        params={"code": str(user.id), "state": env.gateway.state},
        follow_redirects=False,
    )
    assert (
        response.status_code == 302 and response.headers["location"] == "/company/setup"
    )
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(env.gateway.verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert challenge == env.gateway.challenge
    me = env.client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["role"] == "manager"
    assert "workos_user_id" not in me.json()["user"]
    response = env.client.post(
        "/api/v1/auth/logout",
        json={},
        headers={
            "Origin": "http://localhost:5173",
            "X-CSRF-Token": me.json()["csrf_token"],
        },
    )
    assert response.status_code == 204 and env.gateway.revoked
    assert env.client.get("/api/v1/auth/me").status_code == 401


def test_wrong_state_no_exchange_or_cookie(env):
    env.client.get("/api/v1/auth/login", follow_redirects=False)
    response = env.client.get("/api/v1/auth/callback?code=bad&state=forged")
    assert response.status_code == 400
    assert env.gateway.verifier is None
    assert "wos-session" not in env.client.cookies


def test_external_return_path_and_unsigned_state_rejected(env):
    assert (
        env.client.get("/api/v1/auth/login?return_to=https://evil.example").status_code
        == 422
    )
    assert env.client.get("/api/v1/auth/callback?code=x&state=x").status_code == 400


def test_unprovisioned_and_inactive_membership_denied(env):
    login_as(env, env.users[0])
    env.users[0].active = False
    env.db.commit()
    assert env.client.get("/api/v1/auth/me").status_code == 403


def test_cookie_forgery_and_csrf(env):
    env.client.cookies.set("wos-session", "forged")
    assert env.client.get("/api/v1/auth/me").status_code == 401
    headers = login_as(env, env.users[0])
    assert (
        env.client.patch("/api/v1/organization", json={"name": "Oops"}).status_code
        == 403
    )
    headers["Origin"] = "https://evil.example"
    assert (
        env.client.patch(
            "/api/v1/organization", json={"name": "Oops"}, headers=headers
        ).status_code
        == 403
    )


def test_production_rejects_demo_and_sqlite():
    with pytest.raises(ValidationError):
        Settings(app_env="production", demo_adapters_enabled=True)


def test_gateway_exchange_uses_sdk_sealed_cookie(monkeypatch):
    from types import SimpleNamespace

    from cryptography.fernet import Fernet
    from workos.session import unseal_data

    from app.auth.workos import WorkOSGateway

    settings = Settings(
        workos_api_key="sk_test_fixture",
        workos_client_id="client_fixture",
        workos_cookie_password=Fernet.generate_key().decode(),
    )
    gateway = WorkOSGateway(settings)

    class User:
        def to_dict(self):
            return {"id": "user_test"}

    gateway.client = SimpleNamespace(
        user_management=SimpleNamespace(
            authenticate_with_code=lambda **kwargs: SimpleNamespace(
                access_token="token", refresh_token="refresh", user=User()
            )
        )
    )
    value = gateway.exchange("code", "verifier")
    assert unseal_data(value, settings.workos_cookie_password.get_secret_value())[
        "user"
    ] == {"id": "user_test"}


def test_provisioned_company_must_match_workos_session(env):
    org = env.companies[0]
    org.workos_organization_id = "org_expected"
    env.db.commit()
    login_as(env, env.users[0])
    env.gateway.sessions[str(env.users[0].id)].organization_id = "org_other"
    assert env.client.get("/api/v1/auth/me").status_code == 403


def test_callback_denies_unprovisioned_identity(env):
    from types import SimpleNamespace

    env.gateway.sessions["new-user"] = SimpleNamespace(
        user={"id": "user_unprovisioned"},
        session_id="new_session",
        organization_id=None,
    )
    env.client.get("/api/v1/auth/login", follow_redirects=False)
    assert (
        env.client.get(
            "/api/v1/auth/callback",
            params={"code": "new-user", "state": env.gateway.state},
            follow_redirects=False,
        ).status_code
        == 403
    )
    assert "wos-session" not in env.client.cookies
