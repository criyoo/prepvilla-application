from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .flutterwave import (
    FlutterwaveError,
    create_transfer,
    get_or_create_collection_subaccount_id,
    initialize_payment,
    retrieve_transfer,
    verify_transaction,
    verify_transaction_by_reference,
)
from .models import (
    Booking,
    BookingPayment,
    PaymentLedgerEntry,
    PaymentWebhookEvent,
    PlatformFeeTransfer,
    SubscriptionPayment,
    TutorPayout,
)
from .payment_queue import TASK_FLUTTERWAVE_WEBHOOK, TASK_TUTOR_PAYOUT, enqueue_payment_task
from .subscription_plans import SUBSCRIPTION_CURRENCY, get_subscription_plan


MONEY_QUANTUM = Decimal("0.01")


def _response_data(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("data")
    return value if isinstance(value, dict) else {}


def _successful(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status", "")).lower()
    data = _response_data(payload)
    data_status = str(data.get("status", "")).lower()
    return status in {"success", "successful", "succeeded", "ok"} and data_status in {
        "successful", "success", "succeeded", "completed", "paid", ""
    }


def _reference(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _money(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def booking_payment_split(amount: Decimal) -> tuple[Decimal, Decimal]:
    """Return the tutor amount and operational-account fee for a lesson payment."""
    tutor_rate = Decimal(str(getattr(settings, "TUTOR_PAYOUT_PERCENTAGE", 95)))
    admin_rate = Decimal(str(getattr(settings, "PREPVILLA_ADMIN_FEE_PERCENTAGE", 5)))
    if tutor_rate < 0 or admin_rate < 0 or tutor_rate + admin_rate != Decimal("100"):
        raise ValidationError("Tutor payout and PrepVilla fee percentages must total 100%.")

    total = _money(amount)
    admin_amount = _money(total * admin_rate / Decimal("100"))
    return _money(total - admin_amount), admin_amount


def booking_payout_release_conditions_met(booking: Booking) -> bool:
    """The student authorizes release after the paid lesson has ended."""
    return bool(
        booking.status not in {"cancelled", "rejected"}
        and booking.student_completed_at
        and (not booking.ends_at or booking.ends_at <= timezone.now())
    )


def _subscription_amount(user, plan: str) -> Decimal:
    if user.role not in {"student", "tutor"}:
        raise ValidationError({"plan": "The selected subscription plan is not available for this account."})
    selected_plan = get_subscription_plan(plan)
    if selected_plan is None:
        raise ValidationError({"plan": "The selected subscription plan is not available."})
    return _money(selected_plan["price"])


def _json_amount(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def resolve_subscription_payment_account() -> dict[str, str]:
    return {
        "bank_code": str(getattr(settings, "PREPVILLA_OPERATIONAL_BANK_CODE", "") or "").strip(),
        "bank_name": str(getattr(settings, "PREPVILLA_OPERATIONAL_BANK_NAME", "") or "").strip(),
        "account_number": str(getattr(settings, "PREPVILLA_OPERATIONAL_ACCOUNT_NUMBER", "") or "").strip(),
        "account_name": str(getattr(settings, "PREPVILLA_OPERATIONAL_ACCOUNT_NAME", "") or "").strip(),
    }


def subscription_direct_settlement_configured() -> bool:
    if str(getattr(settings, "PREPVILLA_OPERATIONAL_SUBACCOUNT_ID", "") or "").strip():
        return True
    account = resolve_subscription_payment_account()
    return bool(
        account["bank_code"]
        and account["account_number"]
        and account["account_name"]
        and str(getattr(settings, "PREPVILLA_OPERATIONAL_BUSINESS_MOBILE", "") or "").strip()
    )


def build_subscription_subaccount_payload() -> tuple[list[dict[str, Any]], dict[str, str]]:
    account = resolve_subscription_payment_account()
    subaccount_id = str(getattr(settings, "PREPVILLA_OPERATIONAL_SUBACCOUNT_ID", "") or "").strip()
    if not subaccount_id:
        if not subscription_direct_settlement_configured():
            raise FlutterwaveError(
                "PrepVilla operational subscription account is not configured. "
                "Provide the operational bank account and business mobile, or PREPVILLA_OPERATIONAL_SUBACCOUNT_ID."
            )
        subaccount_id = get_or_create_collection_subaccount_id(
            bank_code=account["bank_code"],
            account_number=account["account_number"],
            business_name=account["account_name"],
            business_email=getattr(settings, "PREPVILLA_OPERATIONAL_BUSINESS_EMAIL", ""),
            business_mobile=getattr(settings, "PREPVILLA_OPERATIONAL_BUSINESS_MOBILE", ""),
            country=getattr(settings, "PREPVILLA_OPERATIONAL_SUBACCOUNT_COUNTRY", "NG"),
            split_type=getattr(settings, "PREPVILLA_OPERATIONAL_SUBACCOUNT_SPLIT_TYPE", "flat"),
            split_value=getattr(settings, "PREPVILLA_OPERATIONAL_SUBACCOUNT_SPLIT_VALUE", "0"),
        )
    try:
        transaction_charge = Decimal(
            str(getattr(settings, "PREPVILLA_SUBSCRIPTION_TRANSACTION_CHARGE", "0") or "0")
        )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FlutterwaveError("PrepVilla subscription transaction charge is invalid.") from exc
    transaction_charge_type = str(
        getattr(settings, "PREPVILLA_SUBSCRIPTION_TRANSACTION_CHARGE_TYPE", "flat") or "flat"
    ).strip() or "flat"
    subaccounts = [{
        "id": subaccount_id,
        "transaction_charge_type": transaction_charge_type,
        "transaction_charge": _json_amount(transaction_charge),
    }]
    return subaccounts, {
        **account,
        "subaccount_id": subaccount_id,
        "transaction_charge_type": transaction_charge_type,
        "transaction_charge": str(transaction_charge),
    }


def _checkout_result(payment, provider_payload: dict[str, Any]) -> dict[str, Any]:
    data = _response_data(provider_payload)
    payment.provider_transaction_id = str(data.get("id") or "")
    payment.payment_link = str(data.get("link") or data.get("payment_link") or "")
    payment.provider_payload = provider_payload
    payment.save(update_fields=["provider_transaction_id", "payment_link", "provider_payload", "updated_at"])
    return {
        "id": str(payment.id),
        "transactionId": payment.transaction_id,
        "status": payment.status,
        "paymentLink": payment.payment_link,
        "amount": str(payment.amount),
        "currency": payment.currency,
    }


def _ledger_entry(
    *,
    reference: str,
    entry_type: str,
    status: str,
    amount: Decimal,
    currency: str,
    subscription_payment: SubscriptionPayment | None = None,
    booking_payment: BookingPayment | None = None,
    tutor_payout: TutorPayout | None = None,
    provider_reference: str = "",
    metadata: dict[str, Any] | None = None,
) -> PaymentLedgerEntry:
    entry, _ = PaymentLedgerEntry.objects.update_or_create(
        reference=reference,
        defaults={
            "entry_type": entry_type,
            "status": status,
            "amount": _money(amount),
            "currency": currency,
            "subscription_payment": subscription_payment,
            "booking_payment": booking_payment,
            "tutor_payout": tutor_payout,
            "provider_reference": provider_reference,
            "metadata": metadata or {},
        },
    )
    return entry


def _record_subscription_collection(payment: SubscriptionPayment) -> None:
    _ledger_entry(
        reference=f"subscription:{payment.id}:collection",
        entry_type=PaymentLedgerEntry.EntryType.SUBSCRIPTION_COLLECTION,
        status=PaymentLedgerEntry.Status.COMPLETED,
        amount=payment.amount,
        currency=payment.currency,
        subscription_payment=payment,
        provider_reference=payment.provider_transaction_id or payment.transaction_id,
    )


def _record_booking_allocations(payment: BookingPayment) -> TutorPayout:
    tutor_amount, admin_amount = booking_payment_split(payment.amount)
    held_at = payment.held_at or timezone.now()
    payment.tutor_amount = tutor_amount
    payment.platform_fee_amount = admin_amount
    payment.held_at = held_at
    payment.save(update_fields=["tutor_amount", "platform_fee_amount", "held_at", "updated_at"])

    payout = queue_tutor_payout(payment, enqueue=False)
    _ledger_entry(
        reference=f"booking:{payment.id}:collection",
        entry_type=PaymentLedgerEntry.EntryType.LESSON_COLLECTION,
        status=PaymentLedgerEntry.Status.COMPLETED,
        amount=payment.amount,
        currency=payment.currency,
        booking_payment=payment,
        provider_reference=payment.provider_transaction_id or payment.transaction_id,
    )
    _ledger_entry(
        reference=f"booking:{payment.id}:platform-fee",
        entry_type=PaymentLedgerEntry.EntryType.PLATFORM_FEE,
        status=PaymentLedgerEntry.Status.COMPLETED,
        amount=admin_amount,
        currency=payment.currency,
        booking_payment=payment,
        provider_reference=payment.provider_transaction_id or payment.transaction_id,
        metadata={"retained_in_collection_balance": True},
    )
    _ledger_entry(
        reference=f"booking:{payment.id}:tutor-payable",
        entry_type=PaymentLedgerEntry.EntryType.TUTOR_PAYABLE,
        status=(
            PaymentLedgerEntry.Status.AVAILABLE
            if booking_payout_release_conditions_met(payment.booking)
            else PaymentLedgerEntry.Status.HELD
        ),
        amount=tutor_amount,
        currency=payment.currency,
        booking_payment=payment,
        tutor_payout=payout,
        metadata={"release_requires_student_confirmation": True},
    )
    return payout


def create_subscription_checkout(*, user, plan: str) -> dict[str, Any]:
    amount = _subscription_amount(user, plan)
    normalized_plan = str(plan or "").strip().lower()
    if normalized_plan == "free" and SubscriptionPayment.objects.filter(
        user=user,
        plan="free",
        status=SubscriptionPayment.Status.COMPLETED,
    ).exists():
        raise ValidationError({"plan": "The 14-day free package can only be activated once."})

    payment = SubscriptionPayment.objects.create(
        user=user,
        plan=normalized_plan,
        amount=amount,
        currency=SUBSCRIPTION_CURRENCY,
        transaction_id=_reference("prepvilla-sub"),
    )

    if amount == Decimal("0.00"):
        payment.provider = "none"
        payment.status = SubscriptionPayment.Status.COMPLETED
        payment.paid_at = timezone.now()
        payment.save(update_fields=["provider", "status", "paid_at", "updated_at"])
        _record_subscription_collection(payment)
        return _checkout_result(payment, {})

    subaccounts, destination = build_subscription_subaccount_payload()
    try:
        payload = initialize_payment(
            tx_ref=payment.transaction_id,
            amount=amount,
            email=user.email,
            name=user.full_name or user.display_name,
            phone=user.mobile_number,
            meta={
                "payment_type": "subscription",
                "payment_id": str(payment.id),
                "plan": normalized_plan,
                "subscription_subaccount_id": subaccounts[0]["id"],
            },
            subaccounts=subaccounts,
        )
    except FlutterwaveError:
        payment.status = SubscriptionPayment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        raise
    result = _checkout_result(payment, payload)
    payment.provider_payload = {
        **(payment.provider_payload or {}),
        "subscription_destination": {
            "subaccount_id": destination["subaccount_id"],
            "direct_settlement": True,
        },
    }
    payment.save(update_fields=["provider_payload", "updated_at"])
    return result


def create_booking_checkout(*, user, booking_id: str) -> dict[str, Any]:
    booking = Booking.objects.select_related("student_user", "tutor_profile__user").filter(
        id=booking_id,
        student_user=user,
    ).first()
    if not booking:
        raise ValidationError({"bookingId": "Booking not found."})
    if booking.status in {"cancelled", "rejected"}:
        raise ValidationError({"bookingId": "This booking cannot be paid for."})
    try:
        amount = (Decimal(booking.tutor_profile.hourly_rate_cents) / Decimal("100")).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        amount = Decimal("0.00")
    if amount <= 0:
        raise ValidationError({"amount": "The tutor has not configured a valid lesson rate."})
    payment, _ = BookingPayment.objects.get_or_create(
        booking=booking,
        defaults={
            "student_user": user,
            "tutor_profile": booking.tutor_profile,
            "amount": amount,
            "transaction_id": _reference("prepvilla-booking"),
        },
    )
    if payment.status == BookingPayment.Status.COMPLETED:
        return _checkout_result(payment, payment.provider_payload or {})
    try:
        payload = initialize_payment(
            tx_ref=payment.transaction_id,
            amount=payment.amount,
            email=user.email,
            name=user.full_name or user.display_name,
            phone=user.mobile_number,
            meta={"payment_type": "booking", "payment_id": str(payment.id), "booking_id": str(booking.id)},
        )
    except FlutterwaveError:
        payment.status = BookingPayment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        raise
    return _checkout_result(payment, payload)


@transaction.atomic
def _mark_paid(payment, provider_payload: dict[str, Any], provider_transaction_id: str = "") -> None:
    data = _response_data(provider_payload)
    payment.status = payment.Status.COMPLETED
    payment.provider_payload = provider_payload
    payment.provider_transaction_id = provider_transaction_id or payment.provider_transaction_id
    payment.payment_method = str(data.get("payment_type") or data.get("payment_method") or "")[:40]
    payment.paid_at = payment.paid_at or timezone.now()
    payment.save(update_fields=["status", "provider_payload", "provider_transaction_id", "payment_method", "paid_at", "updated_at"])
    if isinstance(payment, SubscriptionPayment):
        _record_subscription_collection(payment)
    else:
        _record_booking_allocations(payment)


def _find_payment(tx_ref: str):
    return (
        SubscriptionPayment.objects.filter(transaction_id=tx_ref).first()
        or BookingPayment.objects.select_related("booking", "tutor_profile").filter(transaction_id=tx_ref).first()
    )


def _find_payment_by_provider_id(transaction_id: str):
    return (
        SubscriptionPayment.objects.filter(provider_transaction_id=transaction_id).first()
        or BookingPayment.objects.select_related("booking", "tutor_profile").filter(
            provider_transaction_id=transaction_id
        ).first()
    )


def _validate_verified_payment(payment, data: dict[str, Any], resolved_ref: str) -> None:
    if resolved_ref != payment.transaction_id:
        raise ValidationError({"transactionId": "Payment reference does not match."})
    try:
        provider_amount = _money(data.get("amount"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"transactionId": "Payment amount could not be verified."})
    if provider_amount != payment.amount:
        raise ValidationError({"transactionId": "Payment amount does not match."})
    if str(data.get("currency") or "").upper() != payment.currency.upper():
        raise ValidationError({"transactionId": "Payment currency does not match."})


def verify_customer_payment(*, user, transaction_id: str, tx_ref: str = "") -> dict[str, Any]:
    payment = _find_payment(tx_ref) if tx_ref else None
    if payment is not None:
        owner_id = payment.user_id if isinstance(payment, SubscriptionPayment) else payment.student_user_id
        if owner_id != user.id:
            raise ValidationError({"transactionId": "Payment not found."})
    payload = verify_transaction(transaction_id)
    data = _response_data(payload)
    resolved_ref = str(data.get("tx_ref") or data.get("reference") or tx_ref).strip()
    payment = payment or _find_payment(resolved_ref)
    payment = payment or _find_payment_by_provider_id(str(data.get("id") or transaction_id))
    if payment is None:
        raise ValidationError({"transactionId": "Payment not found."})
    if not _successful(payload):
        provider_status = str(data.get("status") or "").lower()
        payment.status = (
            payment.Status.FAILED
            if provider_status in {"failed", "cancelled", "canceled", "reversed"}
            else payment.Status.PENDING
        )
        payment.provider_payload = payload
        payment.save(update_fields=["status", "provider_payload", "updated_at"])
        return {"id": str(payment.id), "transactionId": payment.transaction_id, "status": payment.status}
    _validate_verified_payment(payment, data, resolved_ref)
    _mark_paid(payment, payload, str(data.get("id") or transaction_id))
    if isinstance(payment, BookingPayment):
        payout = queue_tutor_payout(payment, enqueue=booking_payout_release_conditions_met(payment.booking))
        return {"id": str(payment.id), "transactionId": payment.transaction_id, "status": payment.status, "payoutStatus": payout.status}
    return {"id": str(payment.id), "transactionId": payment.transaction_id, "status": payment.status}


def reconcile_pending_customer_payments(*, limit: int = 100) -> dict[str, int]:
    checked = completed = pending = failed = 0
    payments = list(
        SubscriptionPayment.objects.filter(status=SubscriptionPayment.Status.PENDING).order_by("created_at")[:limit]
    )
    remaining = max(limit - len(payments), 0)
    if remaining:
        payments.extend(
            BookingPayment.objects.select_related("booking", "tutor_profile")
            .filter(status=BookingPayment.Status.PENDING)
            .order_by("created_at")[:remaining]
        )
    for payment in payments:
        checked += 1
        try:
            payload = verify_transaction_by_reference(payment.transaction_id)
        except FlutterwaveError as exc:
            if (
                "no transaction was found" in str(exc).lower()
                and payment.created_at <= timezone.now() - timedelta(minutes=30)
            ):
                payment.status = payment.Status.FAILED
                payment.provider_payload = {"reconciliation_error": str(exc)}
                payment.save(update_fields=["status", "provider_payload", "updated_at"])
                failed += 1
            else:
                pending += 1
            continue
        data = _response_data(payload)
        if _successful(payload):
            try:
                _validate_verified_payment(payment, data, str(data.get("tx_ref") or data.get("reference") or ""))
            except ValidationError:
                failed += 1
                continue
            _mark_paid(payment, payload, str(data.get("id") or ""))
            if isinstance(payment, BookingPayment):
                queue_tutor_payout(payment, enqueue=booking_payout_release_conditions_met(payment.booking))
            completed += 1
            continue
        provider_status = str(data.get("status") or "").lower()
        if provider_status in {"failed", "cancelled", "canceled", "reversed"}:
            payment.status = payment.Status.FAILED
            payment.provider_payload = payload
            payment.save(update_fields=["status", "provider_payload", "updated_at"])
            failed += 1
        else:
            pending += 1
    return {"checked": checked, "completed": completed, "pending": pending, "failed": failed}


def backfill_payment_accounting_records() -> dict[str, int]:
    subscriptions = lessons = 0
    for payment in SubscriptionPayment.objects.filter(status=SubscriptionPayment.Status.COMPLETED):
        data = _response_data(payment.provider_payload or {})
        method = str(data.get("payment_type") or data.get("payment_method") or "")[:40]
        if method and payment.payment_method != method:
            payment.payment_method = method
            payment.save(update_fields=["payment_method", "updated_at"])
        _record_subscription_collection(payment)
        subscriptions += 1
    for payment in BookingPayment.objects.select_related("booking", "tutor_profile").filter(
        status=BookingPayment.Status.COMPLETED
    ):
        data = _response_data(payment.provider_payload or {})
        method = str(data.get("payment_type") or data.get("payment_method") or "")[:40]
        if method and payment.payment_method != method:
            payment.payment_method = method
            payment.save(update_fields=["payment_method", "updated_at"])
        _record_booking_allocations(payment)
        lessons += 1
    return {"subscriptions": subscriptions, "lessons": lessons}


@transaction.atomic
def queue_tutor_payout(payment: BookingPayment, *, enqueue: bool = True) -> TutorPayout:
    tutor_amount, admin_amount = booking_payment_split(payment.amount)
    payout, _ = TutorPayout.objects.get_or_create(
        booking_payment=payment,
        defaults={
            "tutor_profile": payment.tutor_profile,
            "amount": tutor_amount,
        },
    )
    if payout.status == TutorPayout.Status.QUEUED and payout.amount != tutor_amount:
        payout.amount = tutor_amount
        payout.error_message = ""
        payout.save(update_fields=["amount", "error_message", "updated_at"])

    fee, _ = PlatformFeeTransfer.objects.get_or_create(
        booking_payment=payment,
        defaults={
            "amount": admin_amount,
            "status": PlatformFeeTransfer.Status.COMPLETED,
            "provider_payload": {"retained_in_collection_balance": True},
        },
    )
    if fee.status != PlatformFeeTransfer.Status.COMPLETED or fee.amount != admin_amount:
        fee.amount = admin_amount
        fee.status = PlatformFeeTransfer.Status.COMPLETED
        fee.error_message = ""
        fee.provider_payload = {"retained_in_collection_balance": True}
        fee.save(update_fields=["amount", "status", "error_message", "provider_payload", "updated_at"])
    payable = PaymentLedgerEntry.objects.filter(
        reference=f"booking:{payment.id}:tutor-payable"
    ).first()
    if payable and booking_payout_release_conditions_met(payment.booking) and payable.status == PaymentLedgerEntry.Status.HELD:
        payable.status = PaymentLedgerEntry.Status.AVAILABLE
        payable.save(update_fields=["status", "updated_at"])
    if enqueue and booking_payout_release_conditions_met(payment.booking) and payout.status == TutorPayout.Status.QUEUED:
        enqueue_payment_task(TASK_TUTOR_PAYOUT, {"payout_id": str(payout.id)})
    return payout


@transaction.atomic
def process_tutor_payout(payout_id: str) -> dict[str, Any]:
    payout = TutorPayout.objects.select_for_update().select_related(
        "tutor_profile",
        "booking_payment",
        "booking_payment__booking",
    ).get(id=payout_id)
    payment = payout.booking_payment
    booking = payment.booking
    if payout.status == TutorPayout.Status.COMPLETED:
        return {"status": payout.status, "transferReference": payout.transfer_reference}
    if payout.status == TutorPayout.Status.PROCESSING and payout.provider_transfer_id:
        return reconcile_tutor_payout(payout)
    if payment.status != BookingPayment.Status.COMPLETED:
        return {"status": payout.status, "error": "The lesson payment is not completed."}
    if not booking_payout_release_conditions_met(booking):
        return {"status": payout.status, "error": "The lesson has not been completed."}

    tutor = payout.tutor_profile
    if tutor.verification_status != "approved":
        return _fail_tutor_payout(payout, "Tutor verification must be approved before payout.")
    if not tutor.bank_code or not tutor.bank_account_number or not tutor.bank_account_name:
        return _fail_tutor_payout(payout, "Tutor payout bank details are not configured.")

    tutor_amount, admin_amount = booking_payment_split(payment.amount)
    if payout.amount != tutor_amount:
        payout.amount = tutor_amount
    fee, _ = PlatformFeeTransfer.objects.get_or_create(
        booking_payment=payment,
        defaults={"amount": admin_amount},
    )
    fee.amount = admin_amount
    fee.status = PlatformFeeTransfer.Status.COMPLETED
    fee.provider_payload = {"retained_in_collection_balance": True}
    fee.error_message = ""
    fee.save(update_fields=["amount", "status", "provider_payload", "error_message", "updated_at"])

    payout.status = TutorPayout.Status.PROCESSING
    payout.error_message = ""
    payout.processed_at = payout.processed_at or timezone.now()
    payout.failed_at = None
    payout.save(update_fields=["status", "amount", "error_message", "processed_at", "failed_at", "updated_at"])
    _update_payout_ledger(payout, PaymentLedgerEntry.Status.PROCESSING)

    try:
        _process_tutor_bank_transfer(payout, tutor, payment)
    except FlutterwaveError as exc:
        return _fail_tutor_payout(payout, str(exc))

    return {
        "status": payout.status,
        "transferReference": payout.transfer_reference,
        "adminFeeStatus": fee.status,
    }


def _operational_account() -> dict[str, str]:
    return {
        "bank_code": str(getattr(settings, "PREPVILLA_OPERATIONAL_BANK_CODE", "") or "").strip(),
        "account_number": str(getattr(settings, "PREPVILLA_OPERATIONAL_ACCOUNT_NUMBER", "") or "").strip(),
        "account_name": str(getattr(settings, "PREPVILLA_OPERATIONAL_ACCOUNT_NAME", "") or "").strip(),
        "bank_name": str(getattr(settings, "PREPVILLA_OPERATIONAL_BANK_NAME", "") or "").strip(),
    }


def _fail_tutor_payout(payout: TutorPayout, message: str) -> dict[str, Any]:
    payout.status = TutorPayout.Status.FAILED
    payout.error_message = message
    payout.failed_at = timezone.now()
    payout.save(update_fields=["status", "error_message", "failed_at", "updated_at"])
    _update_payout_ledger(payout, PaymentLedgerEntry.Status.FAILED, error=message)
    return {"status": payout.status, "error": message}


def _update_payout_ledger(payout: TutorPayout, status: str, *, error: str = "") -> None:
    _ledger_entry(
        reference=f"payout:{payout.id}:transfer",
        entry_type=PaymentLedgerEntry.EntryType.TUTOR_PAYOUT,
        status=status,
        amount=payout.amount,
        currency=payout.currency,
        booking_payment=payout.booking_payment,
        tutor_payout=payout,
        provider_reference=payout.provider_transfer_id or payout.transfer_reference,
        metadata={"error": error} if error else {},
    )


def _process_tutor_bank_transfer(payout: TutorPayout, tutor, payment: BookingPayment) -> None:
    if payout.provider_transfer_id:
        return

    payout.transfer_reference = payout.transfer_reference or _reference("prepvilla-payout")
    payout.save(update_fields=["transfer_reference", "updated_at"])
    payload = create_transfer(
        reference=payout.transfer_reference,
        amount=payout.amount,
        account_bank=tutor.bank_code,
        account_number=tutor.bank_account_number,
        account_name=tutor.bank_account_name,
        narration=f"PrepVilla lesson payout for {payment.booking_id}",
        bank_name=tutor.bank_name,
    )
    data = _response_data(payload)
    payout.provider_transfer_id = str(data.get("id") or payout.transfer_reference)
    payout.provider_payload = payload
    payout.error_message = ""
    provider_status = str(data.get("status") or "").upper()
    if provider_status in {"SUCCESS", "SUCCESSFUL", "COMPLETED"}:
        payout.status = TutorPayout.Status.COMPLETED
        payout.completed_at = timezone.now()
        payment.released_at = payment.released_at or timezone.now()
        payment.save(update_fields=["released_at", "updated_at"])
        PaymentLedgerEntry.objects.filter(
            reference=f"booking:{payment.id}:tutor-payable"
        ).update(status=PaymentLedgerEntry.Status.COMPLETED, updated_at=timezone.now())
    else:
        payout.status = TutorPayout.Status.PROCESSING
    payout.save(update_fields=["provider_transfer_id", "provider_payload", "error_message", "status", "completed_at", "updated_at"])
    _update_payout_ledger(
        payout,
        PaymentLedgerEntry.Status.COMPLETED
        if payout.status == TutorPayout.Status.COMPLETED
        else PaymentLedgerEntry.Status.PROCESSING,
    )


def _apply_tutor_transfer_status(payout: TutorPayout, payload: dict[str, Any]) -> dict[str, Any]:
    data = _response_data(payload)
    status = str(data.get("status") or "").upper()
    payout.provider_payload = payload
    payout.provider_transfer_id = str(data.get("id") or payout.provider_transfer_id)
    if status in {"SUCCESS", "SUCCESSFUL", "COMPLETED"}:
        payout.status = TutorPayout.Status.COMPLETED
        payout.completed_at = payout.completed_at or timezone.now()
        payout.failed_at = None
        payout.error_message = ""
        payout.booking_payment.released_at = payout.booking_payment.released_at or timezone.now()
        payout.booking_payment.save(update_fields=["released_at", "updated_at"])
        PaymentLedgerEntry.objects.filter(
            reference=f"booking:{payout.booking_payment_id}:tutor-payable"
        ).update(status=PaymentLedgerEntry.Status.COMPLETED, updated_at=timezone.now())
        ledger_status = PaymentLedgerEntry.Status.COMPLETED
    elif status in {"FAILED", "CANCELLED", "REVERSED"}:
        payout.status = TutorPayout.Status.FAILED
        payout.failed_at = timezone.now()
        payout.error_message = str(data.get("complete_message") or data.get("message") or "Transfer failed.")
        ledger_status = PaymentLedgerEntry.Status.FAILED
    else:
        payout.status = TutorPayout.Status.PROCESSING
        ledger_status = PaymentLedgerEntry.Status.PROCESSING
    payout.save(
        update_fields=[
            "status",
            "provider_transfer_id",
            "provider_payload",
            "error_message",
            "completed_at",
            "failed_at",
            "updated_at",
        ]
    )
    _update_payout_ledger(payout, ledger_status, error=payout.error_message)
    return {"status": payout.status, "transferReference": payout.transfer_reference}


def reconcile_tutor_payout(payout: TutorPayout) -> dict[str, Any]:
    if not payout.provider_transfer_id:
        return {"status": payout.status, "error": "Transfer has not been submitted."}
    return _apply_tutor_transfer_status(payout, retrieve_transfer(payout.provider_transfer_id))


def reconcile_processing_tutor_payouts() -> dict[str, int]:
    checked = completed = failed = pending = 0
    for payout in TutorPayout.objects.select_related("booking_payment").filter(
        status=TutorPayout.Status.PROCESSING
    ):
        checked += 1
        try:
            result = reconcile_tutor_payout(payout)
        except FlutterwaveError:
            pending += 1
            continue
        if result["status"] == TutorPayout.Status.COMPLETED:
            completed += 1
        elif result["status"] == TutorPayout.Status.FAILED:
            failed += 1
        else:
            pending += 1
    return {"checked": checked, "completed": completed, "failed": failed, "pending": pending}


def process_booking_payout(booking: Booking) -> dict[str, Any]:
    payment = BookingPayment.objects.filter(booking=booking, status=BookingPayment.Status.COMPLETED).first()
    if payment is None:
        return {"status": "not_ready", "booking_id": str(booking.id)}
    payout = queue_tutor_payout(payment, enqueue=False)
    if not booking_payout_release_conditions_met(booking):
        return {"status": payout.status, "booking_id": str(booking.id)}
    result = process_tutor_payout(str(payout.id))
    result["booking_id"] = str(booking.id)
    return result


def process_ready_tutor_payouts(*, now=None) -> dict[str, int]:
    reconcile_processing_tutor_payouts()
    checked = processed = failed = skipped = 0
    for payment in BookingPayment.objects.select_related(
        "booking",
        "tutor_profile",
    ).filter(status=BookingPayment.Status.COMPLETED).order_by("created_at"):
        checked += 1
        if payment.booking.status in {"cancelled", "rejected"}:
            skipped += 1
            continue
        if not booking_payout_release_conditions_met(payment.booking):
            skipped += 1
            continue
        payout = queue_tutor_payout(payment, enqueue=False)
        if payout.status in {TutorPayout.Status.PROCESSING, TutorPayout.Status.COMPLETED, TutorPayout.Status.FAILED}:
            skipped += 1
            continue
        try:
            result = process_tutor_payout(str(payout.id))
        except FlutterwaveError:
            failed += 1
            continue
        if result.get("status") == TutorPayout.Status.COMPLETED:
            processed += 1
        else:
            failed += 1
    return {"checked": checked, "processed": processed, "failed": failed, "skipped": skipped}


def process_due_subscription_renewals(*, now=None) -> dict[str, int]:
    """Return a stable scheduler result until a recurring Flutterwave token is saved.

    PrepVilla subscriptions currently use hosted Flutterwave checkout. A renewal must not
    silently create a new charge without a customer-authorized recurring payment method.
    """
    return {"checked": 0, "renewed": 0, "failed": 0}


def record_flutterwave_webhook(body: dict[str, Any], raw_body: bytes = b"") -> tuple[PaymentWebhookEvent, bool]:
    data = body.get("data") if isinstance(body, dict) else {}
    data = data if isinstance(data, dict) else {}
    canonical = raw_body or json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    event_key = hashlib.sha256(canonical).hexdigest()
    event_type = str(body.get("event") or body.get("type") or "").strip()
    transaction_reference = str(data.get("tx_ref") or data.get("txRef") or data.get("reference") or "").strip()
    transfer_reference = transaction_reference if event_type.lower().startswith("transfer") else ""
    event, created = PaymentWebhookEvent.objects.get_or_create(
        event_key=event_key,
        defaults={
            "provider_event_id": str(body.get("id") or body.get("webhook_id") or "")[:120],
            "event_type": event_type[:80],
            "transaction_reference": transaction_reference[:160],
            "provider_transaction_id": str(data.get("id") or data.get("transaction_id") or "")[:120],
            "transfer_reference": transfer_reference[:160],
            "payload": body,
        },
    )
    return event, created


def _finish_webhook_event(event: PaymentWebhookEvent, status: str, error: str = "") -> None:
    event.status = status
    event.error_message = error
    event.processed_at = timezone.now()
    event.save(update_fields=["status", "error_message", "processed_at", "updated_at"])


def _process_transfer_webhook(data: dict[str, Any]) -> dict[str, Any]:
    reference = str(data.get("reference") or "").strip()
    provider_id = str(data.get("id") or "").strip()
    payout = TutorPayout.objects.select_related("booking_payment").filter(
        transfer_reference=reference
    ).first()
    if payout is None and provider_id:
        payout = TutorPayout.objects.select_related("booking_payment").filter(
            provider_transfer_id=provider_id
        ).first()
    if payout is None:
        return {"status": "ignored", "reason": "unknown_transfer"}
    return _apply_tutor_transfer_status(payout, {"status": "success", "data": data})


@transaction.atomic
def process_flutterwave_webhook(body: dict[str, Any]) -> dict[str, Any]:
    event_id = str(body.get("event_id") or "").strip() if isinstance(body, dict) else ""
    event = PaymentWebhookEvent.objects.select_for_update().filter(id=event_id).first() if event_id else None
    if event is None:
        event, _ = record_flutterwave_webhook(body)
    if event.status == PaymentWebhookEvent.Status.PROCESSED:
        return {"status": "processed", "eventId": str(event.id)}

    event.status = PaymentWebhookEvent.Status.PROCESSING
    event.error_message = ""
    event.save(update_fields=["status", "error_message", "updated_at"])
    payload = event.payload if isinstance(event.payload, dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    event_type = str(payload.get("event") or payload.get("type") or event.event_type or "").lower()
    try:
        if event_type.startswith("transfer"):
            result = _process_transfer_webhook(data)
        else:
            tx_ref = str(data.get("tx_ref") or data.get("txRef") or data.get("reference") or "").strip()
            transaction_id = str(data.get("id") or data.get("transaction_id") or "").strip()
            payment = _find_payment(tx_ref) if tx_ref else None
            payment = payment or (_find_payment_by_provider_id(transaction_id) if transaction_id else None)
            if payment is None or not transaction_id:
                result = {"status": "ignored", "reason": "unknown_payment"}
            else:
                owner = payment.user if isinstance(payment, SubscriptionPayment) else payment.student_user
                result = verify_customer_payment(
                    user=owner,
                    transaction_id=transaction_id,
                    tx_ref=payment.transaction_id,
                )
    except Exception as exc:
        _finish_webhook_event(event, PaymentWebhookEvent.Status.FAILED, str(exc))
        return {"status": "failed", "eventId": str(event.id), "error": str(exc)}

    final_status = (
        PaymentWebhookEvent.Status.IGNORED
        if result.get("status") == "ignored"
        else PaymentWebhookEvent.Status.PROCESSED
    )
    _finish_webhook_event(event, final_status)
    return {**result, "eventId": str(event.id)}
