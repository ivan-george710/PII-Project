import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings, get_settings
from app.dependencies import (
    get_app_settings,
    get_current_identity,
    get_event_sink,
    get_file_storage,
    get_llm_client,
    get_policy_store,
    get_privacy_engine,
)
from app.main import app
from app.schemas.common import ApiError


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
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/health", response.json()["paths"])

    def test_config_missing_workos_lists_names_not_secrets(self):
        settings = Settings(
            app_env="development",
            workos_api_key=None,
            workos_client_id=None,
            workos_cookie_password=None,
        )
        with self.assertRaises(ApiError) as ctx:
            settings.require_workos()
        self.assertEqual(ctx.exception.status, 503)
        self.assertIn("WORKOS_API_KEY", ctx.exception.message)
        self.assertIn("WORKOS_CLIENT_ID", ctx.exception.message)
        self.assertIn("WORKOS_COOKIE_PASSWORD", ctx.exception.message)

    def test_config_missing_llm_lists_names_not_secrets(self):
        settings = Settings(app_env="development", openai_api_key=None)
        with self.assertRaises(ApiError) as ctx:
            settings.require_llm()
        self.assertEqual(ctx.exception.status, 503)
        self.assertIn("OPENAI_API_KEY", ctx.exception.message)

    def test_dependencies_exist(self):
        settings = get_settings()
        self.assertIsNotNone(get_app_settings())
        self.assertIsNotNone(get_privacy_engine(settings=settings))
        self.assertIsNotNone(get_file_storage(settings=settings))
        self.assertIsNotNone(get_llm_client(settings=settings))
