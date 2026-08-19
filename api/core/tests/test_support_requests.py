from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import AppUser, SupportRequest


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SupportRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = AppUser.objects.create_user(
            email="support-student@example.com",
            password="student123",
            role="student",
            display_name="Support Student",
            full_name="Support Student",
            timezone="UTC",
            is_verified=True,
        )
        self.tutor = AppUser.objects.create_user(
            email="support-tutor@example.com",
            password="tutor123",
            role="tutor",
            display_name="Support Tutor",
            full_name="Support Tutor",
            timezone="UTC",
            is_verified=True,
        )

    def test_student_can_submit_feedback_and_receives_a_ticket_number(self):
        self.client.force_authenticate(self.student)

        response = self.client.post(
            "/api/support/requests",
            {
                "kind": "feedback",
                "topic": "Tutor search",
                "message": "Please add more options for filtering tutor availability.",
                "metadata": {"category": "Tutor discovery"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["ticketNumber"].startswith("PV-"))
        record = SupportRequest.objects.get(user=self.student)
        self.assertEqual(record.kind, SupportRequest.Kind.FEEDBACK)
        self.assertEqual(record.priority, SupportRequest.Priority.NORMAL)
        self.assertEqual(mail.outbox[0].to, ["support@prepvilla.info"])

    def test_tutor_can_submit_an_urgent_issue(self):
        self.client.force_authenticate(self.tutor)

        response = self.client.post(
            "/api/support/requests",
            {
                "kind": "issue",
                "topic": "Tutor payout",
                "message": "My completed lesson payout has remained in processing.",
                "relatedReference": "prepvilla-payout-test",
                "metadata": {"severity": "urgent"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        record = SupportRequest.objects.get(user=self.tutor)
        self.assertEqual(record.priority, SupportRequest.Priority.URGENT)
        self.assertEqual(record.related_reference, "prepvilla-payout-test")

    def test_request_history_is_scoped_to_current_user(self):
        SupportRequest.objects.create(
            user=self.student,
            role="student",
            kind=SupportRequest.Kind.COMPLAINT,
            topic="Booking complaint",
            message="The booking was cancelled without an explanation.",
        )
        SupportRequest.objects.create(
            user=self.tutor,
            role="tutor",
            kind=SupportRequest.Kind.ISSUE,
            topic="Profile issue",
            message="My profile changes are not appearing on the public page.",
        )
        self.client.force_authenticate(self.student)

        response = self.client.get("/api/support/requests")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["kind"], "complaint")

