from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.utils.dateparse import parse_date
from rest_framework.exceptions import APIException, ValidationError


class DikriptVerificationUnavailable(APIException):
    status_code = 503
    default_detail = "Dikript verification is temporarily unavailable."
    default_code = "dikript_verification_unavailable"


def is_dikript_configured() -> bool:
    return bool(
        str(getattr(settings, "DIKRIPT_API_BASE_URL", "") or "").strip()
        and str(
            getattr(settings, "DIKRIPT_API_SECRET_KEY", "")
            or getattr(settings, "DIKRIPT_API_PUBLIC_KEY", "")
            or ""
        ).strip()
    )


def _dikript_key() -> str:
    return str(
        getattr(settings, "DIKRIPT_API_SECRET_KEY", "")
        or getattr(settings, "DIKRIPT_API_PUBLIC_KEY", "")
        or ""
    ).strip()


def _decode_response(raw_response: bytes, *, allow_empty: bool = False) -> dict[str, Any]:
    if not raw_response:
        return {} if allow_empty else _raise_unavailable()
    try:
        payload = json.loads(raw_response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DikriptVerificationUnavailable(detail="Dikript returned an invalid response.") from exc
    return payload if isinstance(payload, dict) else {}


def _raise_unavailable():
    raise DikriptVerificationUnavailable()


def extract_dikript_message(payload: dict[str, Any] | None) -> str:
    payload = payload if isinstance(payload, dict) else {}
    return str(payload.get("message") or payload.get("detail") or payload.get("error") or "").strip()


def _payload_successful(payload: dict[str, Any]) -> bool:
    status = payload.get("status")
    response_code = str(payload.get("response_code") or payload.get("code") or "").strip().lower()
    verification_status = str(payload.get("verification_status") or "").strip().lower()
    if response_code and response_code not in {"00", "200", "success", "successful"}:
        return False
    if verification_status and verification_status not in {"verified", "successful", "success"}:
        return False
    return status is True or str(status or "").lower() in {"success", "successful", "verified", "completed"} or response_code in {"00", "200", "success", "successful"}


def dikript_get(path: str, query: dict[str, Any]) -> dict[str, Any]:
    if not is_dikript_configured():
        raise DikriptVerificationUnavailable(detail="Dikript credentials are not configured.")
    base_url = str(settings.DIKRIPT_API_BASE_URL).rstrip("/")
    request = Request(
        f"{base_url}/{str(path).lstrip('/')}?{urlencode(query)}",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": _dikript_key(),
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=int(getattr(settings, "DIKRIPT_TIMEOUT_SECONDS", 10))) as response:
            return _decode_response(response.read())
    except HTTPError as exc:
        payload = _decode_response(exc.read(), allow_empty=True)
        message = extract_dikript_message(payload)
        if exc.code in {400, 404, 422} and payload:
            return payload
        raise DikriptVerificationUnavailable(detail=message or None) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise DikriptVerificationUnavailable() from exc


def dikript_lookup(*, verification_type: str, lookup_value: str, query: dict[str, Any]) -> dict[str, Any]:
    paths = {
        "nin": getattr(settings, "DIKRIPT_NIN_API_URL", "/dikript/verification/api/v1/getnin"),
        "bvn": getattr(settings, "DIKRIPT_BVN_API_URL", "/dikript/verification/api/v1/getbvn"),
        "cac": getattr(settings, "DIKRIPT_CAC_API_URL", "/dikript/verification/api/v1/getcacbasic"),
    }
    try:
        path = paths[verification_type]
    except KeyError as exc:
        raise ValidationError({"verification_type": "Unsupported Dikript verification type."}) from exc

    lookup_hash = hashlib.sha256(str(lookup_value).strip().encode("utf-8")).hexdigest()
    cache_key = f"prepvilla:dikript:{verification_type}:{lookup_hash}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return cached
    payload = dikript_get(str(path), query)
    cache.set(
        cache_key,
        payload,
        timeout=int(getattr(settings, "DIKRIPT_LOOKUP_CACHE_TIMEOUT_SECONDS", 86400)),
    )
    return payload


def _payload_data(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("data", "nin_data", "bvn_data", "verification"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _phone(value: Any) -> str:
    digits = _digits(value)
    if digits.startswith("234"):
        digits = digits[3:]
    if digits.startswith("0"):
        digits = digits[1:]
    return digits


def _date(value: Any):
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    parsed = parse_date(raw[:10])
    if parsed:
        return parsed
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:20], fmt).date()
        except ValueError:
            continue
    return None


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if data.get(key) not in (None, ""):
            return data[key]
    return ""


def _required_match(expected: Any, actual: Any) -> bool:
    return bool(_text(expected)) and _text(expected) == _text(actual)


def _optional_match(expected: Any, actual: Any) -> bool:
    return not _text(expected) or not _text(actual) or _text(expected) == _text(actual)


def _normalize_region(value: Any) -> str:
    return " ".join(re.sub(r"\bSTATE\b", "", _text(value)).split())


def _normalize_nationality(value: Any) -> str:
    normalized = _text(value)
    return "NIGERIA" if normalized == "NIGERIAN" else normalized


def _normalize_country(value: Any) -> str:
    normalized = _text(value)
    return "NIGERIA" if normalized == "NIGERIAN" else normalized


def _normalize_gender(value: Any) -> str:
    return _text(value)[:1]


def _validate_nin_fields(input_data: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    mismatches: dict[str, str] = {}
    first_name = _first_present(data, "firstName", "firstname", "first_name")
    last_name = _first_present(data, "surname", "lastName", "lastname", "last_name")
    middle_name = _first_present(data, "middleName", "middlename", "otherName", "othername", "middle_name")
    birth_date = _first_present(data, "birthDate", "birthdate", "dateOfBirth", "date_of_birth")
    country_of_birth = _first_present(data, "birthCountry", "countryOfBirth", "country_of_birth", "birth_country")

    if not _required_match(input_data.get("first_name"), first_name):
        mismatches["first_name"] = "First name does not match the NIN record."
    if not _required_match(input_data.get("last_name"), last_name):
        mismatches["last_name"] = "Last name does not match the NIN record."
    if not _optional_match(input_data.get("middle_name"), middle_name):
        mismatches["middle_name"] = "Middle name does not match the NIN record."
    if _date(input_data.get("date_of_birth")) != _date(birth_date):
        mismatches["date_of_birth"] = "Date of birth does not match the NIN record."
    if input_data.get("country_of_birth") and country_of_birth and _normalize_country(input_data.get("country_of_birth")) != _normalize_country(country_of_birth):
        mismatches["country_of_birth"] = "Country of birth does not match the NIN record."
    return mismatches


def _validate_bvn_fields(input_data: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    mismatches: dict[str, str] = {}
    first_name = _first_present(data, "firstName", "firstname", "first_name")
    last_name = _first_present(data, "lastName", "surname", "lastname", "last_name")
    middle_name = _first_present(data, "middleName", "middlename", "otherName", "othername", "middle_name")
    birth_date = _first_present(data, "dateOfBirth", "birthDate", "birthdate", "date_of_birth")

    if not _required_match(input_data.get("first_name"), first_name):
        mismatches["first_name"] = "First name does not match the BVN record."
    if not _required_match(input_data.get("last_name"), last_name):
        mismatches["last_name"] = "Last name does not match the BVN record."
    if not _optional_match(input_data.get("middle_name"), middle_name):
        mismatches["middle_name"] = "Middle name does not match the BVN record."
    if _date(input_data.get("date_of_birth")) != _date(birth_date):
        mismatches["date_of_birth"] = "Date of birth does not match the BVN record."

    optional_fields = (
        ("gender", ("gender",), _normalize_gender, "Gender"),
        ("state_of_origin", ("stateOfOrigin", "state_of_origin"), _normalize_region, "State of origin"),
        ("lga", ("lgaOfOrigin", "lga", "lga_of_origin"), _normalize_region, "LGA"),
        ("nationality", ("nationality",), _normalize_nationality, "Nationality"),
    )
    for field, keys, normalizer, label in optional_fields:
        submitted = input_data.get(field)
        actual = _first_present(data, *keys)
        if submitted not in (None, "") and normalizer(submitted) != normalizer(actual):
            mismatches[field] = f"{label} does not match the BVN record."

    submitted_country = input_data.get("country_of_birth")
    actual_country = _first_present(data, "countryOfBirth", "birthCountry", "country_of_birth", "birth_country")
    if submitted_country and actual_country and _normalize_country(submitted_country) != _normalize_country(actual_country):
        mismatches["country_of_birth"] = "Country of birth does not match the BVN record."

    submitted_mobile = input_data.get("mobile")
    actual_mobile = _first_present(data, "phoneNumber1", "phoneNumber", "telephoneNo", "mobile")
    if not _phone(submitted_mobile) or not _phone(actual_mobile) or _phone(submitted_mobile) != _phone(actual_mobile):
        mismatches["mobile"] = "Mobile number does not match the BVN record."
    return mismatches


def _nin_data(payload: dict[str, Any], input_data: dict[str, Any]) -> dict[str, Any]:
    if not _payload_successful(payload):
        raise ValidationError({"ninNumber": extract_dikript_message(payload) or "The NIN could not be verified."})
    data = _payload_data(payload)
    if not data:
        raise ValidationError({"ninNumber": "Dikript returned no NIN record."})

    actual_mobile = _first_present(data, "telephoneNo", "telephoneno", "phoneNumber", "mobile")
    mismatches = _validate_nin_fields(input_data, data)
    if not _phone(input_data.get("mobile_number")):
        mismatches["mobile_number"] = "Contact number is required for NIN verification."
    elif not _phone(input_data.get("mobile_number")) == _phone(actual_mobile):
        mismatches["mobile_number"] = "Mobile number does not match the NIN record."
    if mismatches:
        raise ValidationError(mismatches)
    return data


def verify_nin_identity(*, nin_number: str, first_name: str = "", last_name: str = "", middle_name: str = "", date_of_birth: Any = None, mobile_number: str = "") -> dict[str, Any]:
    normalized_nin = _digits(nin_number)
    if len(normalized_nin) != 11:
        raise ValidationError({"ninNumber": "NIN must contain 11 digits."})
    return _nin_data(
        dikript_lookup(verification_type="nin", lookup_value=normalized_nin, query={"nin": normalized_nin}),
        {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "date_of_birth": date_of_birth,
            "mobile_number": mobile_number,
        },
    )


def validate_nin_payload(
    input_data: dict[str, Any],
    data: dict[str, Any],
    *,
    defer_phone_mismatch: bool = False,
) -> tuple[dict[str, str], bool]:
    mismatches = _validate_nin_fields(input_data, data)
    phone_mismatch = not _phone(input_data.get("mobile")) or not _phone(input_data.get("mobile")) == _phone(
        _first_present(data, "telephoneNo", "telephoneno", "phoneNumber", "mobile")
    )
    if phone_mismatch:
        mismatches["mobile"] = "Mobile number does not match the NIN record."
    return mismatches, phone_mismatch


def validate_bvn_payload(input_data: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    return _validate_bvn_fields(input_data, data)


def _merge_field_mismatches(
    nin_mismatches: dict[str, str],
    bvn_mismatches: dict[str, str],
) -> dict[str, str]:
    result: dict[str, str] = {}
    shared_fields = {"first_name", "last_name", "middle_name", "date_of_birth", "mobile", "country_of_birth"}
    for field in shared_fields:
        if field in nin_mismatches and field in bvn_mismatches:
            result[field] = bvn_mismatches[field]
    for field in {"gender", "state_of_origin", "lga", "nationality"}:
        if field in bvn_mismatches:
            result[field] = bvn_mismatches[field]
    return result


def verify_nin_and_bvn(input_data: dict[str, Any], nin_number: str, bvn_number: str) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_nin = _digits(nin_number)
    normalized_bvn = _digits(bvn_number)
    if len(normalized_nin) != 11:
        raise ValidationError({"nin_number": "NIN must contain 11 digits."})
    if len(normalized_bvn) != 11:
        raise ValidationError({"bvn_number": "BVN must contain 11 digits."})

    nin_payload = dikript_lookup(verification_type="nin", lookup_value=normalized_nin, query={"nin": normalized_nin})
    nin_data = _payload_data(nin_payload)
    if not _payload_successful(nin_payload) or not nin_data:
        raise ValidationError({"nin_number": extract_dikript_message(nin_payload) or "The NIN could not be verified."})

    bvn_payload = dikript_lookup(verification_type="bvn", lookup_value=normalized_bvn, query={"bvn": normalized_bvn})
    bvn_data = _payload_data(bvn_payload)
    if not _payload_successful(bvn_payload) or not bvn_data:
        raise ValidationError({"bvn_number": extract_dikript_message(bvn_payload) or "The BVN could not be verified."})

    nin_mismatches, _ = validate_nin_payload(input_data, nin_data, defer_phone_mismatch=True)
    bvn_mismatches = validate_bvn_payload(input_data, bvn_data)
    mismatches = _merge_field_mismatches(nin_mismatches, bvn_mismatches)
    if mismatches:
        raise ValidationError(mismatches)
    return nin_payload, bvn_payload


def _company_key(value: Any) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    value = re.sub(r"\b(limited|ltd|plc|llc|incorporated|inc)\b", " ", value)
    return " ".join(value.split())


def verify_cac(input_data: dict[str, Any], registration_number: str) -> dict[str, Any]:
    normalized = re.sub(r"[^A-Z0-9]+", "", str(registration_number or "").upper())
    payload = dikript_lookup(verification_type="cac", lookup_value=normalized, query={"regNumber": normalized})
    if not _payload_successful(payload) or not _payload_data(payload):
        raise ValidationError({"registration_number": extract_dikript_message(payload) or "The CAC record could not be verified."})
    data = _payload_data(payload)
    submitted = _company_key(input_data.get("company_name"))
    actual = _company_key(_first_present(data, "companyName", "company_name"))
    if submitted and actual and submitted != actual and submitted not in actual and actual not in submitted and SequenceMatcher(a=submitted, b=actual).ratio() < 0.8:
        raise ValidationError({"company_name": "Company name does not match the CAC record."})
    return payload
