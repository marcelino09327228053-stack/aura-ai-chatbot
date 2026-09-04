"""Google sign-in flow and verified-email account linking."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

test_db = Path(tempfile.gettempdir()) / "mb_google_oauth_test.db"
test_db.unlink(missing_ok=True)
os.environ["SQLITE_PATH"] = str(test_db)
os.environ["SECRET_KEY"] = "google-oauth-test-secret-that-is-long-enough"
os.environ["REDIS_ENABLED"] = "false"
os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "test-google-client"
os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "test-google-secret"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from main import app


class GoogleOAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        from app.infrastructure.database import sqlite_backend
        if sqlite_backend._conn is not None:
            sqlite_backend._conn.close()
            sqlite_backend._conn = None
        test_db.unlink(missing_ok=True)

    def test_google_sign_in_links_existing_verified_email(self):
        registered = self.client.post("/auth/register", json={
            "email": "same-user@example.com",
            "password": "test-password",
            "company_name": "Existing Company",
        })
        self.assertEqual(registered.status_code, 200, registered.text)

        start = self.client.get("/auth/google/start", follow_redirects=False)
        self.assertEqual(start.status_code, 307)
        query = parse_qs(urlparse(start.headers["location"]).query)
        self.assertEqual(query["scope"], ["openid email profile"])

        with (
            patch("app.api.auth._post_google_token", return_value={"access_token": "access"}),
            patch("app.api.auth._get_google_userinfo", return_value={
                "sub": "google-subject-123",
                "email": "same-user@example.com",
                "email_verified": True,
                "name": "Same User",
                "picture": "https://example.com/photo.png",
            }),
        ):
            callback = self.client.get(
                "/auth/google/callback",
                params={"code": "authorization-code", "state": query["state"][0]},
            )
        self.assertEqual(callback.status_code, 200, callback.text)
        self.assertIn("localStorage.setItem('aura_token'", callback.text)

        from app.database import oauth_identity_repository, user_repository
        self.assertEqual(user_repository.count_users(), 1)
        identity = oauth_identity_repository.get_identity("google", "google-subject-123")
        self.assertIsNotNone(identity)


if __name__ == "__main__":
    unittest.main()
