from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import AppUser, StudentVerificationRequest, TutorProfile, VerificationRequest


@override_settings(
    BYPASS_VERIFICATION=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class StudentVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = AppUser.objects.create_user(
            email="student-verification@example.com",
            password="student123",
            role="student",
            display_name="Ada",
            full_name="Ada Byron Lovelace",
            mobile_number="+2348012345678",
            timezone="UTC",
            is_verified=True,
        )
        self.client.force_authenticate(self.student)
        self.payload = {
            "firstName": "Ada",
            "middleName": "Byron",
            "lastName": "Lovelace",
            "email": self.student.email,
            "mobileNumber": "+2348012345678",
            "dateOfBirth": "1990-01-02",
            "countryOfBirth": "Nigeria",
            "nationality": "Nigerian",
            "stateOfOrigin": "Lagos",
            "lgaOfOrigin": "Ikeja",
            "ninNumber": "12345678901",
            "homeState": "Lagos",
            "homeCity": "Ikeja",
            "homeAddress": "1 Verification Street",
            "qualification": "Bachelor's Degree",
            "profilePhotoUrl": "/uploads/images/students/ada.jpg",
            "documentUrls": [
                "/uploads/images/students/ada-id.pdf",
                "/uploads/images/students/ada-qualification.pdf",
            ],
        }

    @patch("core.views.verify_nin_and_bvn")
    @patch("core.views.verify_nin_identity")
    def test_student_can_verify_without_bvn(self, verify_nin, verify_combined):
        payload = {**self.payload, "documentUrls": [self.payload["documentUrls"][0]]}
        payload.pop("qualification")
        response = self.client.post("/api/students/verification", payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "approved")
        verify_nin.assert_called_once()
        verify_combined.assert_not_called()
        verification = StudentVerificationRequest.objects.get(user=self.student)
        self.assertEqual(verification.bvn_number, "")
        self.assertEqual(verification.nin_number, "12345678901")
        self.assertEqual(verification.qualification, "")
        self.assertEqual(verification.document_urls, '["/uploads/images/students/ada-id.pdf"]')

    @patch("core.views.verify_nin_and_bvn")
    @patch("core.views.verify_nin_identity")
    def test_student_bvn_is_queried_and_validated_when_provided(self, verify_nin, verify_combined):
        payload = {**self.payload, "bvnNumber": "10987654321"}

        response = self.client.post("/api/students/verification", payload, format="json")

        self.assertEqual(response.status_code, 200)
        verify_nin.assert_not_called()
        verify_combined.assert_called_once()
        identity_data, nin_number, bvn_number = verify_combined.call_args.args
        self.assertEqual(nin_number, "12345678901")
        self.assertEqual(bvn_number, "10987654321")
        self.assertEqual(identity_data["first_name"], "Ada")
        self.assertEqual(identity_data["last_name"], "Lovelace")
        self.assertEqual(StudentVerificationRequest.objects.get(user=self.student).bvn_number, "10987654321")

    @patch("core.views.verify_nin_and_bvn")
    @patch("core.views.verify_nin_identity")
    def test_student_invalid_optional_bvn_is_rejected_without_provider_call(self, verify_nin, verify_combined):
        payload = {**self.payload, "bvnNumber": "12345"}

        response = self.client.post("/api/students/verification", payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("11 digits", response.json()["detail"])
        verify_nin.assert_not_called()
        verify_combined.assert_not_called()

    @patch("core.views.verify_nin_identity")
    def test_verified_student_completes_profile_and_verified_fields_stay_locked(self, verify_nin):
        verification_payload = {**self.payload}
        verification_payload.pop("profilePhotoUrl")
        response = self.client.post("/api/students/verification", verification_payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profilePhotoUrl"], "")

        missing_photo = self.client.put(
            "/api/me",
            {
                "displayName": "Ada",
                "gender": "female",
                "levelOfEducation": "University (Undergraduate)",
                "completeProfile": True,
            },
            format="json",
        )
        self.assertEqual(missing_photo.status_code, 400)
        self.assertIn("Profile photo", missing_photo.json()["detail"])
        self.student.refresh_from_db()
        self.assertFalse(self.student.student_profile_completed)

        completion = self.client.put(
            "/api/me",
            {
                "displayName": "Ada",
                "gender": "female",
                "levelOfEducation": "University (Undergraduate)",
                "profilePhotoUrl": "/uploads/images/students/ada-profile.jpg",
                "completeProfile": True,
            },
            format="json",
        )
        self.assertEqual(completion.status_code, 200)
        self.assertEqual(completion.json()["gender"], "female")
        self.assertEqual(completion.json()["profilePhotoUrl"], "/uploads/images/students/ada-profile.jpg")
        self.assertEqual(completion.json()["levelOfEducation"], "University (Undergraduate)")
        self.assertTrue(completion.json()["isStudentProfileComplete"])
        self.assertEqual(completion.json()["defaultDashboardPath"], "/search")

        locked_update = self.client.put(
            "/api/me",
            {"displayName": "Ada", "state": "Oyo"},
            format="json",
        )
        self.assertEqual(locked_update.status_code, 403)
        self.assertIn("locked", locked_update.json()["detail"].lower())

        self.student.refresh_from_db()
        verification = StudentVerificationRequest.objects.get(user=self.student)
        self.assertEqual(self.student.gender, "female")
        self.assertTrue(self.student.student_profile_completed)
        self.assertEqual(self.student.state, "Lagos")
        self.assertEqual(verification.qualification, "University (Undergraduate)")

    def test_tutor_bvn_requirement_is_unchanged(self):
        tutor = AppUser.objects.create_user(
            email="required-tutor-bvn@example.com",
            password="tutor123",
            role="tutor",
            display_name="Tutor",
            full_name="Tutor Example",
            mobile_number="+2348012345678",
            timezone="UTC",
            is_verified=True,
        )
        TutorProfile.objects.create(user=tutor, verification_status="not_submitted", hourly_rate_cents=0)
        self.client.force_authenticate(tutor)

        response = self.client.post(
            "/api/tutors/me/verification",
            {
                "homeState": "Lagos",
                "homeCity": "Ikeja",
                "homeAddress": "1 Tutor Street",
                "qualification": "Bachelor's Degree",
                "ninNumber": "12345678901",
                "dateOfBirth": "1990-01-02",
                "profilePhotoUrl": "/uploads/images/tutors/photo.jpg",
                "documentUrls": ["/uploads/images/tutors/id.pdf"],
                "firstName": "Tutor",
                "lastName": "Example",
                "mobileNumber": "+2348012345678",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("bvnNumber", response.json()["detail"])

    @patch("core.views.verify_nin_and_bvn")
    def test_tutor_is_automatically_verified_when_identity_records_match(self, verify_combined):
        tutor = AppUser.objects.create_user(
            email="automatic-tutor@example.com",
            password="tutor123",
            role="tutor",
            display_name="Automatic",
            full_name="Automatic Tutor",
            mobile_number="+2348012345678",
            timezone="UTC",
            is_verified=True,
        )
        profile = TutorProfile.objects.create(user=tutor, verification_status="not_submitted", hourly_rate_cents=0)
        self.client.force_authenticate(tutor)

        response = self.client.post(
            "/api/tutors/me/verification",
            {
                "homeState": "Lagos",
                "homeCity": "Ikeja",
                "homeAddress": "1 Tutor Street",
                "qualification": "Bachelor's Degree",
                "ninNumber": "12345678901",
                "bvnNumber": "10987654321",
                "dateOfBirth": "1990-01-02",
                "documentUrls": [
                    "/uploads/images/tutors/id.pdf",
                    "/uploads/images/tutors/qualification.pdf",
                ],
                "firstName": "Automatic",
                "lastName": "Tutor",
                "mobileNumber": "+2348012345678",
                "countryOfBirth": "Nigeria",
                "nationality": "Nigerian",
                "stateOfOrigin": "Lagos",
                "lgaOfOrigin": "Ikeja",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "approved")
        self.assertEqual(response.json()["profilePhotoUrl"], "")
        verify_combined.assert_called_once()
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, "approved")
        verification = VerificationRequest.objects.get(tutor_profile=profile)
        self.assertEqual(verification.status, "approved")
        self.assertIsNotNone(verification.decided_at)
