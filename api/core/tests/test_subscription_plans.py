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
    @patch("core.payments.build_subscription_subaccount_payload")
    def test_tutor_checkout_uses_the_catalog_price(self, build_subaccounts, initialize_payment):
        build_subaccounts.return_value = (
            [{"id": "RS_TEST", "transaction_charge_type": "flat", "transaction_charge": 0}],
            {"subaccount_id": "RS_TEST"},
        )
        initialize_payment.return_value = {
            "status": "success",
            "data": {"id": "123", "link": "https://checkout.example.test/subscription"},
        }
        self.client.force_authenticate(self.tutor)

        response = self.client.post(
            "/api/payments/subscriptions/checkout",
            {"plan": "platinum"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["amount"], Decimal(plan[3]["price"]))
        payment = SubscriptionPayment.objects.get(user=self.tutor)
        self.assertEqual(payment.plan, "platinum")
        self.assertEqual(payment.amount, Decimal(plan[3]["price"]))
        initialize_payment.assert_called_once()

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
