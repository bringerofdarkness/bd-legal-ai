"""
Unit Tests for Authentication & JWT Management (Sprint 5)
Validates token generation, decoding, guest sessions, and FastAPI auth endpoints.
"""

import unittest
import os
import sys
from datetime import timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.auth import (
    create_access_token,
    decode_access_token,
    create_guest_session,
    authenticate_user_token,
)
from app.api.main import app


class TestAuthService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_create_and_decode_token(self):
        token = create_access_token(
            data={"sub": "usr_test_1", "email": "advocate@bar.gov.bd", "role": "advocate"},
            expires_delta=timedelta(minutes=60),
            is_guest=False,
        )
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 20)

        payload = decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "usr_test_1")
        self.assertEqual(payload["email"], "advocate@bar.gov.bd")
        self.assertEqual(payload["role"], "advocate")
        self.assertFalse(payload["is_guest"])

    def test_expired_token(self):
        token = create_access_token(
            data={"sub": "usr_expired"},
            expires_delta=timedelta(seconds=-10),
            is_guest=False,
        )
        payload = decode_access_token(token)
        self.assertIsNone(payload)

    def test_invalid_token_string(self):
        payload = decode_access_token("not.a.valid.jwt.string")
        self.assertIsNone(payload)

    def test_guest_session(self):
        guest_auth = create_guest_session()
        self.assertTrue(guest_auth.is_guest)
        self.assertTrue(guest_auth.user_id.startswith("guest_"))
        self.assertGreater(guest_auth.expires_in_seconds, 0)

        # Decode and verify payload
        payload = decode_access_token(guest_auth.access_token)
        self.assertIsNotNone(payload)
        self.assertTrue(payload.get("is_guest"))
        self.assertEqual(payload.get("role"), "guest")

    def test_authenticate_user_token(self):
        token = create_access_token(
            data={"sub": "adv_99", "email": "advocate@court.bd", "full_name": "Rahim Ahmed", "role": "advocate"},
            is_guest=False,
        )
        user = authenticate_user_token(token)
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "adv_99")
        self.assertEqual(user.full_name, "Rahim Ahmed")
        self.assertTrue(user.is_authenticated)
        self.assertFalse(user.is_guest)

    def test_api_guest_endpoint(self):
        response = self.client.post("/v1/auth/guest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_guest"])
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_api_login_token_endpoint(self):
        response = self.client.post(
            "/v1/auth/token",
            json={"username_or_email": "tahmid@barcouncil.bd", "password": "securepassword"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertFalse(data["is_guest"])
        self.assertEqual(data["token_type"], "bearer")

    def test_api_me_guest_unauthenticated(self):
        response = self.client.get("/v1/auth/me")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_guest"])
        self.assertFalse(data["is_authenticated"])
        self.assertEqual(data["role"], "guest")

    def test_api_me_authenticated_user(self):
        # Obtain token
        login_resp = self.client.post(
            "/v1/auth/token",
            json={"username_or_email": "advocate_karim", "password": "anypassword"}
        )
        token = login_resp.json()["access_token"]

        # Call /v1/auth/me with Bearer token
        me_resp = self.client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(me_resp.status_code, 200)
        data = me_resp.json()
        self.assertTrue(data["is_authenticated"])
        self.assertFalse(data["is_guest"])
        self.assertEqual(data["role"], "advocate")
        self.assertEqual(data["full_name"], "Advocate Advocate_karim")


if __name__ == "__main__":
    unittest.main()
