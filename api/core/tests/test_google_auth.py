import os
from unittest.mock import patch
from urllib.parse import parse_qs

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import AppUser


GOOGLE_ENV = {
    "GOOGLE_OAUTH_CLIENT_ID": "test-client.apps.googleusercontent.com",
    "GOOGLE_OAUTH_CLIENT_SECRET": "test-secret",
}


@override_settings(
    CORS_ALLOWED_ORIGINS=["http://localhost:3500"],
    WEB_PUBLIC_URL="http://localhost:3500",
)
class GoogleAuthExchangeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch.dict(os.environ, GOOGLE_ENV, clear=False)
    def test_start_returns_client_id_for_popup_flow(self):
        response = self.client.get("/api/auth/google/start?mode=signup&role=student")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["clientId"], GOOGLE_ENV["GOOGLE_OAUTH_CLIENT_ID"])

    @patch.dict(os.environ, GOOGLE_ENV, clear=False)
    @patch("core.views._http_json")
    def test_popup_code_exchange_uses_frontend_origin_and_creates_account(self, http_json):
        http_json.side_effect = [
            {"id_token": "google-id-token"},
            {
                "aud": GOOGLE_ENV["GOOGLE_OAUTH_CLIENT_ID"],
                "email_verified": "true",
                "email": "newstudent@example.com",
                "name": "New Student",
            },
        ]

        response = self.client.post(
            "/api/auth/google/exchange",
            {"code": "authorization-code", "mode": "signup", "role": "student"},
            format="json",
            HTTP_ORIGIN="http://localhost:3500",
            HTTP_X_REQUESTED_WITH="XmlHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "newstudent@example.com")
        self.assertTrue(AppUser.objects.filter(email="newstudent@example.com", role="student").exists())
        token_request = parse_qs(http_json.call_args_list[0].kwargs["data"].decode("utf-8"))
        self.assertEqual(token_request["redirect_uri"], ["http://localhost:3500"])

    @patch.dict(os.environ, GOOGLE_ENV, clear=False)
    @patch("core.views._http_json")
    def test_popup_code_exchange_rejects_unapproved_origin(self, http_json):
        response = self.client.post(
            "/api/auth/google/exchange",
            {"code": "authorization-code", "mode": "signup", "role": "student"},
            format="json",
            HTTP_ORIGIN="https://malicious.example",
            HTTP_X_REQUESTED_WITH="XmlHttpRequest",
        )

        self.assertEqual(response.status_code, 403)
        http_json.assert_not_called()
