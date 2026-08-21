from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
import uuid
from django.utils import timezone

class AppUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("display_name", "Admin")
        extra_fields.setdefault("full_name", "Admin")
        extra_fields.setdefault("timezone", "UTC")
        extra_fields.setdefault("is_verified", True)
        return self.create_user(email, password, **extra_fields)


class AppUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20)
    display_name = models.CharField(max_length=120)
    timezone = models.CharField(max_length=60)
    
    # NEW FIELDS
    full_name = models.CharField(max_length=255, blank=True, default="")
    mobile_number = models.CharField(max_length=20, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    profile_photo_url = models.URLField(blank=True, default="", help_text="Profile photo URL for students")
    location = models.CharField(max_length=100, blank=True, default="", help_text="Student location/city")
    state = models.CharField(max_length=100, blank=True, default="", help_text="Student state/province")
    address = models.TextField(blank=True, default="", help_text="Student full address")
    
    # Account Status Fields
    is_verified = models.BooleanField(default=False, help_text="Whether email is verified via OTP")
    is_frozen = models.BooleanField(default=False, help_text="Whether account is temporarily frozen")
    frozen_until = models.DateTimeField(null=True, blank=True, help_text="When freeze ends (if frozen)")
    is_pending_deletion = models.BooleanField(default=False, help_text="Whether account deletion is requested")
    deletion_scheduled_at = models.DateTimeField(null=True, blank=True, help_text="When account will be permanently deleted")
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = AppUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name", "role"]

    def __str__(self):
        return self.email
    
    def can_perform_actions(self):
        """Check if user can perform platform actions (not frozen, verified, etc.)"""
        if self.is_frozen and self.frozen_until and self.frozen_until > timezone.now():
            return False
        return self.is_active and self.is_verified


class StudentUser(AppUser):
    class Meta:
        proxy = True
        verbose_name = "Student"
        verbose_name_plural = "Students"


class TutorUser(AppUser):
    class Meta:
        proxy = True
        verbose_name = "Tutor"
        verbose_name_plural = "Tutors"


class PlatformAdminUser(AppUser):
    class Meta:
        proxy = True
        verbose_name = "Platform admin"
        verbose_name_plural = "Platform admins"


class TutorProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(AppUser, on_delete=models.CASCADE, related_name="tutor_profile")
    headline = models.CharField(max_length=140)
    bio = models.TextField()
    subjects_csv = models.TextField()
    hourly_rate_cents = models.IntegerField()
    languages_csv = models.TextField()
    gender = models.CharField(max_length=20, blank=True, default="")
    home_state = models.CharField(max_length=120, blank=True, default="")
    home_city = models.CharField(max_length=120, blank=True, default="")
    home_address = models.CharField(max_length=255, blank=True, default="")
    state_of_origin = models.CharField(max_length=120, blank=True, default="")
    lga_of_origin = models.CharField(max_length=120, blank=True, default="")
    country_of_birth = models.CharField(max_length=120, blank=True, default="")
    nationality = models.CharField(max_length=120, blank=True, default="")
    verification_status = models.CharField(max_length=20, default="not_submitted")
    is_listed = models.BooleanField(default=False)
    profile_photo_url = models.CharField(max_length=500, blank=True, default="")
    
    # Verification Fields
    qualification = models.CharField(max_length=255, blank=True, default="")
    nin_number = models.CharField(max_length=50, blank=True, default="")
    bvn_number = models.CharField(max_length=20, blank=True, default="")
    document_urls = models.TextField(blank=True, default="", help_text="Comma separated URLs")
    response_time = models.CharField(max_length=50, blank=True, default="", help_text="e.g., 2 hours")
    first_lesson_free = models.BooleanField(default=False)
    offers_face_to_face = models.BooleanField(default=True)
    offers_webcam = models.BooleanField(default=False)
    video_meeting_url = models.URLField(blank=True, default="")
    video_meeting_space = models.CharField(max_length=120, blank=True, default="")
    additional_document_urls = models.TextField(
        blank=True,
        default="",
        help_text="JSON encoded list of additional supporting document URLs",
    )
    bank_name = models.CharField(max_length=120, blank=True, default="")
    bank_code = models.CharField(max_length=20, blank=True, default="")
    bank_account_number = models.CharField(max_length=20, blank=True, default="")
    bank_account_name = models.CharField(max_length=160, blank=True, default="")
    flutterwave_subaccount_id = models.CharField(max_length=80, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def subjects(self):
        return [s.strip() for s in self.subjects_csv.split(",") if s.strip()]

    def languages(self):
        return [l.strip() for l in self.languages_csv.split(",") if l.strip()]
    
    def __str__(self):
        return f"Tutor: {self.user.display_name}"

    class Meta:
        indexes = [
            models.Index(fields=["is_listed", "verification_status"], name="core_tutor_listed_status_idx"),
            models.Index(fields=["home_state", "home_city"], name="core_tutor_state_city_idx"),
            models.Index(fields=["hourly_rate_cents"], name="core_tutor_rate_idx"),
            models.Index(fields=["gender"], name="core_tutor_gender_idx"),
        ]


class VerificationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor_profile = models.OneToOneField(TutorProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ("pending", "Pending"),
        ("approved", "Verified"),
        ("rejected", "Rejected")
    ], default="pending")
    home_state = models.CharField(max_length=120, blank=True, default="")
    home_city = models.CharField(max_length=120, blank=True, default="")
    home_address = models.CharField(max_length=255, blank=True, default="")
    qualification = models.CharField(max_length=100, blank=True)
    nin_number = models.CharField(max_length=20, blank=True)
    bvn_number = models.CharField(max_length=20, blank=True, default="")
    profile_photo_url = models.CharField(max_length=500, blank=True, default="")
    document_urls = models.TextField(blank=True)  # JSON or comma separated
    notes = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class SeededTutorAccount(models.Model):
    user = models.OneToOneField(AppUser, on_delete=models.CASCADE, related_name="seeded_tutor_account")
    seed_key = models.CharField(max_length=120, unique=True)
    source_hash = models.CharField(max_length=64, blank=True, default="")
    managed_paths = models.TextField(blank=True, default="", help_text="JSON encoded list of storage paths managed by the seed sync")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Seeded tutor {self.seed_key}: {self.user.email}"


class SeededStudentAccount(models.Model):
    user = models.OneToOneField(AppUser, on_delete=models.CASCADE, related_name="seeded_student_account")
    seed_key = models.CharField(max_length=120, unique=True)
    source_hash = models.CharField(max_length=64, blank=True, default="")
    managed_paths = models.TextField(blank=True, default="", help_text="JSON encoded list of storage paths managed by the seed sync")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Seeded student {self.seed_key}: {self.user.email}"


class OTP(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()


class AccountFreezeRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="freeze_requests")
    starts_on = models.DateField()
    ends_on = models.DateField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class AccountDeleteRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="delete_requests")
    code_salt = models.CharField(max_length=32)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class MeOtpChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="me_otp_challenges")
    purpose = models.CharField(max_length=50)
    payload = models.TextField(blank=True, default="")
    code_salt = models.CharField(max_length=32)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class PendingSignupChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=20)
    full_name = models.CharField(max_length=255)
    password_hash = models.CharField(max_length=255)
    code_salt = models.CharField(max_length=32)
    code_hash = models.CharField(max_length=64)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE)
    code_salt = models.CharField(max_length=32)
    code_hash = models.CharField(max_length=64)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AvailabilitySlot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor_profile = models.ForeignKey(TutorProfile, on_delete=models.CASCADE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    recurrence_rule = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tutor_profile", "starts_at"], name="core_slot_tutor_start_idx"),
        ]


class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor_profile = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="bookings")
    student_user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="bookings")
    status = models.CharField(max_length=20, default="requested")
    lesson_type = models.CharField(max_length=100, default="Lesson")
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    requested_from = models.DateTimeField(null=True, blank=True)
    requested_to = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    video_meeting_url = models.URLField(blank=True, default="")
    video_meeting_space = models.CharField(max_length=120, blank=True, default="")
    student_completed_at = models.DateTimeField(null=True, blank=True)
    tutor_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == "rejected":
            Conversation.objects.get_or_create(
                tutor_profile=self.tutor_profile,
                student_user=self.student_user,
                defaults={"is_blocked": True},
            )
            Conversation.objects.filter(
                tutor_profile=self.tutor_profile,
                student_user=self.student_user,
            ).update(is_blocked=True)

    class Meta:
        indexes = [
            models.Index(fields=["student_user", "created_at"], name="core_book_student_ct_idx"),
            models.Index(fields=["tutor_profile", "created_at"], name="core_booking_tutor_created_idx"),
            models.Index(fields=["status", "created_at"], name="core_book_status_ct_idx"),
        ]


class SubscriptionPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="subscription_payments")
    plan = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    provider = models.CharField(max_length=40, default="flutterwave")
    transaction_id = models.CharField(max_length=120, unique=True)
    provider_transaction_id = models.CharField(max_length=120, blank=True, default="")
    payment_link = models.URLField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_payload = models.JSONField(default=dict, blank=True)
    payment_method = models.CharField(max_length=40, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"], name="core_subpay_user_created_idx"),
            models.Index(fields=["status", "created_at"], name="core_subpay_status_created_idx"),
        ]


class BookingPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    student_user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="booking_payments")
    tutor_profile = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="booking_payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    provider = models.CharField(max_length=40, default="flutterwave")
    transaction_id = models.CharField(max_length=120, unique=True)
    provider_transaction_id = models.CharField(max_length=120, blank=True, default="")
    payment_link = models.URLField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_payload = models.JSONField(default=dict, blank=True)
    payment_method = models.CharField(max_length=40, blank=True, default="")
    platform_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tutor_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    held_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["student_user", "created_at"], name="core_bookpay_student_ct_idx"),
            models.Index(fields=["tutor_profile", "status"], name="core_bookpay_tutor_status_idx"),
        ]


class TutorPayout(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_payment = models.OneToOneField(BookingPayment, on_delete=models.CASCADE, related_name="tutor_payout")
    tutor_profile = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    transfer_reference = models.CharField(max_length=120, blank=True, default="")
    provider_transfer_id = models.CharField(max_length=120, blank=True, default="")
    provider_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PlatformFeeTransfer(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_payment = models.OneToOneField(
        BookingPayment,
        on_delete=models.CASCADE,
        related_name="platform_fee_transfer",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    transfer_reference = models.CharField(max_length=120, blank=True, default="")
    provider_transfer_id = models.CharField(max_length=120, blank=True, default="")
    provider_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "platform fee"
        verbose_name_plural = "platform fees"


class SupportRequest(models.Model):
    class Kind(models.TextChoices):
        FEEDBACK = "feedback", "Feedback"
        COMPLAINT = "complaint", "Complaint"
        ISSUE = "issue", "Issue"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="support_requests")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    role = models.CharField(max_length=20)
    topic = models.CharField(max_length=160)
    message = models.TextField()
    related_reference = models.CharField(max_length=160, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    admin_notes = models.TextField(blank=True, default="")
    assigned_to = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        related_name="assigned_support_requests",
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["kind", "status", "-created_at"], name="core_support_kind_status_idx"),
            models.Index(fields=["user", "-created_at"], name="core_support_user_created_idx"),
            models.Index(fields=["priority", "status"], name="core_support_priority_idx"),
        ]

    @property
    def ticket_number(self) -> str:
        return f"PV-{str(self.id).split('-')[0].upper()}"


class PaymentLedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        SUBSCRIPTION_COLLECTION = "subscription_collection", "Subscription collection"
        LESSON_COLLECTION = "lesson_collection", "Lesson collection"
        PLATFORM_FEE = "platform_fee", "PrepVilla fee"
        TUTOR_PAYABLE = "tutor_payable", "Tutor payable"
        TUTOR_PAYOUT = "tutor_payout", "Tutor payout"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        HELD = "held", "Held"
        AVAILABLE = "available", "Available"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=160, unique=True)
    entry_type = models.CharField(max_length=40, choices=EntryType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    subscription_payment = models.ForeignKey(
        SubscriptionPayment,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
        null=True,
        blank=True,
    )
    booking_payment = models.ForeignKey(
        BookingPayment,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
        null=True,
        blank=True,
    )
    tutor_payout = models.ForeignKey(
        TutorPayout,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
        null=True,
        blank=True,
    )
    provider_reference = models.CharField(max_length=120, blank=True, default="", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["entry_type", "status"], name="core_ledger_type_status_idx"),
            models.Index(fields=["booking_payment", "entry_type"], name="core_ledger_booking_type_idx"),
        ]


class PaymentWebhookEvent(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        IGNORED = "ignored", "Ignored"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_key = models.CharField(max_length=64, unique=True)
    provider_event_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    event_type = models.CharField(max_length=80, blank=True, default="", db_index=True)
    transaction_reference = models.CharField(max_length=160, blank=True, default="", db_index=True)
    provider_transaction_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    transfer_reference = models.CharField(max_length=160, blank=True, default="", db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    payload = models.JSONField(default=dict)
    error_message = models.TextField(blank=True, default="")
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-received_at",)
        indexes = [
            models.Index(fields=["event_type", "status"], name="core_webhook_type_status_idx"),
        ]


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor_profile = models.ForeignKey(TutorProfile, on_delete=models.CASCADE)
    student_user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="student_conversations")
    participants = models.ManyToManyField(AppUser, related_name='conversations')
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student_user", "created_at"], name="core_conv_student_created_idx"),
            models.Index(fields=["tutor_profile", "created_at"], name="core_conv_tutor_created_idx"),
        ]


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    sender_user = models.ForeignKey(AppUser, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)


class Review(models.Model):
    """Review model for tutors from students after completed bookings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    tutor_profile = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="reviews")
    student_user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        unique_together = ["booking", "tutor_profile", "student_user"]
        indexes = [
            models.Index(fields=["tutor_profile", "created_at"], name="core_review_tutor_created_idx"),
        ]
    
    def __str__(self):
        return f"Review by {self.student_user.display_name} for {self.tutor_profile.user.display_name}: {self.rating} stars"


class FavoriteTutor(models.Model):
    """Student-saved tutor profiles shown in dashboard favorites."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="favorite_tutors")
    tutor_profile = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["student_user", "tutor_profile"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student_user", "created_at"], name="core_fav_student_created_idx"),
        ]

    def __str__(self):
        return f"{self.student_user.display_name} favorited {self.tutor_profile.user.display_name}"


class MobileNumberChangeRequest(models.Model):
    """Requests for changing mobile numbers that require admin approval"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="mobile_change_requests")
    current_mobile = models.CharField(max_length=20, blank=True, default="")
    requested_mobile = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=[
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected")
    ], default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(AppUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_mobile_changes")
    admin_notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Mobile change request by {self.user.display_name}: {self.current_mobile} → {self.requested_mobile}"


class StudentVerificationRequest(models.Model):
    """Verification requests for student profiles before they can contact tutors"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(AppUser, on_delete=models.CASCADE, related_name="student_verification")
    profile_photo_url = models.CharField(max_length=500, help_text="Student profile photo URL")
    date_of_birth = models.DateField(help_text="Student date of birth")
    mobile_number = models.CharField(max_length=20, help_text="Student mobile number")
    nin_number = models.CharField(max_length=20, blank=True, default="")
    bvn_number = models.CharField(max_length=20, blank=True, default="")
    country_of_birth = models.CharField(max_length=120, blank=True, default="")
    nationality = models.CharField(max_length=120, blank=True, default="")
    state_of_origin = models.CharField(max_length=120, blank=True, default="")
    lga_of_origin = models.CharField(max_length=120, blank=True, default="")
    qualification = models.CharField(max_length=255, blank=True, default="")
    document_urls = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="", help_text="Student city")
    state = models.CharField(max_length=100, help_text="Student state/province")
    address = models.TextField(help_text="Student full address")
    
    status = models.CharField(max_length=20, choices=[
        ("pending", "Pending"),
        ("approved", "Verified"),
        ("rejected", "Rejected")
    ], default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(AppUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_student_verifications")
    admin_notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Student verification request by {self.user.display_name}"
