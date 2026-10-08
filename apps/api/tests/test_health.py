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
