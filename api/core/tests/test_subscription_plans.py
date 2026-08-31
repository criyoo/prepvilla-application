from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from core.models import AppUser, SubscriptionPayment
from core.subscription_plans import get_subscription_plan_catalog, SUBSCRIPTION_PLANS as plan



class SubscriptionPlanTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = AppUser.objects.create_user(
            email="billing-student@example.com",
            password="student123",
            role="student",
            display_name="Billing Student",
            is_verified=True,
        )
        self.tutor = AppUser.objects.create_user(
            email="billing-tutor@example.com",
            password="tutor123",
            role="tutor",
            display_name="Billing Tutor",
            is_verified=True,
        )

    def test_subscription_catalog_is_the_expected_single_source_of_truth(self):
        response = self.client.get("/api/payments/subscriptions/plans")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), get_subscription_plan_catalog())
        self.assertEqual(
            {plan["code"]: plan["price"] for plan in response.json()["plans"]},
            {"free": plan[0]["price"], "silver": plan[1]["price"], "gold": plan[2]["price"], "platinum": plan[3]["price"]},
        )

    def test_student_can_activate_the_free_package_once(self):
        self.client.force_authenticate(self.student)

        response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "free"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "completed")
        payment = SubscriptionPayment.objects.get(user=self.student)
        self.assertEqual(payment.plan, "free")
        self.assertEqual(payment.amount, Decimal("0.00"))
        self.assertEqual(payment.provider, "none")
        self.assertIsNotNone(payment.paid_at)

        repeated_response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "free"},
            format="json",
        )
        self.assertEqual(repeated_response.status_code, 400)

    @patch("core.payments.initialize_payment")
    def test_tutor_checkout_uses_the_catalog_price(self, initialize_payment):
        initialize_payment.return_value = {
            "status": "success",
            "data": {"id": "cks_123", "checkout_url": "https://checkout.example.test/subscription"},
        }
        self.client.force_authenticate(self.tutor)

        response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "platinum"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        amount = Decimal(response.json()["amount"])
        self.assertEqual(amount, plan[3]["price"])

        payment = SubscriptionPayment.objects.get(user=self.tutor)
        self.assertEqual(payment.plan, "platinum")
        self.assertEqual(Decimal(payment.amount), plan[3]["price"])
        self.assertEqual(payment.payment_link, "https://checkout.example.test/subscription")
        
        initialize_payment.assert_called_once()

    @patch("core.payments.initialize_payment")
    def test_existing_pending_payment_can_be_continued(self, initialize_payment):
        initialize_payment.return_value = {
            "status": "success",
            "data": {"id": "cks_pending", "checkout_url": "https://checkout.example.test/pending"},
        }
        self.client.force_authenticate(self.student)

        first_response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "silver"},
            format="json",
        )
        payment_id = first_response.json()["id"]

        continue_response = self.client.post(
            f"/api/payments/subscriptions/{payment_id}/checkout",
            {},
            format="json",
        )
        repeated_plan_response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "silver"},
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(continue_response.status_code, 200)
        self.assertEqual(repeated_plan_response.status_code, 201)
        self.assertEqual(continue_response.json()["paymentLink"], "https://checkout.example.test/pending")
        self.assertEqual(repeated_plan_response.json()["id"], payment_id)
        self.assertEqual(SubscriptionPayment.objects.filter(user=self.student).count(), 1)
        initialize_payment.assert_called_once()

    @patch("core.payments.initialize_payment")
    def test_pending_payment_must_be_cancelled_before_choosing_another_package(self, initialize_payment):
        initialize_payment.return_value = {
            "status": "success",
            "data": {"id": "cks_pending", "checkout_url": "https://checkout.example.test/pending"},
        }
        self.client.force_authenticate(self.student)
        self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "silver"},
            format="json",
        )

        response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "gold"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(SubscriptionPayment.objects.filter(user=self.student).count(), 1)

    @patch("core.payments.initialize_payment")
    def test_pending_payment_can_be_cancelled_then_retried_or_changed(self, initialize_payment):
        initialize_payment.side_effect = [
            {
                "status": "success",
                "data": {"id": "cks_pending", "checkout_url": "https://checkout.example.test/pending"},
            },
            {
                "status": "success",
                "data": {"id": "cks_changed", "checkout_url": "https://checkout.example.test/changed"},
            },
        ]
        self.client.force_authenticate(self.student)
        checkout_response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "silver"},
            format="json",
        )
        payment_id = checkout_response.json()["id"]

        cancel_response = self.client.post(
            f"/api/payments/subscriptions/{payment_id}/cancel",
            {},
            format="json",
        )
        changed_plan_response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "gold"},
            format="json",
        )

        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.json()["status"], "cancelled")
        cancelled_payment = SubscriptionPayment.objects.get(id=payment_id)
        self.assertEqual(cancelled_payment.payment_link, "")
        self.assertEqual(cancelled_payment.provider_payload["cancellation"]["reason"], "cancelled_by_user")
        self.assertEqual(changed_plan_response.status_code, 201)
        self.assertEqual(changed_plan_response.json()["paymentLink"], "https://checkout.example.test/changed")
        self.assertEqual(SubscriptionPayment.objects.filter(user=self.student).count(), 2)

    def test_user_cannot_continue_or_cancel_another_users_payment(self):
        payment = SubscriptionPayment.objects.create(
            user=self.tutor,
            plan="silver",
            amount=plan[1]["price"],
            transaction_id="another-users-pending-subscription",
        )
        self.client.force_authenticate(self.student)

        continue_response = self.client.post(
            f"/api/payments/subscriptions/{payment.id}/checkout",
            {},
            format="json",
        )
        cancel_response = self.client.post(
            f"/api/payments/subscriptions/{payment.id}/cancel",
            {},
            format="json",
        )

        self.assertEqual(continue_response.status_code, 400)
        self.assertEqual(cancel_response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, SubscriptionPayment.Status.PENDING)

    def test_completed_payment_cannot_be_continued_or_cancelled(self):
        payment = SubscriptionPayment.objects.create(
            user=self.student,
            plan="silver",
            amount=plan[1]["price"],
            transaction_id="completed-subscription-payment",
            status=SubscriptionPayment.Status.COMPLETED,
        )
        self.client.force_authenticate(self.student)

        continue_response = self.client.post(
            f"/api/payments/subscriptions/{payment.id}/checkout",
            {},
            format="json",
        )
        cancel_response = self.client.post(
            f"/api/payments/subscriptions/{payment.id}/cancel",
            {},
            format="json",
        )

        self.assertEqual(continue_response.status_code, 400)
        self.assertEqual(cancel_response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, SubscriptionPayment.Status.COMPLETED)

    def test_subscription_history_is_scoped_to_the_authenticated_user(self):
        SubscriptionPayment.objects.create(
            user=self.student,
            plan="silver",
            amount=plan[1]["price"],
            transaction_id="student-subscription",
            status=SubscriptionPayment.Status.COMPLETED,
        )
        SubscriptionPayment.objects.create(
            user=self.tutor,
            plan="gold",
            amount=plan[2]["price"],
            transaction_id="tutor-subscription",
            status=SubscriptionPayment.Status.COMPLETED,
        )
        self.client.force_authenticate(self.student)

        response = self.client.get("/api/payments/subscriptions")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["plan"], "silver")

    def test_admin_cannot_purchase_student_or_tutor_packages(self):
        admin = AppUser.objects.create_superuser(
            email="billing-admin@example.com",
            password="admin123",
            display_name="Billing Admin",
        )
        self.client.force_authenticate(admin)

        response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "silver"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
