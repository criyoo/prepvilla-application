import json

from django.test import RequestFactory, TestCase, override_settings
from unittest.mock import MagicMock, patch
from rest_framework.test import APIClient
from core import views


@override_settings(ALLOWED_HOSTS=["dev.prepvilla.info"])
class HealthCheckTests(TestCase):
  def setUp(self):
    self.client = APIClient()
    self.factory = RequestFactory()

  def test_api_root_returns_service_metadata(self):
    response = self.client.get("/api/", HTTP_HOST="dev.prepvilla.info")

    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.json()["ok"])
    self.assertEqual(response.json()["service"], "api")
    self.assertEqual(response.json()["health"], "/api/health")

  def test_site_root_redirects_to_admin(self):
    response = self.client.get("/", HTTP_HOST="dev.prepvilla.info")

    self.assertEqual(response.status_code, 302)
    self.assertEqual(response["Location"], "/admin/")

  def test_api_root_without_trailing_slash_returns_service_metadata(self):
    response = self.client.get("/api", HTTP_HOST="dev.prepvilla.info")

    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.json()["ok"])
    self.assertEqual(response.json()["service"], "api")

  def test_ready_health_check_accepts_loopback_host(self):
    response = self.client.get("/api/health/ready", HTTP_HOST="127.0.0.1:8500")

    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.json()["ok"])

  def test_ready_health_check_accepts_target_ip_host(self):
    response = self.client.get("/api/health/ready", HTTP_HOST="10.30.19.29:8500")

    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.json()["ok"])

  def test_ready_health_check_reports_missing_core_tables(self):
    fake_cursor = MagicMock()
    fake_cursor.fetchone.return_value = (1,)
    fake_connection = MagicMock()
    fake_connection.cursor.return_value.__enter__.return_value = fake_cursor
    fake_connection.introspection.table_names.return_value = ["core_tutorprofile"]
    request = self.factory.get("/api/health/ready", HTTP_HOST="127.0.0.1:8500")

    with patch("core.views.connections", {"default": fake_connection}):
      response = views.health_ready(request)

    self.assertEqual(response.status_code, 503)
    payload = json.loads(response.content)
    self.assertFalse(payload["ok"])
    self.assertEqual(payload["error"], "schema_incomplete")
    self.assertIn("core_appuser", payload["missingTables"])

  def test_non_health_path_still_rejects_invalid_host(self):
    response = self.client.get("/api/auth/signup", HTTP_HOST="127.0.0.1:8500")

    self.assertEqual(response.status_code, 400)
