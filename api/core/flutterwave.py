from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)
_oauth_lock = threading.Lock()
_oauth_access_token = ""
_oauth_expires_at = 0.0


class FlutterwaveError(Exception):
    pass


NIGERIAN_PAYOUT_BANK_CODES_BY_NAME = {
    "accessbank": "044",
    "ecobank": "050",
    "fidelitybank": "070",
    "firstbank": "011",
    "firstbankofnigeria": "011",
    "firstcitymonumentbank": "214",
    "firstcitymonumentbankplc": "214",
    "fcmb": "214",
    "gtbank": "058",
    "guarantytrustbank": "058",
    "opay": "100004",
    "paycom": "100004",
    "opaydigitalservices": "100004",
    "palmpay": "100033",
    "moniepoint": "090405",
    "moniepointmfb": "090405",
    "moniepointmicrofinancebank": "090405",
    "providus": "101",
    "providusbank": "101",
    "providusbankplc": "101",
    "sterlingbank": "232",
    "uba": "033",
    "unitedbankforafrica": "033",
    "wemabank": "035",
    "zenithbank": "057",
}


def normalize_bank_name_key(bank_name: str) -> str:
    return "".join(character for character in str(bank_name or "").lower() if character.isalnum())


def resolve_nigerian_payout_bank_code(bank_name: str, bank_code: str = "") -> str:
    normalized_bank_name = normalize_bank_name_key(bank_name)
    configured_bank_code = str(bank_code or "").strip()
    return NIGERIAN_PAYOUT_BANK_CODES_BY_NAME.get(normalized_bank_name, configured_bank_code)


def _base_url() -> str:
    version = str(getattr(settings, "FLUTTERWAVE_API_VERSION", "v4") or "v4").strip().lower()
    if version not in {"4", "v4"}:
        raise FlutterwaveError("PrepVilla requires Flutterwave v4 credentials and endpoints.")
    base_url = str(
        getattr(settings, "FLUTTERWAVE_API_BASE_URL", "")
        or "https://developersandbox-api.flutterwave.com"
    ).strip().rstrip("/")
    if "/v3" in base_url.lower() or base_url.lower() == "https://api.flutterwave.com":
        raise FlutterwaveError("FLUTTERWAVE_API_BASE_URL must point to a Flutterwave v4 environment.")
    return base_url


def _clear_access_token() -> None:
    global _oauth_access_token, _oauth_expires_at
    with _oauth_lock:
        _oauth_access_token = ""
        _oauth_expires_at = 0.0


def _access_token() -> str:
    global _oauth_access_token, _oauth_expires_at
    now = time.monotonic()
    if _oauth_access_token and now < _oauth_expires_at:
        return _oauth_access_token

    with _oauth_lock:
        now = time.monotonic()
        if _oauth_access_token and now < _oauth_expires_at:
            return _oauth_access_token

        client_id = str(getattr(settings, "FLUTTERWAVE_CLIENT_ID", "") or "").strip()
        client_secret = str(getattr(settings, "FLUTTERWAVE_CLIENT_SECRET", "") or "").strip()
        if not client_id or not client_secret:
            raise FlutterwaveError("Flutterwave v4 client ID and client secret are not configured.")

        token_url = str(
            getattr(settings, "FLUTTERWAVE_TOKEN_URL", "")
            or "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"
        ).strip()
        token_request = Request(
            token_url,
            data=urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            }).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(
                token_request,
                timeout=int(getattr(settings, "FLUTTERWAVE_TIMEOUT_SECONDS", 20)),
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            logger.warning("Flutterwave OAuth request failed: %s", exc)
            raise FlutterwaveError("Flutterwave v4 authentication failed.") from exc
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("Flutterwave OAuth request failed: %s", exc)
            raise FlutterwaveError("Flutterwave v4 authentication failed.") from exc

        access_token = str(payload.get("access_token") or "").strip() if isinstance(payload, dict) else ""
        if not access_token:
            raise FlutterwaveError("Flutterwave v4 authentication returned no access token.")
        try:
            expires_in = max(int(payload.get("expires_in") or 600), 60)
        except (TypeError, ValueError):
            expires_in = 600
        _oauth_access_token = access_token
        _oauth_expires_at = time.monotonic() + max(expires_in - 60, 30)
        return _oauth_access_token


def _error_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "Flutterwave request failed."
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        validation_errors = error.get("validation_errors")
        if isinstance(validation_errors, list):
            details = [
                str(item.get("message") or "").strip()
                for item in validation_errors
                if isinstance(item, dict) and str(item.get("message") or "").strip()
            ]
            if details:
                return f"{message or 'Flutterwave rejected the request'}: {', '.join(details)}"
        if message:
            return str(message)
    return str(payload.get("message") or "Flutterwave request failed.")


def _request(
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Trace-Id": str(uuid.uuid4()),
    }
    if method.upper() in {"POST", "PUT", "PATCH"}:
        headers["X-Idempotency-Key"] = idempotency_key or str(uuid.uuid4())

    payload: Any = None
    for attempt in range(2):
        headers["Authorization"] = f"Bearer {_access_token()}"
        request = Request(
            f"{_base_url()}/{path.lstrip('/')}",
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=int(getattr(settings, "FLUTTERWAVE_TIMEOUT_SECONDS", 20))) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, OSError):
                error_payload = {}
            if exc.code == 401 and attempt == 0:
                _clear_access_token()
                continue
            message = _error_message(error_payload)
            logger.warning("Flutterwave request failed: %s", message)
            raise FlutterwaveError(message) from exc
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("Flutterwave request failed: %s", exc)
            raise FlutterwaveError("Flutterwave request failed.") from exc
    if not isinstance(payload, dict):
        raise FlutterwaveError("Flutterwave returned an invalid response.")
    if str(payload.get("status", "")).lower() not in {"success", "successful", "ok", ""}:
        raise FlutterwaveError(_error_message(payload))
    return payload


def initialize_payment(
    *,
    tx_ref: str,
    amount: Decimal,
    email: str,
    name: str,
    phone: str = "",
    meta: dict[str, Any] | None = None,
    subaccount_id: str = "",
    subaccounts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    customer_id = get_or_create_customer_id(email=email, name=name, phone=phone)
    body: dict[str, Any] = {
        "reference": tx_ref,
        "amount": float(amount),
        "currency": "NGN",
        "redirect_url": getattr(settings, "FLUTTERWAVE_REDIRECT_URL", ""),
        "customer_id": customer_id,
        "max_retry_attempts": 3,
        "session_duration": 30,
    }
    return _request(
        "checkout/sessions",
        method="POST",
        body=body,
        idempotency_key=f"checkout-{tx_ref}",
    )


def _customer_id(payload: dict[str, Any] | None) -> str:
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list):
        data = data[0] if data else None
    return str(data.get("id") or "").strip() if isinstance(data, dict) else ""


def _customer_name(name: str) -> dict[str, str]:
    parts = [part for part in str(name or "").strip().split() if part]
    if not parts:
        return {}
    if len(parts) == 1:
        return {"first": parts[0], "last": parts[0]}
    result = {"first": parts[0], "last": parts[-1]}
    if len(parts) > 2:
        result["middle"] = " ".join(parts[1:-1])
    return result


def _customer_phone(phone: str) -> dict[str, str]:
    digits = "".join(character for character in str(phone or "") if character.isdigit())
    if digits.startswith("234") and len(digits[3:]) == 10:
        return {"country_code": "234", "number": digits[3:]}
    if 7 <= len(digits) <= 10:
        return {"country_code": "234", "number": digits}
    return {}


def get_or_create_customer_id(*, email: str, name: str = "", phone: str = "") -> str:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email:
        raise FlutterwaveError("A customer email is required for Flutterwave checkout.")

    search_payload = _request(
        "customers/search?page=1&size=10",
        method="POST",
        body={"email": normalized_email},
        idempotency_key=f"customer-search-{hashlib.sha256(normalized_email.encode()).hexdigest()[:24]}",
    )
    customer_id = _customer_id(search_payload)
    if customer_id:
        return customer_id

    body: dict[str, Any] = {"email": normalized_email}
    customer_name = _customer_name(name)
    customer_phone = _customer_phone(phone)
    if customer_name:
        body["name"] = customer_name
    if customer_phone:
        body["phone"] = customer_phone
    create_payload = _request(
        "customers",
        method="POST",
        body=body,
        idempotency_key=f"customer-create-{hashlib.sha256(normalized_email.encode()).hexdigest()[:24]}",
    )
    customer_id = _customer_id(create_payload)
    if not customer_id:
        raise FlutterwaveError("Flutterwave did not return a customer ID.")
    return customer_id


def verify_transaction(transaction_id: str) -> dict[str, Any]:
    return _request(f"charges/{str(transaction_id).strip()}")


def retrieve_checkout_session(session_id: str) -> dict[str, Any]:
    return _request(f"checkout/sessions/{str(session_id).strip()}")


def verify_transaction_by_reference(tx_ref: str) -> dict[str, Any]:
    payload = _request(f"charges?{urlencode({'reference': str(tx_ref).strip(), 'page': 1, 'size': 10})}")
    data = payload.get("data")
    if isinstance(data, list):
        matching = next(
            (item for item in data if isinstance(item, dict) and str(item.get("reference") or "") == str(tx_ref).strip()),
            None,
        )
        return {**payload, "data": matching or {}}
    return payload


def retrieve_transfer(transfer_id: str) -> dict[str, Any]:
    return _request(f"transfers/{str(transfer_id).strip()}")


def create_transfer(
    *,
    reference: str,
    amount: Decimal,
    account_bank: str,
    account_number: str,
    account_name: str,
    narration: str,
    bank_name: str = "",
) -> dict[str, Any]:
    resolved_bank_code = resolve_nigerian_payout_bank_code(bank_name, account_bank)
    body = {
        "type": "bank",
        "action": "instant",
        "reference": reference,
        "narration": narration,
        "payment_instruction": {
            "source_currency": "NGN",
            "destination_currency": "NGN",
            "amount": float(amount),
            "recipient": {
                "bank": {
                    "account_number": account_number,
                    "code": resolved_bank_code,
                },
            },
        },
    }
    return _request(
        "direct-transfers",
        method="POST",
        body=body,
        idempotency_key=f"transfer-{reference}",
    )


def verify_webhook_signature(signature: str, raw_body: bytes | None = None, *, hmac_signature: str = "") -> bool:
    expected = str(getattr(settings, "FLUTTERWAVE_WEBHOOK_SECRET_HASH", "") or "").strip()
    if not expected:
        return not bool(getattr(settings, "FLUTTERWAVE_ENFORCE_WEBHOOK_SIGNATURE", True))
    if hmac_signature and raw_body is not None:
        digest = hmac.new(expected.encode("utf-8"), raw_body, hashlib.sha256).digest()
        calculated = base64.b64encode(digest).decode("ascii")
        return hmac.compare_digest(str(hmac_signature).strip(), calculated)
    return bool(signature) and hmac.compare_digest(str(signature).strip(), expected)
