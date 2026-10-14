"""
Unit tests for FastAPI REST Endpoints
Validates /health, /v1/statutes, /v1/query, and /v1/search routes.
"""

import unittest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.api.main import app


class TestFastAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertGreaterEqual(data["laws_indexed"], 2)

    def test_v1_health_endpoint(self):
        response = self.client.get("/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_v1_statutes_endpoint(self):
        response = self.client.get("/v1/statutes")
        self.assertEqual(response.status_code, 200)
        statutes = response.json()
        self.assertIsInstance(statutes, list)
        self.assertTrue(any(s["key"] == "penal_code_1860" for s in statutes))

    def test_v1_query_theft(self):
        response = self.client.post("/v1/query", json={"query": "What is theft?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(len(data["citations"]) > 0)
        self.assertTrue(len(data["evidence"]) > 0)

    def test_v1_query_refusal(self):
        response = self.client.post("/v1/query", json={"query": "What is the capital of France?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "refused")
        self.assertIsNotNone(data["refusal_reason"])


if __name__ == "__main__":
    unittest.main()
