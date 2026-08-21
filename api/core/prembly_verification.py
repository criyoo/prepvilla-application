from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import APIException, ValidationError

logger = logging.getLogger(__name__)


class PremblyVerificationUnavailable(APIException):
    status_code = 503
    default_detail = "Prembly verification is temporarily unavailable."
    default_code = "prembly_verification_unavailable"


def is_prembly_configured() -> bool:
    return bool(
        str(getattr(settings, "PREMBLY_API_BASE_URL", "") or "").strip()
        and str(
            getattr(settings, "PREMBLY_API_SECRET_KEY", "")
            or getattr(settings, "PREMBLY_API_KEY", "")
            or ""
        ).strip()
    )


def _api_key() -> str:
    return str(
        getattr(settings, "PREMBLY_API_SECRET_KEY", "")
        or getattr(settings, "PREMBLY_API_KEY", "")
        or ""
    ).strip()


def _decode(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PremblyVerificationUnavailable(detail="Prembly returned an invalid response.") from exc
    return payload if isinstance(payload, dict) else {}


def extract_prembly_message(payload: dict[str, Any]) -> str:
    return str(payload.get("message") or payload.get("detail") or payload.get("error") or "").strip()


def _is_success(payload: dict[str, Any]) -> bool:
    status = payload.get("status")
    response_code = str(payload.get("response_code") or payload.get("code") or "").strip()
    verification = payload.get("verification")
    verification_status = str(
        payload.get("verification_status")
        or (verification.get("status") if isinstance(verification, dict) else "")
        or ""
    ).strip().lower()
    if response_code and response_code not in {"00", "200"}:
        return False
    if verification_status and verification_status not in {"verified", "successful", "success"}:
        return False
    return status is True or response_code in {"00", "200"} or verification_status in {"verified", "successful", "success"}


def prembly_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    if not is_prembly_configured():
        raise PremblyVerificationUnavailable(detail="Prembly credentials are not configured.")

    base_url = str(settings.PREMBLY_API_BASE_URL).rstrip("/")
    request = Request(
        f"{base_url}/{str(path).lstrip('/')}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": _api_key(),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=int(getattr(settings, "PREMBLY_TIMEOUT_SECONDS", 10))) as response:
            return _decode(response.read())
    except HTTPError as exc:
        try:
            payload = _decode(exc.read())
        except PremblyVerificationUnavailable:
            payload = {}
        if exc.code in {400, 404, 422} and payload:
            return payload
        raise PremblyVerificationUnavailable(detail=extract_prembly_message(payload) or None) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise PremblyVerificationUnavailable() from exc


def prembly_lookup(*, verification_type: str, lookup_value: str, body: dict[str, Any]) -> dict[str, Any]:
    value_hash = hashlib.sha256(str(lookup_value).strip().encode("utf-8")).hexdigest()
    cache_key = f"prepvilla:prembly:{verification_type}:{value_hash}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return cached
    paths = {
        "nin": getattr(settings, "PREMBLY_NIN_API_URL", "/verification/vnin"),
        "bvn": getattr(settings, "PREMBLY_BVN_API_URL", "/verification/bvn"),
        "cac": getattr(settings, "PREMBLY_CAC_API_URL", "/verification/cac"),
    }
    try:
        payload = prembly_post(str(paths[verification_type]), body)
    except KeyError as exc:
        raise ValidationError({"verification_type": "Unsupported Prembly verification type."}) from exc
    cache.set(
        cache_key,
        payload,
        timeout=int(getattr(settings, "PREMBLY_LOOKUP_CACHE_TIMEOUT_SECONDS", 86400)),
    )
    return payload


def _payload_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    for key in ("nin_data", "bvn_data", "verification"):
        data = payload.get(key)
        if isinstance(data, dict):
            return data
    return {}


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return ""


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _normalize_digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _normalize_phone(value: Any) -> str:
    digits = _normalize_digits(value)
    if digits.startswith("234"):
        digits = digits[3:]
    if digits.startswith("0"):
        digits = digits[1:]
    return digits


def _parse_date(value: Any):
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw[:20], fmt).date()
            except ValueError:
                continue
    return None


def _required_match(expected: Any, actual: Any) -> bool:
    return bool(_normalize_text(expected)) and _normalize_text(expected) == _normalize_text(actual)


def _optional_match(expected: Any, actual: Any) -> bool:
    return not _normalize_text(expected) or not _normalize_text(actual) or _normalize_text(expected) == _normalize_text(actual)


def _normalize_region(value: Any) -> str:
    return " ".join(re.sub(r"\bSTATE\b", "", _normalize_text(value)).split())


def _normalize_nationality(value: Any) -> str:
    normalized = _normalize_text(value)
    return "NIGERIA" if normalized == "NIGERIAN" else normalized


def _normalize_country(value: Any) -> str:
    normalized = _normalize_text(value)
    return "NIGERIA" if normalized == "NIGERIAN" else normalized


def _normalize_gender(value: Any) -> str:
    return _normalize_text(value)[:1]


def _validate_nin_fields(input_data: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    mismatches: dict[str, str] = {}
    country_of_birth = _first_present(data, "birthCountry", "countryOfBirth", "country_of_birth", "birth_country")
    if not _required_match(input_data.get("first_name"), _first_present(data, "firstname", "firstName", "first_name")):
        mismatches["first_name"] = "First name does not match the NIN record."
    if not _required_match(input_data.get("last_name"), _first_present(data, "surname", "lastName", "lastname", "last_name")):
        mismatches["last_name"] = "Last name does not match the NIN record."
    if not _optional_match(input_data.get("middle_name"), _first_present(data, "middlename", "middleName", "othername", "otherName", "middle_name")):
        mismatches["middle_name"] = "Middle name does not match the NIN record."
    if _parse_date(input_data.get("date_of_birth")) != _parse_date(_first_present(data, "birthdate", "birthDate", "dateOfBirth", "date_of_birth")):
        mismatches["date_of_birth"] = "Date of birth does not match the NIN record."
    if input_data.get("country_of_birth") and country_of_birth and _normalize_country(input_data.get("country_of_birth")) != _normalize_country(country_of_birth):
        mismatches["country_of_birth"] = "Country of birth does not match the NIN record."
    optional_fields = (
        ("state_of_origin", ("selfOriginState", "stateOfOrigin", "state_of_origin"), _normalize_region, "State of origin"),
        ("lga", ("selfOriginLga", "lgaOfOrigin", "lga", "lga_of_origin"), _normalize_region, "LGA"),
        ("nationality", ("nationality",), _normalize_nationality, "Nationality"),
    )
    for field, keys, normalizer, label in optional_fields:
        submitted = input_data.get(field)
        actual = _first_present(data, *keys)
        if submitted not in (None, "") and actual not in (None, "") and normalizer(submitted) != normalizer(actual):
            mismatches[field] = f"{label} does not match the NIN record."
    return mismatches


def _validate_bvn_fields(input_data: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    mismatches: dict[str, str] = {}
    if not _required_match(input_data.get("first_name"), _first_present(data, "firstname", "firstName", "first_name")):
        mismatches["first_name"] = "First name does not match the BVN record."
    if not _required_match(input_data.get("last_name"), _first_present(data, "surname", "lastName", "lastname", "last_name")):
        mismatches["last_name"] = "Last name does not match the BVN record."
    if not _optional_match(input_data.get("middle_name"), _first_present(data, "middlename", "middleName", "othername", "otherName", "middle_name")):
        mismatches["middle_name"] = "Middle name does not match the BVN record."
    if _parse_date(input_data.get("date_of_birth")) != _parse_date(_first_present(data, "birthdate", "birthDate", "dateOfBirth", "date_of_birth")):
        mismatches["date_of_birth"] = "Date of birth does not match the BVN record."

    optional_fields = (
        ("gender", ("gender",), _normalize_gender, "Gender"),
        ("state_of_origin", ("stateOfOrigin", "state_of_origin"), _normalize_region, "State of origin"),
        ("lga", ("lgaOfOrigin", "lga", "lga_of_origin"), _normalize_region, "LGA"),
        ("nationality", ("nationality",), _normalize_nationality, "Nationality"),
    )
    for field, keys, normalizer, label in optional_fields:
        submitted = input_data.get(field)
        if submitted not in (None, "") and normalizer(submitted) != normalizer(_first_present(data, *keys)):
            mismatches[field] = f"{label} does not match the BVN record."

    submitted_country = input_data.get("country_of_birth")
    actual_country = _first_present(data, "countryOfBirth", "birthCountry", "country_of_birth", "birth_country")
    if submitted_country and actual_country and _normalize_country(submitted_country) != _normalize_country(actual_country):
        mismatches["country_of_birth"] = "Country of birth does not match the BVN record."

    submitted_mobile = input_data.get("mobile")
    actual_mobile = _first_present(data, "phoneNumber1", "phoneNumber", "telephoneno", "telephoneNo", "mobile")
    if not _normalize_phone(submitted_mobile) or not _normalize_phone(actual_mobile) or _normalize_phone(submitted_mobile) != _normalize_phone(actual_mobile):
        mismatches["mobile"] = "Mobile number does not match the BVN record."
    return mismatches


def validate_nin_payload(input_data: dict[str, Any], data: dict[str, Any], *, defer_phone_mismatch: bool = False) -> tuple[dict[str, str], bool]:
    mismatches = _validate_nin_fields(input_data, data)
    actual_mobile = _first_present(data, "telephoneno", "telephoneNo", "phoneNumber", "mobile")
    phone_mismatch = not _normalize_phone(input_data.get("mobile")) or not _normalize_phone(actual_mobile) or _normalize_phone(input_data.get("mobile")) != _normalize_phone(actual_mobile)
    if phone_mismatch:
        mismatches["mobile"] = "Mobile number does not match the NIN record."
    return mismatches, phone_mismatch


def validate_bvn_payload(input_data: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    return _validate_bvn_fields(input_data, data)


def _merge_field_mismatches(nin_mismatches: dict[str, str], bvn_mismatches: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in {"first_name", "last_name", "middle_name", "date_of_birth", "mobile", "country_of_birth"}:
        if field in nin_mismatches and field in bvn_mismatches:
            result[field] = bvn_mismatches[field]
    for field in {"gender", "state_of_origin", "lga", "nationality"}:
        if field in bvn_mismatches:
            result[field] = bvn_mismatches[field]
    return result


def verify_nin_identity(
    *,
    nin_number: str,
    first_name: str = "",
    last_name: str = "",
    middle_name: str = "",
    date_of_birth: Any = None,
    mobile_number: str = "",
    country_of_birth: str = "",
    nationality: str = "",
    state_of_origin: str = "",
    lga: str = "",
) -> dict[str, Any]:
    normalized_nin = "".join(str(nin_number or "").split())
    if len(normalized_nin) != 11 or not normalized_nin.isdigit():
        raise ValidationError({"ninNumber": "NIN must contain 11 digits."})
    payload = prembly_lookup(
        verification_type="nin",
        lookup_value=normalized_nin,
        body={"number_nin": normalized_nin},
    )
    if not _is_success(payload):
        raise ValidationError({"ninNumber": extract_prembly_message(payload) or "The NIN could not be verified."})

    data = _payload_data(payload)
    mismatches, _ = validate_nin_payload(
        {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "date_of_birth": date_of_birth,
            "mobile": mobile_number,
            "country_of_birth": country_of_birth,
            "nationality": nationality,
            "state_of_origin": state_of_origin,
            "lga": lga,
        },
        data,
    )
    if mismatches:
        raise ValidationError(mismatches)
    return data


def verify_nin_and_bvn(input_data: dict[str, Any], nin_number: str, bvn_number: str) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_nin = _normalize_digits(nin_number)
    normalized_bvn = _normalize_digits(bvn_number)
    if len(normalized_nin) != 11:
        raise ValidationError({"nin_number": "NIN must contain 11 digits."})
    if len(normalized_bvn) != 11:
        raise ValidationError({"bvn_number": "BVN must contain 11 digits."})

    nin_payload = prembly_lookup(
        verification_type="nin",
        lookup_value=normalized_nin,
        body={"number_nin": normalized_nin},
    )
    nin_data = _payload_data(nin_payload)
    if not _is_success(nin_payload) or not nin_data:
        raise ValidationError({"nin_number": extract_prembly_message(nin_payload) or "The NIN could not be verified."})

    bvn_payload = prembly_lookup(
        verification_type="bvn",
        lookup_value=normalized_bvn,
        body={"number": normalized_bvn},
    )
    bvn_data = _payload_data(bvn_payload)
    if not _is_success(bvn_payload) or not bvn_data:
        raise ValidationError({"bvn_number": extract_prembly_message(bvn_payload) or "The BVN could not be verified."})

    nin_mismatches, _ = validate_nin_payload(input_data, nin_data, defer_phone_mismatch=True)
    bvn_mismatches = validate_bvn_payload(input_data, bvn_data)
    mismatches = _merge_field_mismatches(nin_mismatches, bvn_mismatches)
    if mismatches:
        raise ValidationError(mismatches)
    return nin_payload, bvn_payload


def verify_cac(input_data: dict[str, Any], registration_number: str) -> dict[str, Any]:
    payload = prembly_lookup(
        verification_type="cac",
        lookup_value=registration_number,
        body={"rc_number": str(registration_number).strip()},
    )
    if not _is_success(payload):
        raise ValidationError({"registration_number": extract_prembly_message(payload) or "The CAC record could not be verified."})
    return _payload_data(payload)


def compute_prembly_webhook_signature(raw_body: bytes | str, *, public_key: str | None = None) -> str:
    key = str(public_key if public_key is not None else getattr(settings, "PREMBLY_API_PUBLIC_KEY", "") or "").strip()
    if not key:
        return ""
    body = raw_body if isinstance(raw_body, bytes) else str(raw_body).encode("utf-8")
    digest = hmac.new(key.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_prembly_webhook_signature(raw_body: bytes | str, signature: str, *, public_key: str | None = None) -> bool:
    provided = str(signature or "").removeprefix("sha256=").strip()
    expected = compute_prembly_webhook_signature(raw_body, public_key=public_key)
    return bool(provided and expected) and hmac.compare_digest(provided, expected)
