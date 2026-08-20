import re

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import AppUser, StudentVerificationRequest, TutorProfile, VerificationRequest


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ResidentialAddressChangeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _otp_from_latest_email(self) -> str:
        match = re.search(r"\b([A-Z0-9]{6})\b", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_student_address_change_requires_otp_and_syncs_verification(self):
        student = AppUser.objects.create_user(
            email="address-student@example.com",
            password="student123",
            role="student",
            display_name="Address Student",
            timezone="UTC",
            is_verified=True,
        )
        verification = StudentVerificationRequest.objects.create(
            user=student,
            profile_photo_url="/uploads/images/students/address.webp",
            date_of_birth="2000-01-01",
            mobile_number="+2348012345678",
            state="Lagos",
            city="Ikeja",
            address="1 Old Student Road",
            status="approved",
        )
        self.client.force_authenticate(student)

        me_response = self.client.get("/api/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["address"], "1 Old Student Road")

        request_response = self.client.post(
            "/api/me/change-address/request",
            {"newAddress": "25 New Student Avenue, Ikeja"},
            format="json",
        )
        self.assertEqual(request_response.status_code, 200)
        student.refresh_from_db()
        self.assertEqual(student.address, "")

        wrong_response = self.client.post(
            "/api/me/change-address/confirm",
            {"code": "WRONG1"},
            format="json",
        )
        self.assertEqual(wrong_response.status_code, 400)

        confirm_response = self.client.post(
            "/api/me/change-address/confirm",
            {"code": self._otp_from_latest_email()},
            format="json",
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.json()["address"], "25 New Student Avenue, Ikeja")

        student.refresh_from_db()
        verification.refresh_from_db()
        self.assertEqual(student.address, "25 New Student Avenue, Ikeja")
        self.assertEqual(verification.address, "25 New Student Avenue, Ikeja")

    def test_tutor_address_change_requires_otp_and_syncs_profile_records(self):
        tutor = AppUser.objects.create_user(
            email="address-tutor@example.com",
            password="tutor123",
            role="tutor",
            display_name="Address Tutor",
            timezone="UTC",
            is_verified=True,
            address="2 Old Tutor Road",
        )
        profile = TutorProfile.objects.create(
            user=tutor,
            headline="Mathematics tutor",
            bio="Experienced tutor",
            subjects_csv="Mathematics",
            hourly_rate_cents=500000,
            languages_csv="English",
            verification_status="approved",
            is_listed=True,
            home_address="2 Old Tutor Road",
        )
        verification = VerificationRequest.objects.create(
            tutor_profile=profile,
            status="approved",
            home_address="2 Old Tutor Road",
        )
        self.client.force_authenticate(tutor)

        request_response = self.client.post(
            "/api/me/change-address/request",
            {"newAddress": "44 New Tutor Crescent, Abuja"},
            format="json",
        )
        self.assertEqual(request_response.status_code, 200)

        confirm_response = self.client.post(
            "/api/me/change-address/confirm",
            {"code": self._otp_from_latest_email()},
            format="json",
        )
        self.assertEqual(confirm_response.status_code, 200)

        tutor.refresh_from_db()
        profile.refresh_from_db()
        verification.refresh_from_db()
        self.assertEqual(tutor.address, "44 New Tutor Crescent, Abuja")
        self.assertEqual(profile.home_address, "44 New Tutor Crescent, Abuja")
        self.assertEqual(verification.home_address, "44 New Tutor Crescent, Abuja")

    def test_address_cannot_be_changed_through_general_profile_endpoints(self):
        student = AppUser.objects.create_user(
            email="address-bypass-student@example.com",
            password="student123",
            role="student",
            display_name="Address Student",
            timezone="UTC",
            is_verified=True,
            address="1 Existing Road",
        )
        self.client.force_authenticate(student)
        me_response = self.client.put(
            "/api/me",
            {"displayName": "Address Student", "address": "2 Bypass Road"},
            format="json",
        )
        self.assertEqual(me_response.status_code, 400)
        student.refresh_from_db()
        self.assertEqual(student.address, "1 Existing Road")

        tutor = AppUser.objects.create_user(
            email="address-bypass-tutor@example.com",
            password="tutor123",
            role="tutor",
            display_name="Address Tutor",
            timezone="UTC",
            is_verified=True,
            address="3 Existing Road",
        )
        profile = TutorProfile.objects.create(
            user=tutor,
            headline="Tutor",
            bio="Tutor bio",
            subjects_csv="English",
            hourly_rate_cents=500000,
            languages_csv="English",
            verification_status="approved",
            is_listed=True,
            home_address="3 Existing Road",
        )
        self.client.force_authenticate(tutor)
        profile_response = self.client.put(
            "/api/tutors/me/profile",
            {"homeAddress": "4 Bypass Road"},
            format="json",
        )
        self.assertEqual(profile_response.status_code, 400)
        profile.refresh_from_db()
        self.assertEqual(profile.home_address, "3 Existing Road")

    def test_address_request_rejects_invalid_and_unchanged_values(self):
        student = AppUser.objects.create_user(
            email="address-validation@example.com",
            password="student123",
            role="student",
            display_name="Address Validation",
            timezone="UTC",
            is_verified=True,
            address="10 Existing Avenue",
        )
        self.client.force_authenticate(student)

        invalid_response = self.client.post(
            "/api/me/change-address/request",
            {"newAddress": "123"},
            format="json",
        )
        self.assertEqual(invalid_response.status_code, 400)

        unchanged_response = self.client.post(
            "/api/me/change-address/request",
            {"newAddress": "10 Existing Avenue"},
            format="json",
        )
        self.assertEqual(unchanged_response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)
