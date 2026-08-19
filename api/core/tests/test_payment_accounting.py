import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    AppUser,
    Booking,
    BookingPayment,
    PaymentLedgerEntry,
    PaymentWebhookEvent,
    PlatformFeeTransfer,
    SubscriptionPayment,
    TutorPayout,
    TutorProfile,
)
from core.payments import process_flutterwave_webhook, process_tutor_payout, verify_customer_payment


@override_settings(
    PAYMENT_QUEUE_BACKEND="sync",
    FLUTTERWAVE_WEBHOOK_SECRET_HASH="payment-webhook-secret",
    FLUTTERWAVE_ENFORCE_WEBHOOK_SIGNATURE=True,
)
class PaymentAccountingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = AppUser.objects.create_user(
            email="payments-student@example.com",
            password="student123",
            role="student",
            display_name="Payments Student",
            timezone="UTC",
            is_verified=True,
        )
        self.tutor_user = AppUser.objects.create_user(
            email="payments-tutor@example.com",
            password="tutor123",
            role="tutor",
            display_name="Payments Tutor",
            timezone="UTC",
            is_verified=True,
        )
        self.tutor = TutorProfile.objects.create(
            user=self.tutor_user,
            headline="Tutor",
            bio="Tutor bio",
            subjects_csv="Mathematics",
            hourly_rate_cents=1000000,
            languages_csv="English",
            verification_status="approved",
            is_listed=True,
            bank_name="Moniepoint MFB",
            bank_code="090405",
            bank_account_number="0123456789",
            bank_account_name="Payments Tutor",
        )

    @patch("core.payments.verify_transaction")
    def test_bank_transfer_webhook_is_persisted_and_records_subscription(self, verify_transaction):
        payment = SubscriptionPayment.objects.create(
            user=self.student,
            plan="silver",
            amount=Decimal("5000.00"),
            transaction_id="prepvilla-sub-bank-transfer",
        )
        verify_transaction.return_value = {
            "status": "success",
            "data": {
                "id": 10101,
                "tx_ref": payment.transaction_id,
                "amount": 5000,
                "currency": "NGN",
                "status": "successful",
                "payment_type": "bank_transfer",
            },
        }
        body = {
            "event": "charge.completed",
            "data": {
                "id": 10101,
                "tx_ref": payment.transaction_id,
                "amount": 5000,
                "currency": "NGN",
                "status": "successful",
                "payment_type": "bank_transfer",
            },
        }

        response = self.client.post(
            "/api/payments/webhook/flutterwave",
            data=json.dumps(body),
            content_type="application/json",
            HTTP_VERIF_HASH="payment-webhook-secret",
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, SubscriptionPayment.Status.COMPLETED)
        self.assertEqual(payment.payment_method, "bank_transfer")
        self.assertTrue(PaymentWebhookEvent.objects.filter(status=PaymentWebhookEvent.Status.PROCESSED).exists())
        self.assertTrue(
            PaymentLedgerEntry.objects.filter(
                subscription_payment=payment,
                entry_type=PaymentLedgerEntry.EntryType.SUBSCRIPTION_COLLECTION,
                status=PaymentLedgerEntry.Status.COMPLETED,
            ).exists()
        )

    @patch("core.payments.verify_transaction")
    def test_lesson_collection_holds_95_percent_and_retains_5_percent(self, verify_transaction):
        booking = Booking.objects.create(
            tutor_profile=self.tutor,
            student_user=self.student,
            status="confirmed",
            starts_at=timezone.now() - timedelta(hours=2),
            ends_at=timezone.now() - timedelta(hours=1),
        )
        payment = BookingPayment.objects.create(
            booking=booking,
            student_user=self.student,
            tutor_profile=self.tutor,
            amount=Decimal("10000.00"),
            transaction_id="prepvilla-booking-bank-transfer",
        )
        verify_transaction.return_value = {
            "status": "success",
            "data": {
                "id": 20202,
                "tx_ref": payment.transaction_id,
                "amount": 10000,
                "currency": "NGN",
                "status": "successful",
                "payment_type": "bank_transfer",
            },
        }

        verify_customer_payment(
            user=self.student,
            transaction_id="20202",
            tx_ref=payment.transaction_id,
        )

        payment.refresh_from_db()
        payout = TutorPayout.objects.get(booking_payment=payment)
        fee = PlatformFeeTransfer.objects.get(booking_payment=payment)
        self.assertEqual(payment.tutor_amount, Decimal("9500.00"))
        self.assertEqual(payment.platform_fee_amount, Decimal("500.00"))
        self.assertEqual(payout.amount, Decimal("9500.00"))
        self.assertEqual(payout.status, TutorPayout.Status.QUEUED)
        self.assertEqual(fee.amount, Decimal("500.00"))
        self.assertEqual(fee.status, PlatformFeeTransfer.Status.COMPLETED)
        self.assertEqual(
            PaymentLedgerEntry.objects.get(reference=f"booking:{payment.id}:tutor-payable").status,
            PaymentLedgerEntry.Status.HELD,
        )

    @patch("core.payments.enqueue_payment_task")
    def test_student_confirmation_alone_authorizes_tutor_payout(self, enqueue_payment_task):
        booking = Booking.objects.create(
            tutor_profile=self.tutor,
            student_user=self.student,
            status="confirmed",
            starts_at=timezone.now() - timedelta(hours=2),
            ends_at=timezone.now() - timedelta(hours=1),
        )
        payment = BookingPayment.objects.create(
            booking=booking,
            student_user=self.student,
            tutor_profile=self.tutor,
            amount=Decimal("10000.00"),
            transaction_id="prepvilla-booking-confirmation",
            status=BookingPayment.Status.COMPLETED,
            paid_at=timezone.now(),
        )
        from core.payments import queue_tutor_payout

        queue_tutor_payout(payment, enqueue=False)
        self.client.force_authenticate(self.student)

        response = self.client.post(f"/api/bookings/{booking.id}/complete", {}, format="json")

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertIsNotNone(booking.student_completed_at)
        self.assertIsNone(booking.tutor_completed_at)
        enqueue_payment_task.assert_called_once()

    @patch("core.payments.create_transfer")
    def test_tutor_transfer_completes_only_after_provider_confirmation(self, create_transfer):
        booking = Booking.objects.create(
            tutor_profile=self.tutor,
            student_user=self.student,
            status="confirmed",
            starts_at=timezone.now() - timedelta(hours=2),
            ends_at=timezone.now() - timedelta(hours=1),
            student_completed_at=timezone.now(),
        )
        payment = BookingPayment.objects.create(
            booking=booking,
            student_user=self.student,
            tutor_profile=self.tutor,
            amount=Decimal("10000.00"),
            tutor_amount=Decimal("9500.00"),
            platform_fee_amount=Decimal("500.00"),
            transaction_id="prepvilla-booking-payout",
            status=BookingPayment.Status.COMPLETED,
            paid_at=timezone.now(),
        )
        from core.payments import queue_tutor_payout

        payout = queue_tutor_payout(payment, enqueue=False)
        create_transfer.return_value = {
            "status": "success",
            "data": {"id": 30303, "status": "NEW"},
        }

        result = process_tutor_payout(str(payout.id))

        payout.refresh_from_db()
        self.assertEqual(result["status"], TutorPayout.Status.PROCESSING)
        self.assertEqual(payout.status, TutorPayout.Status.PROCESSING)
        create_transfer.assert_called_once()

        webhook_result = process_flutterwave_webhook(
            {
                "event": "transfer.completed",
                "data": {
                    "id": 30303,
                    "reference": payout.transfer_reference,
                    "status": "SUCCESSFUL",
                    "amount": 9500,
                    "currency": "NGN",
                },
            }
        )

        payout.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(webhook_result["status"], TutorPayout.Status.COMPLETED)
        self.assertEqual(payout.status, TutorPayout.Status.COMPLETED)
        self.assertIsNotNone(payment.released_at)

