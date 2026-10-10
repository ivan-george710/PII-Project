import unittest

from fastapi.testclient import TestClient

from app.main import app


class HealthTests(unittest.TestCase):
    def test_health_response(self):
        with TestClient(app) as client:
            response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["service"], "pii-guard-api")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_openapi_exposes_health(self):
        with TestClient(app) as client:
            response = client.get("/api/openapi.json")
        self.assertIn("/api/health", response.json()["paths"])


def test_health_reports_exact_commit(monkeypatch):
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "a" * 40)
    with TestClient(app) as client:
        assert client.get("/api/health").json()["commit"] == "a" * 40
        paths = client.get("/api/openapi.json").json()["paths"]
        assert "/api/v1/auth/signup" in paths
        assert "post" in paths["/api/v1/auth/login"]
        assert "/api/v1/organization/assignments" in paths


def test_configuration_error_names_setting_without_leaking_value(env, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("SESSION_SECRET", "private-short-value")
    get_settings.cache_clear()
    response = env.client.get("/api/v1/auth/me")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CONFIGURATION_ERROR"
    assert response.json()["error"]["fields"] == [
        {"path": "SESSION_SECRET", "message": "Invalid setting"}
    ]
    assert "private-short-value" not in response.text
    assert "input_value" not in response.text


def test_missing_session_configuration_names_required_setting(env, monkeypatch):
    from app.config import get_settings

    monkeypatch.delenv("SESSION_SECRET")
    get_settings.cache_clear()
    response = env.client.get("/api/v1/auth/me")
    assert response.status_code == 503
    assert response.json()["error"]["fields"] == [
        {"path": "SESSION_SECRET", "message": "Required setting"}
    ]


def test_implemented_router_is_registered(monkeypatch):
    from types import SimpleNamespace
    from fastapi import APIRouter, FastAPI
    from app import dependencies

    router = APIRouter()

    @router.get("/api/v1/chat-integration-check")
    def endpoint():
        return {"connected": True}

    monkeypatch.setattr(dependencies, "find_spec", lambda name: object() if name == "app.routes.chat" else None)
    monkeypatch.setattr(dependencies, "import_module", lambda name: SimpleNamespace(router=router))
    isolated = FastAPI()
    dependencies.register_feature_routers(isolated)
    with TestClient(isolated) as client:
        assert client.get("/api/v1/chat-integration-check").json() == {"connected": True}


def test_broken_implemented_router_cannot_silently_disappear(monkeypatch):
    import pytest
    from fastapi import FastAPI
    from app import dependencies

    monkeypatch.setattr(dependencies, "find_spec", lambda name: object())

    def broken_import(name):
        raise ModuleNotFoundError("Missing internal processing dependency")

    monkeypatch.setattr(dependencies, "import_module", broken_import)
    with pytest.raises(ModuleNotFoundError, match="internal processing"):
        dependencies.register_feature_routers(FastAPI())


def test_feature_routes_have_unique_openapi_operations():
    import warnings

    # Generate afresh after all test modules have been imported: tests must not
    # install duplicate routes on the shared production app during collection.
    previous_schema = app.openapi_schema
    try:
        app.openapi_schema = None
        with warnings.catch_warnings():
            warnings.filterwarnings("error", message="Duplicate Operation ID.*")
            schema = app.openapi()
        assert "/api/v1/conversations" in schema["paths"]
        assert "/api/v1/uploads/init" in schema["paths"]
        assert "/api/v1/demo/samples" in schema["paths"]
    finally:
        app.openapi_schema = previous_schema


def test_production_health_checks_models(env, monkeypatch):
    from app.services import engine_adapter
    calls = []
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(engine_adapter, "privacy_engine", lambda: calls.append(True))
    assert env.client.get("/api/health").status_code == 200
    assert calls == [True]


def test_production_health_fails_when_models_are_missing(env, monkeypatch):
    from app.services import engine_adapter
    monkeypatch.setenv("APP_ENV", "production")
    def unavailable():
        raise RuntimeError("private model path and internal dependency details")
    monkeypatch.setattr(engine_adapter, "privacy_engine", unavailable)
    response = env.client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GUARD_UNAVAILABLE"
    assert "private model path" not in response.text
