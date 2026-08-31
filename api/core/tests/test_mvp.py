from datetime import date, timedelta
import json
import re
import tempfile
from pathlib import Path

from django.contrib import admin
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from django.conf import settings
from django.core import mail
import hashlib

from core.admin import (
  TutorProfileAdminForm,
  VerificationRequestAdmin,
  VerificationRequestAdminForm,
)
from core.models import AppUser, AvailabilitySlot, Booking, Conversation, Message, PasswordResetToken, PendingSignupChallenge, Review, SeededStudentAccount, SeededTutorAccount, StudentVerificationRequest, TutorProfile, VerificationRequest
from core.seed_demo_data import seed_demo_accounts_students, seed_demo_accounts_tutors


class MvpFlowTests(TestCase):
  def setUp(self):
    self.client = APIClient()

    self.admin = AppUser.objects.create_superuser(
      email="admin@example.com",
      password="admin123",
      display_name="Admin",
      timezone="UTC",
    )

    self.student = AppUser.objects.create_user(
      email="student@example.com",
      password="student123",
      role="student",
      display_name="Student",
      timezone="UTC",
      is_verified=True,
    )
    StudentVerificationRequest.objects.create(
      user=self.student,
      profile_photo_url="/media/images/students/student.jpg",
      date_of_birth="2000-01-01",
      mobile_number="+2348012345678",
      city="Lagos",
      state="Lagos",
      address="1 Student Street, Lagos",
      status="approved",
    )

    self.tutor_user = AppUser.objects.create_user(
      email="tutor@example.com",
      password="tutor123",
      role="tutor",
      display_name="Tutor",
      timezone="UTC",
      is_verified=True,
    )

    self.tutor_profile = TutorProfile.objects.create(
      user=self.tutor_user,
      headline="Math tutoring",
      bio="Experienced teacher",
      subjects_csv="Math,Algebra",
      hourly_rate_cents=5000,
      languages_csv="English",
      verification_status="approved",
      is_listed=True,
    )

    start = timezone.now() + timedelta(days=1)
    AvailabilitySlot.objects.create(tutor_profile=self.tutor_profile, starts_at=start, ends_at=start + timedelta(hours=1))

  def _login(self, email: str, password: str):
    res = self.client.post("/api/auth/login", {"email": email, "password": password}, format="json")
    self.assertEqual(res.status_code, 200)
    token = res.json()["accessToken"]
    self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

  def test_health_endpoint(self):
    """Test health endpoint with and without trailing slash"""
    res = self.client.get("/api/health/")
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["ok"], True)
    
    res2 = self.client.get("/api/health")
    self.assertEqual(res2.status_code, 200)

  def test_jwt_signing_key_meets_hs256_minimum_length(self):
    signing_key = settings.SIMPLE_JWT["SIGNING_KEY"]
    key_bytes = signing_key if isinstance(signing_key, bytes) else str(signing_key).encode("utf-8")
    self.assertGreaterEqual(len(key_bytes), 32)

  def test_signup_validates_password_length(self):
    """Test that signup rejects short passwords"""
    res = self.client.post(
      "/api/auth/signup",
      {
        "email": "newuser@example.com",
        "password": "123",  # Too short
        "role": "student",
        "displayName": "New User",
        "fullName": "New User",
        "timezone": "UTC",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 400)
    self.assertIn("Password", res.json()["detail"])

  def test_signup_validates_role(self):
    """Test that signup validates role"""
    res = self.client.post(
      "/api/auth/signup",
      {
        "email": "newuser@example.com",
        "password": "password123",
        "role": "invalid_role",
        "displayName": "New User",
        "fullName": "New User",
        "timezone": "UTC",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 400)
    self.assertIn("Role", res.json()["detail"])

  def test_tutor_signup_requires_full_name(self):
    res = self.client.post(
      "/api/auth/signup",
      {
        "email": "newtutor@example.com",
        "password": "password123",
        "role": "tutor",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 400)
    self.assertIn("Full name", res.json()["detail"])

  def test_signup_creates_pending_challenge_before_account(self):
    res = self.client.post(
      "/api/auth/signup",
      {
        "email": "pendingstudent@example.com",
        "password": "password123",
        "role": "student",
        "fullName": "Pending Student",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertFalse(AppUser.objects.filter(email="pendingstudent@example.com").exists())
    self.assertTrue(
      PendingSignupChallenge.objects.filter(email="pendingstudent@example.com", used_at__isnull=True).exists()
    )

  def test_student_signup_accepts_split_name_fields(self):
    res = self.client.post(
      "/api/auth/signup",
      {
        "email": "splitstudent@example.com",
        "password": "password123",
        "role": "student",
        "firstName": "Grace",
        "middleName": "Brewster Murray",
        "lastName": "Hopper",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    challenge = PendingSignupChallenge.objects.get(
      email="splitstudent@example.com",
      used_at__isnull=True,
    )
    self.assertEqual(challenge.full_name, "Grace Brewster Murray Hopper")

  def test_signup_accepts_trailing_slash(self):
    res = self.client.post(
      "/api/auth/signup/",
      {
        "email": "trailingslash@example.com",
        "password": "password123",
        "role": "tutor",
        "fullName": "Trailing Slash",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["pendingEmail"], "trailingslash@example.com")
    self.assertTrue(
      PendingSignupChallenge.objects.filter(email="trailingslash@example.com", used_at__isnull=True).exists()
    )

  def test_verify_otp_creates_tutor_account_after_pending_signup(self):
    signup_res = self.client.post(
      "/api/auth/signup",
      {
        "email": "pendingtutor@example.com",
        "password": "password123",
        "role": "tutor",
        "fullName": "Pending Tutor",
      },
      format="json",
    )
    self.assertEqual(signup_res.status_code, 200)
    self.assertFalse(AppUser.objects.filter(email="pendingtutor@example.com").exists())

    otp_email = mail.outbox[-1]
    self.assertEqual(otp_email.subject, "Your PrepVilla verification code")
    self.assertIn("Return to PrepVilla", otp_email.body)
    self.assertEqual(len(otp_email.alternatives), 1)
    self.assertEqual(otp_email.alternatives[0].mimetype, "text/html")
    self.assertIn("Complete your PrepVilla registration", otp_email.alternatives[0].content)

    otp_match = re.search(r"\b([A-Z0-9]{6})\b", otp_email.body)
    self.assertIsNotNone(otp_match)
    otp_code = otp_match.group(1)
    self.assertIn(otp_code, otp_email.alternatives[0].content)

    verify_res = self.client.post(
      "/api/auth/verify-otp",
      {"email": "pendingtutor@example.com", "otp": otp_code},
      format="json",
    )
    self.assertEqual(verify_res.status_code, 200)

    created_user = AppUser.objects.get(email="pendingtutor@example.com")
    self.assertTrue(created_user.is_verified)
    self.assertEqual(created_user.role, "tutor")
    self.assertTrue(TutorProfile.objects.filter(user=created_user).exists())

  def test_tutor_signup_returns_split_name_details_after_otp(self):
    signup_res = self.client.post(
      "/api/auth/signup",
      {
        "email": "splitname@example.com",
        "password": "password123",
        "role": "tutor",
        "firstName": "Ada",
        "middleName": "Byron",
        "lastName": "Lovelace",
        "fullName": "Ada Byron Lovelace",
      },
      format="json",
    )
    self.assertEqual(signup_res.status_code, 200)
    otp_code = re.search(r"\b([A-Z0-9]{6})\b", mail.outbox[-1].body).group(1)

    verify_res = self.client.post(
      "/api/auth/verify-otp",
      {"email": "splitname@example.com", "otp": otp_code},
      format="json",
    )
    self.assertEqual(verify_res.status_code, 200)
    self.assertEqual(verify_res.json()["user"]["firstName"], "Ada")
    self.assertEqual(verify_res.json()["user"]["middleName"], "Byron")
    self.assertEqual(verify_res.json()["user"]["lastName"], "Lovelace")
    self.assertEqual(verify_res.json()["user"]["email"], "splitname@example.com")

  def test_verify_otp_rejects_verified_account_without_active_code(self):
    res = self.client.post(
      "/api/auth/verify-otp",
      {"email": "student@example.com", "otp": "ABC123"},
      format="json",
    )
    self.assertEqual(res.status_code, 400)

  def test_login_rejects_invalid_credentials(self):
    """Test login with invalid credentials"""
    res = self.client.post(
      "/api/auth/login",
      {"email": "nonexistent@example.com", "password": "password123"},
      format="json",
    )
    self.assertEqual(res.status_code, 401)

  def test_student_login_redirects_to_profile(self):
    res = self.client.post(
      "/api/auth/login",
      {"email": "student@example.com", "password": "student123"},
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["defaultDashboardPath"], "/dashboard/profile")

  def test_unverified_student_login_redirects_to_student_verification(self):
    student = AppUser.objects.create_user(
      email="needs-verification@example.com",
      password="student123",
      role="student",
      display_name="New Student",
      timezone="UTC",
      is_verified=True,
    )

    res = self.client.post(
      "/api/auth/login",
      {"email": student.email, "password": "student123"},
      format="json",
    )

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["defaultDashboardPath"], "/dashboard/student-verification")

  def test_completed_student_login_redirects_to_find_a_tutor(self):
    self.student.gender = "female"
    self.student.save(update_fields=["gender"])

    res = self.client.post(
      "/api/auth/login",
      {"email": self.student.email, "password": "student123"},
      format="json",
    )

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["defaultDashboardPath"], "/search")

  def test_unapproved_tutor_login_redirects_to_verification(self):
    pending_tutor = AppUser.objects.create_user(
      email="pendingtutor@example.com",
      password="pending123",
      role="tutor",
      display_name="Pending Tutor",
      timezone="UTC",
      is_verified=True,
    )
    TutorProfile.objects.create(
      user=pending_tutor,
      headline="",
      bio="",
      subjects_csv="",
      hourly_rate_cents=0,
      languages_csv="",
      verification_status="not_submitted",
      is_listed=False,
    )

    res = self.client.post(
      "/api/auth/login",
      {"email": "pendingtutor@example.com", "password": "pending123"},
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["defaultDashboardPath"], "/dashboard/verification")

  def test_approved_tutor_login_redirects_to_profile(self):
    res = self.client.post(
      "/api/auth/login",
      {"email": "tutor@example.com", "password": "tutor123"},
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["defaultDashboardPath"], "/dashboard/profile")

  def test_refresh_auth_token_issues_new_access_token(self):
    login_res = self.client.post(
      "/api/auth/login",
      {"email": "student@example.com", "password": "student123"},
      format="json",
    )
    self.assertEqual(login_res.status_code, 200)
    refresh_token = login_res.json()["refreshToken"]

    refresh_res = self.client.post(
      "/api/auth/refresh",
      {"refreshToken": refresh_token},
      format="json",
    )
    self.assertEqual(refresh_res.status_code, 200)
    self.assertIn("accessToken", refresh_res.json())
    self.assertEqual(refresh_res.json()["refreshToken"], refresh_token)

    self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_res.json()['accessToken']}")
    me_res = self.client.get("/api/me")
    self.assertEqual(me_res.status_code, 200)
    self.assertEqual(me_res.json()["email"], "student@example.com")

  def test_tutor_profile_admin_form_matches_profile_page_fields(self):
    unsubmitted_profile = TutorProfile.objects.create(
      user=AppUser.objects.create_user(
        email="admin-form@example.com",
        password="form123",
        role="tutor",
        display_name="Admin Form Tutor",
        timezone="UTC",
        is_verified=True,
      ),
      headline="Pending tutor",
      bio="Pending verification",
      subjects_csv="Mathematics",
      hourly_rate_cents=5000,
      languages_csv="English",
      verification_status="not_submitted",
      is_listed=False,
    )

    form = TutorProfileAdminForm(instance=unsubmitted_profile)

    self.assertIn("display_name", form.fields)
    self.assertIn("mobile_number", form.fields)
    self.assertIn("date_of_birth", form.fields)
    self.assertNotIn("verification_status", form.fields)

  def test_verification_request_admin_form_does_not_allow_manual_status_changes(self):
    unsubmitted_profile = TutorProfile.objects.create(
      user=AppUser.objects.create_user(
        email="verification-form@example.com",
        password="form123",
        role="tutor",
        display_name="Verification Form Tutor",
        timezone="UTC",
        is_verified=True,
      ),
      headline="Pending tutor",
      bio="Pending verification",
      subjects_csv="Mathematics",
      hourly_rate_cents=5000,
      languages_csv="English",
      verification_status="not_submitted",
      is_listed=False,
    )
    verification = VerificationRequest.objects.create(
      tutor_profile=unsubmitted_profile,
      status="pending",
    )

    form = VerificationRequestAdminForm(instance=verification)

    self.assertNotIn("status", form.fields)

  def test_verification_request_admin_form_accepts_relative_profile_photo_path(self):
    unsubmitted_profile = TutorProfile.objects.create(
      user=AppUser.objects.create_user(
        email="relative-photo@example.com",
        password="form123",
        role="tutor",
        display_name="Relative Photo Tutor",
        timezone="UTC",
        is_verified=True,
      ),
      headline="Pending tutor",
      bio="Pending verification",
      subjects_csv="Mathematics",
      hourly_rate_cents=5000,
      languages_csv="English",
      verification_status="pending",
      is_listed=False,
    )
    verification = VerificationRequest.objects.create(
      tutor_profile=unsubmitted_profile,
      status="approved",
      profile_photo_url="/uploads/images/tutors/photo.webp",
    )

    form = VerificationRequestAdminForm(
      data={
        "tutor_profile": str(unsubmitted_profile.id),
        "home_state": "",
        "home_city": "",
        "home_address": "",
        "qualification": "",
        "nin_number": "",
        "profile_photo_url": "/uploads/images/tutors/photo.webp",
        "document_urls": "",
        "notes": "",
        "full_name": "",
        "mobile_number": "",
        "date_of_birth": "",
      },
      instance=verification,
    )

    self.assertTrue(form.is_valid(), form.errors)

  def test_verification_request_admin_change_list_shows_email_and_request(self):
    verification_admin = VerificationRequestAdmin(VerificationRequest, admin.site)
    self.assertEqual(verification_admin.list_display[:2], ("user_email", "verification_request"))

  def test_verification_request_admin_save_model_updates_tutor_profile(self):
    request_factory = RequestFactory()
    review_request = request_factory.post("/admin/core/verificationrequest/")
    review_request.user = self.admin
    pending_tutor = AppUser.objects.create_user(
      email="review-admin@example.com",
      password="review123",
      role="tutor",
      display_name="Review Tutor",
      full_name="Review Tutor",
      timezone="UTC",
      is_verified=True,
      mobile_number="+2348012345678",
    )
    pending_profile = TutorProfile.objects.create(
      user=pending_tutor,
      headline="",
      bio="",
      subjects_csv="",
      hourly_rate_cents=0,
      languages_csv="",
      verification_status="approved",
      is_listed=False,
    )
    verification = VerificationRequest.objects.create(
      tutor_profile=pending_profile,
      status="approved",
      decided_at=timezone.now(),
      home_state="Lagos",
      home_city="Lagos",
      home_address="22 Review Road",
      qualification="B.Ed",
      nin_number="12345678901",
      profile_photo_url="/media/images/tutors/review.jpg",
      document_urls='["/media/documents/tutors/id.pdf"]',
    )

    class DummyForm:
      cleaned_data = {
        "full_name": "Review Tutor Updated",
        "mobile_number": "+2348099999999",
        "date_of_birth": date(1991, 5, 1),
      }

    verification_admin = VerificationRequestAdmin(VerificationRequest, admin.site)
    verification_admin.save_model(review_request, verification, DummyForm(), change=True)

    verification.refresh_from_db()
    pending_profile.refresh_from_db()
    pending_tutor.refresh_from_db()
    self.assertEqual(verification.status, "approved")
    self.assertIsNotNone(verification.decided_at)
    self.assertEqual(pending_profile.verification_status, "approved")
    self.assertFalse(pending_profile.is_listed)
    self.assertEqual(pending_profile.qualification, "B.Ed")
    self.assertEqual(pending_profile.nin_number, "12345678901")
    self.assertEqual(pending_profile.profile_photo_url, "/media/images/tutors/review.jpg")
    self.assertEqual(pending_profile.home_state, "Lagos")
    self.assertEqual(pending_profile.home_city, "Lagos")
    self.assertEqual(pending_profile.home_address, "22 Review Road")
    self.assertEqual(pending_tutor.full_name, "Review Tutor Updated")
    self.assertEqual(pending_tutor.display_name, "Review")
    self.assertEqual(pending_tutor.mobile_number, "+2348099999999")
    self.assertEqual(pending_tutor.date_of_birth, date(1991, 5, 1))
    self.assertEqual(pending_tutor.state, "Lagos")
    self.assertEqual(pending_tutor.location, "Lagos")
    self.assertEqual(pending_tutor.address, "22 Review Road")
    self.assertEqual(pending_tutor.profile_photo_url, "/media/images/tutors/review.jpg")

  @override_settings(BYPASS_VERIFICATION=True)
  def test_tutor_verification_submission_is_automatically_verified(self):
    pending_tutor = AppUser.objects.create_user(
      email="verifyme@example.com",
      password="verify123",
      role="tutor",
      display_name="Verify Me",
      full_name="Verify Me",
      timezone="UTC",
      is_verified=True,
      mobile_number="+2348011111111",
    )
    TutorProfile.objects.create(
      user=pending_tutor,
      headline="Starter tutor",
      bio="Ready to teach",
      subjects_csv="Mathematics",
      hourly_rate_cents=500000,
      languages_csv="English",
      verification_status="not_submitted",
      is_listed=False,
    )

    self._login("verifyme@example.com", "verify123")
    res = self.client.post(
      "/api/tutors/me/verification",
      {
        "qualification": "B.Ed",
        "ninNumber": "12345678901",
        "bvnNumber": "10987654321",
        "dateOfBirth": "1990-01-01",
        "profilePhotoUrl": "/media/images/tutors/photo.jpg",
        "documentUrls": ["/media/documents/tutors/id.pdf", "/media/documents/tutors/qualification.pdf"],
        "notes": "Please review",
        "fullName": "Verify Me",
        "displayName": "Verify",
        "mobileNumber": "+2348011111111",
        "homeCity": "Lagos",
        "homeState": "Lagos",
        "homeAddress": "22 Tutor Street",
        "stateOfOrigin": "Lagos",
        "lgaOfOrigin": "Ikeja",
        "countryOfBirth": "Nigeria",
        "nationality": "Nigerian",
        "subjects": ["Mathematics"],
        "languages": ["English"],
        "headline": "Experienced maths tutor",
        "bio": "Detailed coaching",
        "hourlyRate": 5000,
        "offersFaceToFace": True,
        "offersWebcam": True,
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["status"], "approved")

    pending_profile = TutorProfile.objects.get(user=pending_tutor)
    self.assertEqual(pending_profile.verification_status, "approved")
    self.assertFalse(pending_profile.is_listed)
    self.assertEqual(pending_profile.home_state, "Lagos")
    self.assertEqual(pending_profile.home_city, "Lagos")
    self.assertEqual(pending_profile.home_address, "22 Tutor Street")
    self.assertEqual(pending_profile.state_of_origin, "Lagos")
    self.assertEqual(pending_profile.lga_of_origin, "Ikeja")
    self.assertEqual(pending_profile.country_of_birth, "Nigeria")
    self.assertEqual(pending_profile.nationality, "Nigerian")
    self.assertEqual(pending_profile.languages_csv, "English")
    self.assertTrue(pending_profile.offers_face_to_face)
    self.assertFalse(pending_profile.offers_webcam)

  @override_settings(BYPASS_VERIFICATION=True)
  def test_tutor_verification_allows_residence_to_be_completed_on_profile(self):
    pending_tutor = AppUser.objects.create_user(
      email="residence-on-profile@example.com",
      password="verify123",
      role="tutor",
      display_name="Residence Tutor",
      full_name="Residence Tutor",
      timezone="UTC",
      is_verified=True,
      mobile_number="+2348011111111",
    )
    profile = TutorProfile.objects.create(
      user=pending_tutor,
      headline="",
      bio="",
      subjects_csv="",
      hourly_rate_cents=0,
      languages_csv="",
      verification_status="not_submitted",
      is_listed=False,
    )
    self.client.force_authenticate(user=pending_tutor)

    response = self.client.post(
      "/api/tutors/me/verification",
      {
        "qualification": "B.Ed",
        "ninNumber": "12345678901",
        "bvnNumber": "10987654321",
        "dateOfBirth": "1990-01-01",
        "profilePhotoUrl": "/media/images/tutors/photo.jpg",
        "documentUrls": [
          "/media/documents/tutors/id.pdf",
          "/media/documents/tutors/qualification.pdf",
        ],
        "firstName": "Residence",
        "lastName": "Tutor",
        "mobileNumber": "+2348011111111",
        "countryOfBirth": "Nigeria",
        "nationality": "Nigerian",
        "stateOfOrigin": "Lagos",
        "lgaOfOrigin": "Ikeja",
      },
      format="json",
    )

    self.assertEqual(response.status_code, 200)
    profile.refresh_from_db()
    self.assertEqual(profile.verification_status, "approved")
    self.assertEqual(profile.home_state, "")
    self.assertEqual(profile.home_city, "")
    self.assertEqual(profile.home_address, "")

  def test_tutor_verification_rejects_invalid_mobile_number(self):
    pending_tutor = AppUser.objects.create_user(
      email="badmobile@example.com",
      password="verify123",
      role="tutor",
      display_name="Bad Mobile",
      full_name="Bad Mobile",
      timezone="UTC",
      is_verified=True,
    )
    TutorProfile.objects.create(
      user=pending_tutor,
      headline="",
      bio="",
      subjects_csv="",
      hourly_rate_cents=0,
      languages_csv="",
      verification_status="not_submitted",
      is_listed=False,
    )

    self.client.force_authenticate(user=pending_tutor)
    res = self.client.post(
      "/api/tutors/me/verification",
      {
        "homeState": "Lagos",
        "homeCity": "Lagos",
        "homeAddress": "22 Tutor Street",
        "qualification": "B.Ed",
        "ninNumber": "12345678901",
        "bvnNumber": "10987654321",
        "dateOfBirth": "1990-01-01",
        "profilePhotoUrl": "/media/images/tutors/photo.jpg",
        "documentUrls": ["/media/documents/tutors/id.pdf", "/media/documents/tutors/qualification.pdf"],
        "notes": "Please review",
        "fullName": "Bad Mobile",
        "mobileNumber": "08012345678",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 400)
    self.assertIn("+234", res.json()["detail"])

  def test_tutor_verification_rejects_invalid_nin_number(self):
    pending_tutor = AppUser.objects.create_user(
      email="badnin@example.com",
      password="verify123",
      role="tutor",
      display_name="Bad Nin",
      full_name="Bad Nin",
      timezone="UTC",
      is_verified=True,
    )
    TutorProfile.objects.create(
      user=pending_tutor,
      headline="",
      bio="",
      subjects_csv="",
      hourly_rate_cents=0,
      languages_csv="",
      verification_status="not_submitted",
      is_listed=False,
    )

    self.client.force_authenticate(user=pending_tutor)
    res = self.client.post(
      "/api/tutors/me/verification",
      {
        "homeState": "Lagos",
        "homeCity": "Lagos",
        "homeAddress": "22 Tutor Street",
        "qualification": "B.Ed",
        "ninNumber": "12345A7890",
        "bvnNumber": "10987654321",
        "dateOfBirth": "1990-01-01",
        "profilePhotoUrl": "/media/images/tutors/photo.jpg",
        "documentUrls": ["/media/documents/tutors/id.pdf", "/media/documents/tutors/qualification.pdf"],
        "notes": "Please review",
        "fullName": "Bad Nin",
        "mobileNumber": "+2348011111111",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 400)
    self.assertIn("11 digits", res.json()["detail"])

  def test_student_verification_rejects_invalid_mobile_number(self):
    self.client.force_authenticate(user=self.student)
    res = self.client.post(
      "/api/students/verification",
      {
        "profilePhotoUrl": "/media/images/students/student.jpg",
        "dateOfBirth": "2000-01-01",
        "mobileNumber": "+1234567890",
        "city": "Lagos",
        "state": "Lagos",
        "address": "1 Student Street, Lagos",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 400)
    self.assertIn("+234", res.json()["detail"])

  def test_change_phone_request_rejects_invalid_mobile_number(self):
    self.client.force_authenticate(user=self.student)
    res = self.client.post(
      "/api/me/change-phone/request",
      {"newPhone": "+23480123"},
      format="json",
    )
    self.assertEqual(res.status_code, 400)
    self.assertIn("+234", res.json()["detail"])

  def test_manual_tutor_verification_decision_endpoint_is_removed(self):
    pending_tutor = AppUser.objects.create_user(
      email="queue@example.com",
      password="queue123",
      role="tutor",
      display_name="Queue Tutor",
      full_name="Queue Tutor",
      timezone="UTC",
      is_verified=True,
    )
    pending_profile = TutorProfile.objects.create(
      user=pending_tutor,
      headline="Physics",
      bio="Queue",
      subjects_csv="Physics",
      hourly_rate_cents=400000,
      languages_csv="English",
      verification_status="pending",
      is_listed=False,
      profile_photo_url="/media/images/tutors/photo.jpg",
    )
    verification = VerificationRequest.objects.create(
      tutor_profile=pending_profile,
      status="pending",
      home_state="Lagos",
      home_city="Lagos",
      home_address="4 Queue Road",
      qualification="M.Sc",
      nin_number="10987654321",
      profile_photo_url="/media/images/tutors/photo.jpg",
      document_urls='["/media/documents/tutors/id.pdf","/media/documents/tutors/qualification.pdf"]',
    )

    self._login("admin@example.com", "admin123")
    res = self.client.post(
      f"/api/admin/verification-requests/{verification.id}/approve",
      {"notes": "Looks good"},
      format="json",
    )
    self.assertEqual(res.status_code, 404)

    pending_profile.refresh_from_db()
    verification.refresh_from_db()
    self.assertEqual(pending_profile.verification_status, "pending")
    self.assertFalse(pending_profile.is_listed)
    self.assertEqual(verification.status, "pending")

  def test_approved_tutor_can_save_additional_documents(self):
    self._login("tutor@example.com", "tutor123")
    res = self.client.put(
      "/api/tutors/me/profile",
      {"additionalDocumentUrls": ["/media/documents/tutors/extra-proof.pdf"]},
      format="json",
    )
    self.assertEqual(res.status_code, 403)

  def test_marketplace_tutor_list(self):
    res = self.client.get("/api/tutors")
    self.assertEqual(res.status_code, 200)
    data = res.json()
    self.assertGreaterEqual(len(data["results"]), 1)

  def test_tutor_list_filters_by_search(self):
    """Test tutor search functionality"""
    res = self.client.get("/api/tutors?q=Math")
    self.assertEqual(res.status_code, 200)
    data = res.json()
    self.assertIn("results", data)

  def test_tutor_list_filters_by_rate(self):
    """Test tutor filtering by hourly rate"""
    res = self.client.get("/api/tutors?minRate=40&maxRate=60")
    self.assertEqual(res.status_code, 200)
    data = res.json()
    self.assertIn("results", data)

  def test_tutor_detail_requires_listed_tutor(self):
    """Test that unlisted tutors are not accessible"""
    self.tutor_profile.is_listed = False
    self.tutor_profile.save()
    res = self.client.get(f"/api/tutors/{self.tutor_profile.id}")
    self.assertEqual(res.status_code, 404)

  def test_tutor_detail_rejects_invalid_tutor_id(self):
    res = self.client.get("/api/tutors/index.txt")
    self.assertEqual(res.status_code, 404)

  def test_tutor_reviews_reject_invalid_tutor_id(self):
    res = self.client.get("/api/tutors/index.txt/reviews")
    self.assertEqual(res.status_code, 404)

  def test_approved_listed_tutor_can_change_email_with_otp(self):
    approved_tutor = AppUser.objects.create_user(
      email="locked-email@example.com",
      password="locked123",
      role="tutor",
      display_name="Locked Email Tutor",
      timezone="UTC",
      is_verified=True,
    )
    TutorProfile.objects.create(
      user=approved_tutor,
      headline="Tutor",
      bio="Bio",
      subjects_csv="Math",
      hourly_rate_cents=5000,
      languages_csv="English",
      verification_status="approved",
      is_listed=True,
    )

    self.client.force_authenticate(user=approved_tutor)
    res = self.client.post("/api/me/change-email/request", {"newEmail": "new@example.com"}, format="json")
    self.assertEqual(res.status_code, 200)
    code = re.search(r"\b([A-Z0-9]{6})\b", mail.outbox[-1].body).group(1)
    confirm = self.client.post("/api/me/change-email/confirm", {"code": code}, format="json")
    self.assertEqual(confirm.status_code, 200)
    approved_tutor.refresh_from_db()
    self.assertEqual(approved_tutor.email, "new@example.com")

  def test_approved_listed_tutor_can_change_phone_with_otp(self):
    approved_tutor = AppUser.objects.create_user(
      email="locked-phone@example.com",
      password="locked123",
      role="tutor",
      display_name="Locked Phone Tutor",
      timezone="UTC",
      is_verified=True,
      mobile_number="+2348012345678",
    )
    TutorProfile.objects.create(
      user=approved_tutor,
      headline="Tutor",
      bio="Bio",
      subjects_csv="Math",
      hourly_rate_cents=5000,
      languages_csv="English",
      verification_status="approved",
      is_listed=True,
    )

    self.client.force_authenticate(user=approved_tutor)
    res = self.client.post("/api/me/change-phone/request", {"newPhone": "+2348099999999"}, format="json")
    self.assertEqual(res.status_code, 200)
    code = re.search(r"\b([A-Z0-9]{6})\b", mail.outbox[-1].body).group(1)
    confirm = self.client.post("/api/me/change-phone/confirm", {"code": code}, format="json")
    self.assertEqual(confirm.status_code, 200)
    approved_tutor.refresh_from_db()
    self.assertEqual(approved_tutor.mobile_number, "+2348099999999")

  def test_approved_listed_tutor_can_change_qualification_with_otp(self):
    approved_tutor = AppUser.objects.create_user(
      email="qualification@example.com",
      password="locked123",
      role="tutor",
      display_name="Qualification Tutor",
      timezone="UTC",
      is_verified=True,
    )
    tutor_profile = TutorProfile.objects.create(
      user=approved_tutor,
      headline="Tutor",
      bio="Bio",
      subjects_csv="Math",
      hourly_rate_cents=5000,
      languages_csv="English",
      qualification="B.Ed",
      verification_status="approved",
      is_listed=True,
    )
    verification = VerificationRequest.objects.create(
      tutor_profile=tutor_profile,
      qualification="B.Ed",
      status="approved",
    )

    self.client.force_authenticate(user=approved_tutor)
    res = self.client.post(
      "/api/me/change-qualification/request",
      {"newQualification": "M.Ed, Mathematics"},
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    code = re.search(r"\b([A-Z0-9]{6})\b", mail.outbox[-1].body).group(1)
    confirm = self.client.post("/api/me/change-qualification/confirm", {"code": code}, format="json")
    self.assertEqual(confirm.status_code, 200)
    tutor_profile.refresh_from_db()
    verification.refresh_from_db()
    self.assertEqual(tutor_profile.qualification, "M.Ed, Mathematics")
    self.assertEqual(verification.qualification, "M.Ed, Mathematics")
    profile_res = self.client.get("/api/tutors/me/profile")
    self.assertEqual(profile_res.status_code, 200)
    self.assertEqual(profile_res.json()["qualification"], "M.Ed, Mathematics")

  def test_tutor_can_send_support_message(self):
    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.post(
      "/api/support/contact",
      {"subject": "Locked profile field", "message": "Please help update my NIN number."},
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(mail.outbox), 1)
    self.assertEqual(mail.outbox[0].to, ["support@prepvilla.info"])
    self.assertIn("Full name: Tutor", mail.outbox[0].body)
    self.assertIn("Email: tutor@example.com", mail.outbox[0].body)
    self.assertIn("Please help update my NIN number.", mail.outbox[0].body)

  def test_student_booking_request_creates_conversation(self):
    self._login("student@example.com", "student123")
    res = self.client.get(f"/api/tutors/{self.tutor_profile.id}")
    self.assertEqual(res.status_code, 200)
    slot_id = res.json()["availability"][0]["id"]

    res2 = self.client.post(
      f"/api/tutors/{self.tutor_profile.id}/booking-requests",
      {"lessonType": "Trial", "slotId": slot_id, "notes": "Hi"},
      format="json",
    )
    self.assertEqual(res2.status_code, 200)
    payload = res2.json()
    self.assertIn("bookingId", payload)
    self.assertIn("conversation", payload)

  def test_student_can_view_their_bookings(self):
    """Test that students can only view their own bookings"""
    self._login("student@example.com", "student123")
    res = self.client.get("/api/bookings")
    self.assertEqual(res.status_code, 200)
    self.assertIn("results", res.json())

  def test_tutor_can_view_their_bookings(self):
    """Test that tutors can only view their own bookings"""
    self._login("tutor@example.com", "tutor123")
    res = self.client.get("/api/bookings")
    self.assertEqual(res.status_code, 200)
    self.assertIn("results", res.json())

  def test_approved_tutor_can_store_default_google_meet_room(self):
    meeting_url = "https://meet.google.com/abc-mnop-xyz"

    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.post(
      "/api/tutors/me/video-room",
      {
        "videoMeetingUrl": meeting_url,
        "videoMeetingSpace": "spaces/jQCFfuBOdN5z",
      },
      format="json",
    )

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["videoMeetingUrl"], meeting_url)

    self.tutor_profile.refresh_from_db()
    self.assertEqual(self.tutor_profile.video_meeting_url, meeting_url)
    self.assertEqual(self.tutor_profile.video_meeting_space, "spaces/jQCFfuBOdN5z")

  def test_tutor_can_store_google_meet_room_for_webcam_booking(self):
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="confirmed",
      lesson_type="Webcam",
    )
    meeting_url = "https://meet.google.com/def-uvwx-yza"

    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.post(
      f"/api/bookings/{booking.id}/video-room",
      {
        "videoMeetingUrl": meeting_url,
        "videoMeetingSpace": "spaces/A1b2C3d4E5",
      },
      format="json",
    )

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["videoMeetingUrl"], meeting_url)

    booking.refresh_from_db()
    self.assertEqual(booking.video_meeting_url, meeting_url)
    self.assertEqual(booking.video_meeting_space, "spaces/A1b2C3d4E5")

    res = self.client.get("/api/bookings")
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["results"][0]["videoMeetingUrl"], meeting_url)

  def test_public_booking_video_room_access_is_available_during_booking_window(self):
    start = timezone.now() + timedelta(minutes=10)
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="confirmed",
      lesson_type="Webcam",
      starts_at=start,
      ends_at=start + timedelta(hours=1),
    )

    res = self.client.get(f"/api/video-rooms/prepvilla-booking-{booking.id}/access")

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["source"], "booking")
    self.assertEqual(res.json()["roomName"], f"prepvilla-booking-{booking.id}")
    self.assertEqual(res.json()["expiresAt"], booking.ends_at.isoformat())

  def test_public_booking_video_room_access_blocks_early_entry(self):
    start = timezone.now() + timedelta(hours=1)
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="confirmed",
      lesson_type="Webcam",
      starts_at=start,
      ends_at=start + timedelta(hours=1),
    )

    res = self.client.get(f"/api/video-rooms/prepvilla-booking-{booking.id}/access")

    self.assertEqual(res.status_code, 403)
    self.assertEqual(res.json()["error"], "This room is not open yet.")

  def test_public_booking_video_room_access_expires_after_booking_end(self):
    end = timezone.now() - timedelta(minutes=5)
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="confirmed",
      lesson_type="Webcam",
      starts_at=end - timedelta(hours=1),
      ends_at=end,
    )

    res = self.client.get(f"/api/video-rooms/prepvilla-booking-{booking.id}/access")

    self.assertEqual(res.status_code, 410)
    self.assertEqual(res.json()["error"], "This room link has expired.")

  def test_student_cannot_store_google_meet_room_for_booking(self):
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="confirmed",
      lesson_type="Webcam",
    )

    self.client.force_authenticate(user=self.student)
    res = self.client.post(
      f"/api/bookings/{booking.id}/video-room",
      {
        "videoMeetingUrl": "https://meet.google.com/ghi-jklm-nop",
        "videoMeetingSpace": "spaces/Z9y8X7w6V5",
      },
      format="json",
    )

    self.assertEqual(res.status_code, 403)

  def test_tutor_can_confirm_requested_booking(self):
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="requested",
      lesson_type="Trial",
    )

    self._login("tutor@example.com", "tutor123")
    res = self.client.post(f"/api/bookings/{booking.id}/confirm", {}, format="json")
    self.assertEqual(res.status_code, 200)

    booking.refresh_from_db()
    self.assertEqual(booking.status, "confirmed")

  def test_tutor_can_reject_requested_booking(self):
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="requested",
      lesson_type="Trial",
    )

    self._login("tutor@example.com", "tutor123")
    res = self.client.post(f"/api/bookings/{booking.id}/reject", {}, format="json")
    self.assertEqual(res.status_code, 200)

    booking.refresh_from_db()
    self.assertEqual(booking.status, "rejected")

  def test_student_cannot_confirm_booking(self):
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="requested",
      lesson_type="Trial",
    )

    self._login("student@example.com", "student123")
    res = self.client.post(f"/api/bookings/{booking.id}/confirm", {}, format="json")
    self.assertEqual(res.status_code, 403)

  def test_student_can_cancel_their_booking(self):
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="confirmed",
      lesson_type="Trial",
    )

    self._login("student@example.com", "student123")
    res = self.client.post(f"/api/bookings/{booking.id}/cancel", {}, format="json")
    self.assertEqual(res.status_code, 200)

    booking.refresh_from_db()
    self.assertEqual(booking.status, "cancelled")

  def test_tutor_cannot_confirm_non_requested_booking(self):
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="confirmed",
      lesson_type="Trial",
    )

    self._login("tutor@example.com", "tutor123")
    res = self.client.post(f"/api/bookings/{booking.id}/confirm", {}, format="json")
    self.assertEqual(res.status_code, 400)

  def test_booking_requires_valid_slot(self):
    """Test booking with invalid slot"""
    self._login("student@example.com", "student123")
    res = self.client.post(
      f"/api/tutors/{self.tutor_profile.id}/booking-requests",
      {"lessonType": "Trial", "slotId": "00000000-0000-0000-0000-000000000000"},
      format="json",
    )
    self.assertEqual(res.status_code, 400)

  def test_messaging_rest_endpoint(self):
    self._login("student@example.com", "student123")
    res = self.client.post("/api/conversations", {"tutorId": str(self.tutor_profile.id)}, format="json")
    self.assertEqual(res.status_code, 200)
    conv_id = res.json()["conversation"]["id"]

    res2 = self.client.post(
      f"/api/conversations/{conv_id}/messages",
      {"body": "Hello"},
      format="json",
    )
    self.assertEqual(res2.status_code, 200)
    msg = res2.json()["message"]
    self.assertEqual(msg["body"], "Hello")

  def test_messages_require_body(self):
    """Test that messages require a body"""
    self._login("student@example.com", "student123")
    res = self.client.post("/api/conversations", {"tutorId": str(self.tutor_profile.id)}, format="json")
    conv_id = res.json()["conversation"]["id"]
    
    res2 = self.client.post(
      f"/api/conversations/{conv_id}/messages",
      {},
      format="json",
    )
    self.assertEqual(res2.status_code, 400)

  def test_conversation_blocked_after_rejection(self):
    """Test that conversation is blocked after booking rejection"""
    # Create booking and reject it
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="requested",
      lesson_type="Trial",
    )
    booking.status = "rejected"
    booking.save()
    
    conv = Conversation.objects.get(tutor_profile=self.tutor_profile, student_user=self.student)
    self.assertTrue(conv.is_blocked)

  def test_tutor_can_update_availability(self):
    """Test tutor can update their availability slots"""
    self._login("tutor@example.com", "tutor123")
    now = timezone.now()
    start = now + timedelta(days=1)
    end = start + timedelta(hours=1)
    
    res = self.client.post(
      "/api/tutors/me/availability",
      {
        "slots": [
          {"startsAt": start.isoformat(), "endsAt": end.isoformat()}
        ]
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertIn("results", res.json())

  def test_tutor_can_update_profile(self):
    """Test tutor can update their profile"""
    self._login("tutor@example.com", "tutor123")
    res = self.client.put(
      "/api/tutors/me/profile",
      {
        "headline": "New Headline",
        "bio": "New bio",
        "hourlyRate": 75,
        "subjects": ["Math", "Physics"],
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["headline"], "New Headline")

  def test_unapproved_tutor_cannot_update_profile(self):
    pending_tutor = AppUser.objects.create_user(
      email="locked-profile@example.com",
      password="locked123",
      role="tutor",
      display_name="Locked Tutor",
      timezone="UTC",
      is_verified=True,
    )
    TutorProfile.objects.create(
      user=pending_tutor,
      headline="",
      bio="",
      subjects_csv="",
      hourly_rate_cents=0,
      languages_csv="",
      verification_status="pending",
      is_listed=False,
    )

    self.client.force_authenticate(user=pending_tutor)
    res = self.client.put(
      "/api/tutors/me/profile",
      {
        "headline": "Blocked update",
        "bio": "Blocked bio",
        "subjects": ["Mathematics"],
        "languages": ["English"],
        "hourlyRate": 50,
      },
      format="json",
    )
    self.assertEqual(res.status_code, 403)

  def test_approved_unlisted_tutor_can_complete_profile_and_become_listed(self):
    approved_tutor = AppUser.objects.create_user(
      email="approved-unlisted@example.com",
      password="approved123",
      role="tutor",
      display_name="Approved Tutor",
      timezone="UTC",
      is_verified=True,
    )
    approved_profile = TutorProfile.objects.create(
      user=approved_tutor,
      headline="",
      bio="",
      subjects_csv="",
      hourly_rate_cents=0,
      languages_csv="",
      verification_status="approved",
      is_listed=False,
      profile_photo_url="/media/images/tutors/profile.jpg",
    )

    self.client.force_authenticate(user=approved_tutor)
    res = self.client.put(
      "/api/tutors/me/profile",
      {
        "headline": "Approved Headline",
        "bio": "Ready to teach students.",
        "subjects": ["Mathematics"],
        "languages": ["English"],
        "hourlyRate": 75,
        "homeCity": "Lagos",
        "homeState": "Lagos",
        "homeAddress": "1 Tutor Street",
        "stateOfOrigin": "Oyo",
        "lgaOfOrigin": "Ibadan North",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertTrue(res.json()["isListed"])
    self.assertEqual(res.json()["lgaOfOrigin"], "Ibadan North")

    approved_profile.refresh_from_db()
    self.assertTrue(approved_profile.is_listed)
    self.assertEqual(approved_profile.lga_of_origin, "Ibadan North")

  def test_tutor_profile_returns_verification_origin_fields(self):
    self.tutor_profile.state_of_origin = "Lagos"
    self.tutor_profile.lga_of_origin = "Ikeja"
    self.tutor_profile.country_of_birth = "Nigeria"
    self.tutor_profile.nationality = "Nigerian"
    self.tutor_profile.save(
      update_fields=["state_of_origin", "lga_of_origin", "country_of_birth", "nationality"]
    )
    self.client.force_authenticate(user=self.tutor_user)

    res = self.client.get("/api/tutors/me/profile")

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["stateOfOrigin"], "Lagos")
    self.assertEqual(res.json()["lgaOfOrigin"], "Ikeja")
    self.assertEqual(res.json()["countryOfBirth"], "Nigeria")
    self.assertEqual(res.json()["nationality"], "Nigerian")

  def test_tutor_profile_update_persists_photo_url(self):
    self.client.force_authenticate(user=self.tutor_user)
    photo_url = "/media/images/tutors/profile_photo.jpg"
    res = self.client.put(
      "/api/tutors/me/profile",
      {
        "profilePhotoUrl": photo_url,
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["profilePhotoUrl"], photo_url)

    self.tutor_profile.refresh_from_db()
    self.tutor_user.refresh_from_db()
    self.assertEqual(self.tutor_profile.profile_photo_url, photo_url)
    self.assertEqual(self.tutor_user.profile_photo_url, photo_url)

  def test_approved_tutor_can_update_home_state_and_city_on_profile(self):
    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.put(
      "/api/tutors/me/profile",
      {
        "homeState": "Oyo",
        "homeCity": "Ibadan",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["homeState"], "Oyo")
    self.assertEqual(res.json()["homeCity"], "Ibadan")
    self.assertEqual(res.json()["homeAddress"], "")

    self.tutor_profile.refresh_from_db()
    self.assertEqual(self.tutor_profile.home_state, "Oyo")
    self.assertEqual(self.tutor_profile.home_city, "Ibadan")
    self.assertEqual(self.tutor_profile.home_address, "")

  def test_approved_listed_tutor_cannot_update_locked_identity_fields_via_me(self):
    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.put(
      "/api/me",
      {
        "displayName": "Tutor Updated",
        "fullName": "Locked Tutor Name",
        "mobileNumber": "+2348099998888",
        "dateOfBirth": "1991-05-01",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 403)

  def test_approved_listed_tutor_cannot_update_state_of_origin_on_profile(self):
    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.put(
      "/api/tutors/me/profile",
      {
        "stateOfOrigin": "Oyo",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 403)

  def test_approved_listed_tutor_can_update_gender_on_profile(self):
    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.put(
      "/api/tutors/me/profile",
      {
        "gender": "male",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["gender"], "male")

    self.tutor_profile.refresh_from_db()
    self.assertEqual(self.tutor_profile.gender, "male")

    change_res = self.client.put(
      "/api/tutors/me/profile",
      {
        "gender": "female",
      },
      format="json",
    )
    self.assertEqual(change_res.status_code, 403)
    self.tutor_profile.refresh_from_db()
    self.assertEqual(self.tutor_profile.gender, "male")

  def test_approved_tutor_can_update_display_name_and_home_location(self):
    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.put(
      "/api/me",
      {
        "displayName": "Tutor Updated",
        "state": "Lagos",
        "city": "Ikeja",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["displayName"], "Tutor Updated")
    self.assertEqual(res.json()["state"], "Lagos")
    self.assertEqual(res.json()["city"], "Ikeja")
    self.assertEqual(res.json()["address"], "")

  def test_tutor_public_endpoints_fall_back_to_user_photo_url(self):
    photo_url = "/media/images/tutors/fallback_photo.jpg"
    self.tutor_user.profile_photo_url = photo_url
    self.tutor_user.save(update_fields=["profile_photo_url"])
    VerificationRequest.objects.create(
      tutor_profile=self.tutor_profile,
      status="approved",
      profile_photo_url="",
    )

    detail_res = self.client.get(f"/api/tutors/{self.tutor_profile.id}")
    self.assertEqual(detail_res.status_code, 200)
    self.assertEqual(detail_res.json()["tutor"]["profilePhotoUrl"], photo_url)

    list_res = self.client.get("/api/tutors")
    self.assertEqual(list_res.status_code, 200)
    self.assertEqual(list_res.json()["results"][0]["profilePhotoUrl"], photo_url)

  def test_password_reset_confirm_updates_password(self):
    code = "ABC123"
    salt = "0123456789abcdef0123456789abcdef"
    digest = hashlib.sha256((settings.SECRET_KEY + salt + code).encode("utf-8")).hexdigest()
    PasswordResetToken.objects.create(
      user=self.student,
      code_salt=salt,
      code_hash=digest,
      expires_at=timezone.now() + timedelta(minutes=10),
    )

    res = self.client.post(
      "/api/auth/password-reset/confirm",
      {"email": "student@example.com", "code": code, "newPassword": "newpass123"},
      format="json",
    )
    self.assertEqual(res.status_code, 200)

    self.assertTrue(AppUser.objects.get(email="student@example.com").check_password("newpass123"))

  def test_password_reset_rate_limits_attempts(self):
    """Test that password reset limits failed attempts"""
    code = "RIGHT1"
    salt = "0123456789abcdef0123456789abcdef"
    digest = hashlib.sha256((settings.SECRET_KEY + salt + code).encode("utf-8")).hexdigest()
    token = PasswordResetToken.objects.create(
      user=self.student,
      code_salt=salt,
      code_hash=digest,
      expires_at=timezone.now() + timedelta(minutes=10),
    )
    
    # Try multiple wrong codes
    for i in range(6):
      res = self.client.post(
        "/api/auth/password-reset/confirm",
        {"email": "student@example.com", "code": f"WRONG{i}", "newPassword": "newpass123"},
        format="json",
      )
    
    token.refresh_from_db()
    self.assertGreaterEqual(token.attempts, 5)

  @override_settings(BYPASS_VERIFICATION=True)
  def test_tutor_verification_submit_handles_long_urls(self):
    pending_tutor = AppUser.objects.create_user(
      email="longurl@example.com",
      password="longurl123",
      role="tutor",
      display_name="Long Url",
      full_name="Long Url Tutor",
      timezone="UTC",
      is_verified=True,
    )
    TutorProfile.objects.create(
      user=pending_tutor,
      headline="Long URL tutor",
      bio="Ready",
      subjects_csv="Mathematics",
      hourly_rate_cents=7500,
      languages_csv="English",
      verification_status="not_submitted",
      is_listed=False,
    )
    self.client.force_authenticate(user=pending_tutor)
    long_url = "https://example.com/" + ("a" * 1200)
    res = self.client.post(
      "/api/tutors/me/verification",
      {
        "qualification": "B.Ed",
        "ninNumber": "12345678901",
        "bvnNumber": "10987654321",
        "dateOfBirth": "2000-01-01",
        "fullName": "Tutor Example",
        "displayName": "Tutor",
        "mobileNumber": "+2348012345678",
        "homeCity": "Lagos",
        "homeState": "Lagos",
        "homeAddress": "1 Tutor Street, Lagos",
        "stateOfOrigin": "Oyo",
        "subjects": ["Mathematics", "Physics"],
        "languages": ["English"],
        "headline": "Experienced tutor",
        "bio": "Helping students prepare for exams.",
        "hourlyRate": 75,
        "profilePhotoUrl": long_url,
        "documentUrls": [long_url, long_url],
        "notes": "test",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 200)

  @override_settings(BYPASS_VERIFICATION=True)
  def test_tutor_verification_uses_existing_user_fields_when_request_omits_them(self):
    pending_tutor = AppUser.objects.create_user(
      email="existingfields@example.com",
      password="verify123",
      role="tutor",
      display_name="Existing Fields",
      full_name="Existing Fields Tutor",
      timezone="UTC",
      is_verified=True,
      mobile_number="+2348011112222",
      date_of_birth="1992-06-15",
    )
    TutorProfile.objects.create(
      user=pending_tutor,
      headline="Starter tutor",
      bio="Ready to teach",
      subjects_csv="Mathematics",
      hourly_rate_cents=500000,
      languages_csv="English",
      verification_status="not_submitted",
      is_listed=False,
    )

    self.client.force_authenticate(user=pending_tutor)
    res = self.client.post(
      "/api/tutors/me/verification",
      {
        "qualification": "B.Ed",
        "ninNumber": "12345678901",
        "bvnNumber": "10987654321",
        "profilePhotoUrl": "/media/images/tutors/photo.jpg",
        "documentUrls": ["/media/documents/tutors/id.pdf", "/media/documents/tutors/qualification.pdf"],
        "notes": "Please review",
        "homeCity": "Lagos",
        "homeState": "Lagos",
        "homeAddress": "22 Tutor Street",
      },
      format="json",
    )

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["status"], "approved")
    self.assertEqual(res.json()["fullName"], "Existing Fields Tutor")
    self.assertEqual(res.json()["mobileNumber"], "+2348011112222")
    self.assertEqual(res.json()["dateOfBirth"], "1992-06-15")

  def test_approved_tutor_can_update_verification_backed_fields_via_verification_endpoint(self):
    approved_tutor = AppUser.objects.create_user(
      email="approved-fields@example.com",
      password="verify123",
      role="tutor",
      display_name="Approved",
      full_name="Approved Tutor",
      timezone="UTC",
      is_verified=True,
      mobile_number="+2348011112222",
      date_of_birth="1990-01-01",
    )
    approved_profile = TutorProfile.objects.create(
      user=approved_tutor,
      headline="Starter tutor",
      bio="Ready to teach",
      subjects_csv="Mathematics",
      hourly_rate_cents=500000,
      languages_csv="English",
      verification_status="approved",
      is_listed=True,
      home_state="Lagos",
      home_city="Ikeja",
      home_address="11 Old Street",
      qualification="B.Ed",
      nin_number="12345678901",
      profile_photo_url="/uploads/images/tutors/original.webp",
      document_urls='["/uploads/documents/tutors/original-id.pdf"]',
    )
    VerificationRequest.objects.create(
      tutor_profile=approved_profile,
      status="approved",
      home_state="Lagos",
      home_city="Ikeja",
      home_address="11 Old Street",
      qualification="B.Ed",
      nin_number="12345678901",
      profile_photo_url="/uploads/images/tutors/original.webp",
      document_urls='["/uploads/documents/tutors/original-id.pdf"]',
      decided_at=timezone.now(),
    )

    self.client.force_authenticate(user=approved_tutor)
    res = self.client.post(
      "/api/tutors/me/verification",
      {
        "fullName": "Updated Tutor Name",
        "mobileNumber": "+2348099998888",
        "dateOfBirth": "1991-05-01",
        "homeState": "Oyo",
        "homeCity": "Ibadan",
        "homeAddress": "22 Updated Street",
        "qualification": "M.Ed",
        "ninNumber": "10987654321",
        "profilePhotoUrl": "/uploads/images/tutors/updated.webp",
        "documentUrls": ["/uploads/documents/tutors/original-id.pdf"],
      },
      format="json",
    )

    self.assertEqual(res.status_code, 403)
    approved_tutor.refresh_from_db()
    approved_profile.refresh_from_db()
    verification = VerificationRequest.objects.get(tutor_profile=approved_profile)
    self.assertEqual(approved_tutor.full_name, "Approved Tutor")
    self.assertEqual(approved_tutor.mobile_number, "+2348011112222")
    self.assertEqual(approved_tutor.date_of_birth, date(1990, 1, 1))
    self.assertEqual(approved_tutor.state, "")
    self.assertEqual(approved_tutor.location, "")
    self.assertEqual(approved_tutor.address, "")
    self.assertEqual(approved_profile.home_state, "Lagos")
    self.assertEqual(approved_profile.home_city, "Ikeja")
    self.assertEqual(approved_profile.home_address, "11 Old Street")
    self.assertEqual(approved_profile.qualification, "B.Ed")
    self.assertEqual(approved_profile.nin_number, "12345678901")
    self.assertEqual(approved_profile.profile_photo_url, "/uploads/images/tutors/original.webp")
    self.assertEqual(verification.status, "approved")
    self.assertEqual(verification.qualification, "B.Ed")
    self.assertEqual(verification.nin_number, "12345678901")

  @override_settings(SEED_DEMO_ACCOUNTS=True, ENVIRONMENT="development")
  def test_seed_demo_accounts_tutor_creates_updates_and_deletes_seeded_tutors(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      tmp_path = Path(tmpdir)
      seed_dir = tmp_path / "seed_demo_data"
      tutors_dir = seed_dir / "images" / "tutors"
      docs_dir = seed_dir / "images" / "documents"
      uploads_dir = tmp_path / "uploads"
      tutors_dir.mkdir(parents=True)
      docs_dir.mkdir(parents=True)
      uploads_dir.mkdir()

      (tutors_dir / "seeded.webp").write_bytes(b"photo-bytes")
      (docs_dir / "seeded-id.jpg").write_bytes(b"id-bytes")
      (docs_dir / "seeded-qualification.pdf").write_bytes(b"qualification-bytes")

      seed_file = seed_dir / "default_tutors.json"
      seed_payload = {
        "seeded-tutor": {
          "sign_up": {
            "full_name": "Seeded Tutor",
            "email": "seeded@example.com",
            "password": "seeded123",
          },
          "verification": {
            "mobile_number": "+2348012345678",
            "date_of_birth": "1990-02-03",
            "residence": {
              "state": "Lagos",
              "city": "Ikeja",
              "address": "1 Seeded Street",
              "qualification": "B.Ed",
              "nin_number": "12345678901",
              "profile_photo": str(tutors_dir / "seeded.webp"),
              "id_document": str(docs_dir / "seeded-id.jpg"),
              "qualification_document": str(docs_dir / "seeded-qualification.pdf"),
            },
          },
          "profile": {
            "basic_information": {
              "state_of_origin": "Oyo",
            },
            "tutor_profile": {
              "headline": "Seeded headline",
              "hourly_rate": 5000,
              "about": "Seeded biography",
              "subjects": ["Mathematics", "Physics"],
              "language": ["English", "Yoruba"],
              "gender": "male",
              "firs_lesson_free": True,
              "teaching_methods": {
                "face_to_face": True,
                "webcam": True,
              },
            },
          },
        }
      }
      seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

      with override_settings(DEFAULT_TUTOR_SEED_PATH=seed_file, MEDIA_ROOT=uploads_dir):
        create_result = seed_demo_accounts_tutors(force=True)
        self.assertEqual(create_result["created"], 1)
        seeded_user = AppUser.objects.get(email="seeded@example.com")
        seeded_profile = TutorProfile.objects.get(user=seeded_user)
        seeded_verification = VerificationRequest.objects.get(tutor_profile=seeded_profile)
        seeded_tracker = SeededTutorAccount.objects.get(user=seeded_user)

        self.assertTrue(seeded_user.is_verified)
        self.assertTrue(seeded_user.check_password("seeded123"))
        self.assertEqual(seeded_user.display_name, "Seeded")
        self.assertEqual(seeded_user.full_name, "Seeded Tutor")
        self.assertEqual(seeded_user.mobile_number, "+2348012345678")
        self.assertEqual(seeded_profile.verification_status, "approved")
        self.assertTrue(seeded_profile.is_listed)
        self.assertEqual(seeded_profile.headline, "Seeded headline")
        self.assertEqual(seeded_profile.hourly_rate_cents, 500000)
        self.assertEqual(seeded_verification.status, "approved")
        self.assertEqual(seeded_tracker.seed_key, "seeded-tutor")
        self.assertTrue(seeded_tracker.managed_paths)

        seed_payload["seeded-tutor"]["profile"]["tutor_profile"]["headline"] = "Updated seeded headline"
        seed_payload["seeded-tutor"]["verification"]["residence"]["city"] = "Lekki"
        seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

        update_result = seed_demo_accounts_tutors(force=True)
        self.assertEqual(update_result["updated"], 1)
        seeded_user.refresh_from_db()
        seeded_profile.refresh_from_db()
        self.assertEqual(seeded_user.location, "Lekki")
        self.assertEqual(seeded_profile.home_city, "Lekki")
        self.assertEqual(seeded_profile.headline, "Updated seeded headline")

        seed_file.write_text(json.dumps({}), encoding="utf-8")
        delete_result = seed_demo_accounts_tutors(force=True)
        self.assertEqual(delete_result["deleted"], 1)
        self.assertFalse(AppUser.objects.filter(email="seeded@example.com").exists())

  @override_settings(SEED_DEMO_ACCOUNTS=True, ENVIRONMENT="development")
  def test_seed_demo_accounts_student_creates_updates_and_deletes_seeded_students(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      tmp_path = Path(tmpdir)
      seed_dir = tmp_path / "seed_demo_data"
      students_dir = seed_dir / "images" / "student"
      uploads_dir = tmp_path / "uploads"
      students_dir.mkdir(parents=True)
      uploads_dir.mkdir()

      (students_dir / "seeded.jpg").write_bytes(b"student-photo-bytes")

      seed_file = seed_dir / "default_students.json"
      seed_payload = {
        "seeded-student": {
          "sign_up": {
            "full_name": "Seeded Student",
            "email": "seeded-student@example.com",
            "password": "student123",
          },
          "profile": {
            "basic_information": {
              "state": "Lagos",
              "city": "Yaba",
              "address": "2 Seeded Street",
              "mobile_number": "+2348098765432",
              "date_of_birth": "2007-08-21",
              "profile_photo": str(students_dir / "seeded.jpg"),
            },
          },
        },
      }
      seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

      with override_settings(DEFAULT_STUDENT_SEED_PATH=seed_file, MEDIA_ROOT=uploads_dir):
        create_result = seed_demo_accounts_students(force=True)
        self.assertEqual(create_result["created"], 1)
        seeded_user = AppUser.objects.get(email="seeded-student@example.com")
        seeded_verification = StudentVerificationRequest.objects.get(user=seeded_user)
        seeded_tracker = SeededStudentAccount.objects.get(user=seeded_user)

        self.assertTrue(seeded_user.is_verified)
        self.assertTrue(seeded_user.check_password("student123"))
        self.assertEqual(seeded_user.role, "student")
        self.assertEqual(seeded_user.display_name, "Seeded")
        self.assertEqual(seeded_user.full_name, "Seeded Student")
        self.assertEqual(seeded_user.mobile_number, "+2348098765432")
        self.assertEqual(seeded_user.location, "Yaba")
        self.assertEqual(seeded_user.state, "Lagos")
        self.assertEqual(seeded_verification.status, "approved")
        self.assertEqual(seeded_verification.city, "Yaba")
        self.assertEqual(seeded_tracker.seed_key, "seeded-student")
        self.assertTrue(seeded_tracker.managed_paths)

        seed_payload["seeded-student"]["profile"]["basic_information"]["city"] = "Surulere"
        seed_payload["seeded-student"]["profile"]["basic_information"]["address"] = "5 Updated Street"
        seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

        update_result = seed_demo_accounts_students(force=True)
        self.assertEqual(update_result["updated"], 1)
        seeded_user.refresh_from_db()
        seeded_verification.refresh_from_db()
        self.assertEqual(seeded_user.location, "Surulere")
        self.assertEqual(seeded_user.address, "5 Updated Street")
        self.assertEqual(seeded_verification.city, "Surulere")
        self.assertEqual(seeded_verification.address, "5 Updated Street")

        seed_file.write_text(json.dumps({}), encoding="utf-8")
        delete_result = seed_demo_accounts_students(force=True)
        self.assertEqual(delete_result["deleted"], 1)
        self.assertFalse(AppUser.objects.filter(email="seeded-student@example.com").exists())

  def test_me_endpoint_can_update_full_name(self):
    self.client.force_authenticate(user=self.tutor_user)
    res = self.client.put(
      "/api/me",
      {
        "displayName": "Tutor",
        "fullName": "Tutor Example Updated",
        "state": "Lagos",
        "city": "Lagos",
        "address": "1 Tutor Street, Lagos",
      },
      format="json",
    )
    self.assertEqual(res.status_code, 403)

  def test_unauthenticated_requests_to_protected_endpoints(self):
    """Test that protected endpoints require authentication"""
    endpoints = [
      "/api/me",
      "/api/bookings",
      "/api/conversations",
      "/api/tutors/me/profile",
      "/api/tutors/me/availability",
      "/api/tutors/me/verification",
    ]
    for endpoint in endpoints:
      res = self.client.get(endpoint)
      self.assertEqual(res.status_code, 401)

  def test_admin_can_access_verification_queue(self):
    """Test admin access to verification queue"""
    self._login("admin@example.com", "admin123")
    res = self.client.get("/api/admin/verification-requests")
    self.assertEqual(res.status_code, 200)
    self.assertIn("results", res.json())

  def test_student_cannot_access_admin_endpoints(self):
    """Test that students cannot access admin endpoints"""
    self._login("student@example.com", "student123")
    res = self.client.get("/api/admin/verification-requests")
    self.assertEqual(res.status_code, 403)


class ReviewTests(TestCase):
  def setUp(self):
    self.client = APIClient()

    self.student = AppUser.objects.create_user(
      email="student@example.com",
      password="student123",
      role="student",
      display_name="Student",
      timezone="UTC",
      is_verified=True,
    )

    self.tutor_user = AppUser.objects.create_user(
      email="tutor@example.com",
      password="tutor123",
      role="tutor",
      display_name="Tutor",
      timezone="UTC",
      is_verified=True,
    )

    self.tutor_profile = TutorProfile.objects.create(
      user=self.tutor_user,
      headline="Math tutoring",
      bio="Experienced teacher",
      subjects_csv="Math,Algebra",
      hourly_rate_cents=5000,
      languages_csv="English",
      verification_status="approved",
      is_listed=True,
    )

  def _login(self, email: str, password: str):
    res = self.client.post("/api/auth/login", {"email": email, "password": password}, format="json")
    self.assertEqual(res.status_code, 200)
    token = res.json()["accessToken"]
    self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

  def test_get_tutor_reviews(self):
    """Test getting reviews for a tutor"""
    # Create a completed booking
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="completed",
      lesson_type="Trial",
    )
    
    # Create a review
    Review.objects.create(
      booking=booking,
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      rating=5,
      comment="Great tutor!",
    )

    res = self.client.get(f"/api/tutors/{self.tutor_profile.id}/reviews")
    self.assertEqual(res.status_code, 200)
    data = res.json()
    self.assertIn("reviews", data)
    self.assertIn("summary", data)
    self.assertEqual(len(data["reviews"]), 1)
    self.assertEqual(data["summary"]["averageRating"], 5.0)
    self.assertEqual(data["summary"]["totalReviews"], 1)

  def test_get_tutor_review_summary(self):
    """Test getting review summary for a tutor"""
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="completed",
      lesson_type="Trial",
    )
    
    Review.objects.create(
      booking=booking,
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      rating=4,
      comment="Good session",
    )

    res = self.client.get(f"/api/tutors/{self.tutor_profile.id}/reviews/summary")
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["averageRating"], 4.0)
    self.assertEqual(res.json()["totalReviews"], 1)

  def test_submit_review_for_completed_booking(self):
    """Test submitting a review for a completed booking"""
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="completed",
      lesson_type="Trial",
    )

    self._login("student@example.com", "student123")
    res = self.client.post(
      f"/api/bookings/{booking.id}/review",
      {"rating": 5, "comment": "Excellent session!"},
      format="json",
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.json()["rating"], 5)
    self.assertEqual(res.json()["comment"], "Excellent session!")

  def test_cannot_review_non_completed_booking(self):
    """Test that only completed bookings can be reviewed"""
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="requested",
      lesson_type="Trial",
    )

    self._login("student@example.com", "student123")
    res = self.client.post(
      f"/api/bookings/{booking.id}/review",
      {"rating": 5, "comment": "Excellent session!"},
      format="json",
    )
    self.assertEqual(res.status_code, 400)
    self.assertIn("completed", res.json()["detail"].lower())

  def test_cannot_review_others_booking(self):
    """Test that students cannot review others' bookings"""
    other_student = AppUser.objects.create_user(
      email="other@example.com",
      password="other123",
      role="student",
      display_name="Other Student",
      timezone="UTC",
    )
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=other_student,
      status="completed",
      lesson_type="Trial",
    )

    self._login("student@example.com", "student123")
    res = self.client.post(
      f"/api/bookings/{booking.id}/review",
      {"rating": 5, "comment": "Excellent session!"},
      format="json",
    )
    self.assertEqual(res.status_code, 403)

  def test_cannot_submit_duplicate_review(self):
    """Test that a booking can only be reviewed once"""
    booking = Booking.objects.create(
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      status="completed",
      lesson_type="Trial",
    )

    Review.objects.create(
      booking=booking,
      tutor_profile=self.tutor_profile,
      student_user=self.student,
      rating=5,
      comment="Great!",
    )

    self._login("student@example.com", "student123")
    res = self.client.post(
      f"/api/bookings/{booking.id}/review",
      {"rating": 5, "comment": "Second review"},
      format="json",
    )
    self.assertEqual(res.status_code, 400)
