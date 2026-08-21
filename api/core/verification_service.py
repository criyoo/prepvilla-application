from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework.exceptions import APIException

from . import prembly_verification
from . import dikript_verification


class VerificationProviderUnavailable(APIException):
    status_code = 503
    default_detail = "Verification provider is not configured."
    default_code = "verification_provider_unavailable"


def _provider_module():
    provider = str(getattr(settings, "VERIFICATION_SERVICE", "prembly") or "prembly").strip().lower()
    if provider == "prembly":
        return prembly_verification
    if provider == "dikript":
        return dikript_verification
    raise VerificationProviderUnavailable(detail=f"Unsupported verification provider: {provider}")


def is_verification_configured() -> bool:
    service = _provider_module()
    checker = getattr(service, "is_prembly_configured", None) or getattr(service, "is_dikript_configured", None)
    return bool(checker and checker())


def _require_configured_provider():
    service = _provider_module()
    checker = getattr(service, "is_prembly_configured", None) or getattr(service, "is_dikript_configured", None)
    if not checker or not checker():
        raise VerificationProviderUnavailable()
    return service


def verify_nin_identity(**kwargs):
    return _require_configured_provider().verify_nin_identity(**kwargs)


def verify_nin_and_bvn(input_data: dict[str, Any], nin_number: str, bvn_number: str):
    return _require_configured_provider().verify_nin_and_bvn(input_data, nin_number, bvn_number)


def verify_cac(input_data: dict[str, Any], registration_number: str):
    return _require_configured_provider().verify_cac(input_data, registration_number)
