from datetime import UTC, datetime, timedelta

import pytest
from conftest import login_as
from pydantic import ValidationError
from sqlalchemy import select

from app.auth.sessions import COOKIE, token_hash
from app.config import Settings, get_settings
from app.db.models import AuthSession


def sign_in(env, email=None, password=None, **extra):
    return env.client.post(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:5173"},
        json={
            "email": email or env.users[0].email,
            "password": password or env.password,
            **extra,
        },
    )


def test_real_password_login_me_logout_and_revocation(env):
    response = sign_in(env)
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "manager"
    assert "password_hash" not in response.text
    assert (
        "HttpOnly" in response.headers["set-cookie"]
        and "SameSite=lax" in response.headers["set-cookie"]
    )
    token = env.client.cookies.get(COOKIE)
    stored = env.db.get(AuthSession, token_hash(token))
    assert stored and stored.token_hash != token
    me = env.client.get("/api/v1/auth/me")
    assert me.status_code == 200
    headers = {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": me.json()["csrf_token"],
    }
    assert (
        env.client.post("/api/v1/auth/logout", json={}, headers=headers).status_code
        == 204
    )
    env.client.cookies.set(COOKIE, token)
    assert env.client.get("/api/v1/auth/me").status_code == 401


def test_invalid_and_unknown_credentials_have_same_error(env):
    wrong = sign_in(env, password="wrong-password-at-least-12")
    absent = sign_in(env, email="nobody@example.com")
    assert wrong.status_code == absent.status_code == 401
    assert (
        wrong.json()["error"]["code"]
        == absent.json()["error"]["code"]
        == "INVALID_CREDENTIALS"
    )
    assert COOKIE not in env.client.cookies


def test_login_origin_and_privilege_input_denied(env):
    body = {"email": env.users[0].email, "password": env.password}
    assert env.client.post("/api/v1/auth/login", json=body).status_code == 403
    assert (
        env.client.post(
            "/api/v1/auth/login", json=body, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert sign_in(env, role="manager").status_code == 422
    assert sign_in(env, password="short").status_code == 422
    assert COOKIE not in env.client.cookies


def test_normalized_email_and_role_from_database(env):
    result = sign_in(env, email=env.users[1].email.upper())
    assert result.status_code == 200 and result.json()["user"]["role"] == "employee"
    assert env.client.get("/api/v1/organization/users").status_code == 403


def test_existing_session_replaced_by_new_login(env):
    assert sign_in(env).status_code == 200
    old = env.client.cookies.get(COOKIE)
    assert sign_in(env).status_code == 200
    assert old != env.client.cookies.get(COOKIE)
    assert env.db.get(AuthSession, token_hash(old)) is None


def test_forged_expired_and_inactive_session_denied(env):
    env.client.cookies.set(COOKIE, "a" * 43)
    assert env.client.get("/api/v1/auth/me").status_code == 401
    login_as(env, env.users[0])
    row = env.db.scalar(select(AuthSession))
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    env.db.commit()
    assert env.client.get("/api/v1/auth/me").status_code == 401
    login_as(env, env.users[0])
    env.users[0].active = False
    env.db.commit()
    assert env.client.get("/api/v1/auth/me").status_code == 403
    assert sign_in(env).status_code == 401


def test_csrf_token_and_origin_required_for_mutations(env):
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
    headers = {"Origin": "http://localhost:5173", "X-CSRF-Token": "a" * 64}
    assert (
        env.client.patch(
            "/api/v1/organization", json={"name": "Oops"}, headers=headers
        ).status_code
        == 403
    )


def test_account_lockout_is_persistent_and_expires(env):
    for _ in range(5):
        assert sign_in(env, password="wrong-password-long-enough").status_code == 401
    assert sign_in(env).status_code == 429
    env.users[0].locked_until = datetime.now(UTC) - timedelta(seconds=1)
    env.db.commit()
    assert sign_in(env).status_code == 200
    assert env.users[0].failed_login_attempts == 0 and env.users[0].locked_until is None


def test_secure_cookie_on_https(env, monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", "https://demo.example")
    get_settings.cache_clear()
    response = env.client.post(
        "/api/v1/auth/login",
        json={"email": env.users[0].email, "password": env.password},
        headers={"Origin": "https://demo.example"},
    )
    assert response.status_code == 200 and "Secure" in response.headers["set-cookie"]


def test_production_configuration_validation():
    with pytest.raises(ValidationError):
        Settings(app_env="production", demo_adapters_enabled=True)
    with pytest.raises(ValidationError):
        Settings(session_secret="short")


def test_no_provider_routes_or_public_registration(env):
    assert env.client.get("/api/v1/auth/callback?code=x&state=x").status_code == 404
    assert env.client.post("/api/v1/auth/register", json={}).status_code == 404
