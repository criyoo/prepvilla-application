from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from decimal import Decimal
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


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
    version = str(getattr(settings, "FLUTTERWAVE_API_VERSION", "v3") or "v3").strip().lower()
    if version not in {"3", "v3"}:
        raise FlutterwaveError(
            "This checkout flow requires Flutterwave v3 credentials and endpoints."
        )
    return str(
        getattr(settings, "FLUTTERWAVE_V3_API_BASE_URL", "")
        or getattr(settings, "FLUTTERWAVE_API_BASE_URL", "")
        or "https://api.flutterwave.com/v3"
    ).rstrip("/")


def _request(path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    secret_key = str(getattr(settings, "FLUTTERWAVE_SECRET_KEY", "") or "").strip()
    if not secret_key:
        raise FlutterwaveError("Flutterwave secret key is not configured.")
    request = Request(
        f"{_base_url()}/{path.lstrip('/')}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret_key}",
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=int(getattr(settings, "FLUTTERWAVE_TIMEOUT_SECONDS", 20))) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            error_payload = {}
        message = error_payload.get("message") if isinstance(error_payload, dict) else None
        logger.warning("Flutterwave request failed: %s", message or exc)
        raise FlutterwaveError(str(message or "Flutterwave request failed.")) from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Flutterwave request failed: %s", exc)
        raise FlutterwaveError("Flutterwave request failed.") from exc
    if not isinstance(payload, dict):
        raise FlutterwaveError("Flutterwave returned an invalid response.")
    if str(payload.get("status", "")).lower() not in {"success", "successful", "ok", ""}:
        message = payload.get("message") or "Flutterwave rejected the request."
        raise FlutterwaveError(str(message))
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
    body: dict[str, Any] = {
        "tx_ref": tx_ref,
        "amount": float(amount),
        "currency": "NGN",
        "redirect_url": getattr(settings, "FLUTTERWAVE_REDIRECT_URL", ""),
        "customer": {"email": email, "name": name, "phonenumber": phone},
        "meta": meta or {},
    }
    resolved_subaccounts = list(subaccounts or [])
    if subaccount_id and not resolved_subaccounts:
        resolved_subaccounts = [{"id": str(subaccount_id).strip(), "transaction_charge_type": "flat", "transaction_charge": 0}]
    if resolved_subaccounts:
        body["subaccounts"] = resolved_subaccounts
    # Booking checkouts intentionally do not provide subaccounts. The payment
    # therefore remains in Flutterwave's Collection Balance until the payout
    # worker releases it after the lesson confirmations are complete.
    return _request("payments", method="POST", body=body)


def _extract_subaccount_id(payload: dict[str, Any] | None) -> str:
    payload = payload if isinstance(payload, dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    for key in ("subaccount_id", "subAccountId", "account_id", "id"):
        value = str(data.get(key) or "").strip()
        if value and (key != "id" or value.startswith("RS_")):
            return value
    return ""


def create_collection_subaccount(
    *,
    bank_code: str,
    account_number: str,
    business_name: str,
    business_email: str = "",
    business_mobile: str = "",
    country: str = "NG",
    split_type: str = "flat",
    split_value: str | Decimal = "0",
) -> dict[str, Any]:
    try:
        normalized_split_value = Decimal(str(split_value or "0"))
    except (ArithmeticError, ValueError) as exc:
        raise FlutterwaveError("Flutterwave subaccount split value is invalid.") from exc

    body: dict[str, Any] = {
        "account_bank": str(bank_code or "").strip(),
        "account_number": str(account_number or "").strip(),
        "business_name": str(business_name or "").strip(),
        "business_mobile": str(business_mobile or "").strip(),
        "country": str(country or "NG").strip() or "NG",
        "split_type": str(split_type or "flat").strip() or "flat",
        "split_value": float(normalized_split_value),
    }
    missing = [key for key in ("account_bank", "account_number", "business_name", "business_mobile") if not body[key]]
    if missing:
        raise FlutterwaveError(f"Flutterwave subaccount requires: {', '.join(missing)}.")
    if business_email:
        body["business_email"] = str(business_email).strip()
    return _request("subaccounts", method="POST", body=body)


def _collection_subaccounts(account_number: str) -> list[dict[str, Any]]:
    payload = _request(f"subaccounts?account_number={str(account_number).strip()}")
    data = payload.get("data")
    if isinstance(data, dict):
        data = data.get("data") if isinstance(data.get("data"), list) else [data]
    return [item for item in (data or []) if isinstance(item, dict)] if isinstance(data, list) else []


@lru_cache(maxsize=8)
def get_or_create_collection_subaccount_id(
    *,
    bank_code: str,
    account_number: str,
    business_name: str,
    business_email: str = "",
    business_mobile: str = "",
    country: str = "NG",
    split_type: str = "flat",
    split_value: str = "0",
) -> str:
    try:
        payload = create_collection_subaccount(
            bank_code=bank_code,
            account_number=account_number,
            business_name=business_name,
            business_email=business_email,
            business_mobile=business_mobile,
            country=country,
            split_type=split_type,
            split_value=split_value,
        )
        subaccount_id = _extract_subaccount_id(payload)
        if subaccount_id:
            return subaccount_id
    except FlutterwaveError as exc:
        if "already exists" not in str(exc).lower():
            raise

    for subaccount in _collection_subaccounts(account_number):
        candidate_bank = str(subaccount.get("account_bank") or subaccount.get("bank_code") or "").strip()
        candidate_account = str(subaccount.get("account_number") or "").strip()
        if candidate_account == str(account_number).strip() and (not bank_code or not candidate_bank or candidate_bank == str(bank_code).strip()):
            subaccount_id = _extract_subaccount_id(subaccount)
            if subaccount_id:
                return subaccount_id
    raise FlutterwaveError("Flutterwave did not return a subscription subaccount id.")


def verify_transaction(transaction_id: str) -> dict[str, Any]:
    return _request(f"transactions/{str(transaction_id).strip()}/verify")


def verify_transaction_by_reference(tx_ref: str) -> dict[str, Any]:
    return _request(f"transactions/verify_by_reference?{urlencode({'tx_ref': str(tx_ref).strip()})}")


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
        "account_bank": resolved_bank_code,
        "account_number": account_number,
        "amount": float(amount),
        "currency": "NGN",
        "debit_currency": "NGN",
        "reference": reference,
        "beneficiary_name": account_name,
        "narration": narration,
    }
    transfer_pin = str(getattr(settings, "FLUTTERWAVE_TRANSFER_PIN", "") or "").strip()
    if transfer_pin:
        body["debit_currency"] = "NGN"
        body["pin"] = transfer_pin
    return _request("transfers", method="POST", body=body)


def verify_webhook_signature(signature: str, raw_body: bytes | None = None, *, hmac_signature: str = "") -> bool:
    expected = str(getattr(settings, "FLUTTERWAVE_WEBHOOK_SECRET_HASH", "") or "").strip()
    if not expected:
        return not bool(getattr(settings, "FLUTTERWAVE_ENFORCE_WEBHOOK_SIGNATURE", True))
    if hmac_signature and raw_body is not None:
        digest = hmac.new(expected.encode("utf-8"), raw_body, hashlib.sha256).digest()
        calculated = base64.b64encode(digest).decode("ascii")
        return hmac.compare_digest(str(hmac_signature).strip(), calculated)
    return bool(signature) and hmac.compare_digest(str(signature).strip(), expected)
