import logging

from django.db import connections
from django.http import JsonResponse
from django.utils import timezone


logger = logging.getLogger(__name__)


class HealthCheckHostBypassMiddleware:
  HEALTH_PATHS = {
    "/api/health",
    "/api/health/",
    "/api/health/live",
    "/api/health/live/",
    "/api/health/ready",
    "/api/health/ready/",
  }

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    if request.path_info not in self.HEALTH_PATHS:
      return self.get_response(request)

    if request.path_info in {"/api/health/ready", "/api/health/ready/"}:
      try:
        with connections["default"].cursor() as cursor:
          cursor.execute("SELECT 1")
          cursor.fetchone()
      except Exception as exc:
        logger.exception("Readiness check failed")
        return JsonResponse({"ok": False, "error": str(exc)}, status=503)

      return JsonResponse({"ok": True, "service": "api", "timestamp": timezone.now().isoformat()})

    if request.path_info in {"/api/health/live", "/api/health/live/"}:
      return JsonResponse({"ok": True, "service": "api", "timestamp": timezone.now().isoformat()})

    return JsonResponse({"ok": True, "timestamp": timezone.now().isoformat()})
