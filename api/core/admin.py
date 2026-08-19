from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from core.models import (
  AvailabilitySlot,
  Booking,
  BookingPayment,
  Conversation,
  Message,
  PaymentLedgerEntry,
  PaymentWebhookEvent,
  PlatformAdminUser,
  PlatformFeeTransfer,
  StudentVerificationRequest,
  StudentUser,
  SubscriptionPayment,
  SupportRequest,
  TutorProfile,
  TutorPayout,
  TutorUser,
  VerificationRequest,
)
from core.tutor_sync import apply_verified_tutor_fields

TUTOR_VERIFICATION_STATUS_CHOICES = (
  ("pending", "Pending"),
  ("approved", "Verified"),
  ("rejected", "Rejected"),
)

admin.site.site_header = "PrepVilla Admin"
admin.site.site_title = "PrepVilla Admin"
admin.site.index_title = "PrepVilla Administration"


@admin.register(StudentVerificationRequest)
class StudentVerificationRequestAdmin(admin.ModelAdmin):
  list_display = ("user", "status", "mobile_number", "state", "city", "submitted_at", "reviewed_at")
  list_filter = ("status", "state", "submitted_at", "reviewed_at")
  search_fields = ("user__email", "user__display_name", "user__full_name", "nin_number", "bvn_number")
  readonly_fields = (
    "id", "user", "profile_photo_url", "date_of_birth", "mobile_number", "nin_number", "bvn_number",
    "country_of_birth", "nationality", "state_of_origin", "lga_of_origin", "qualification", "document_urls",
    "city", "state", "address", "notes", "submitted_at",
  )
  raw_id_fields = ("reviewed_by",)
  ordering = ("-submitted_at",)


def normalize_verification_status(value: str | None) -> str:
  normalized = (value or "").strip().lower()
  if normalized in {"approved", "verified"}:
    return "approved"
  if normalized == "rejected":
    return "rejected"
  return "pending"


class RoleUserAdmin(UserAdmin):
  role_value = ""
  ordering = ("email",)
  list_display = ("email", "full_name", "display_name", "is_verified", "is_active", "created_at")
  search_fields = ("email", "display_name", "full_name", "mobile_number")
  list_filter = ("is_verified", "is_active", "state", "created_at")
  fieldsets = (
    (None, {"fields": ("email", "password")}),
    (
      "Profile",
      {
        "fields": (
          "full_name",
          "display_name",
          "timezone",
          "mobile_number",
          "date_of_birth",
          "state",
          "location",
          "address",
          "profile_photo_url",
        )
      },
    ),
    ("Account Status", {"fields": ("is_verified", "is_active")}),
  )
  add_fieldsets = (
    (
      None,
      {
        "classes": ("wide",),
        "fields": (
          "email",
          "full_name",
          "display_name",
          "password1",
          "password2",
          "timezone",
          "is_verified",
          "is_active",
        ),
      },
    ),
  )

  def get_queryset(self, request):
    return super().get_queryset(request).filter(role=self.role_value)

  def save_model(self, request, obj, form, change):
    obj.role = self.role_value
    super().save_model(request, obj, form, change)


@admin.register(StudentUser)
class StudentUserAdmin(RoleUserAdmin):
  role_value = "student"


@admin.register(TutorUser)
class TutorUserAdmin(RoleUserAdmin):
  role_value = "tutor"


@admin.register(PlatformAdminUser)
class PlatformAdminUserAdmin(UserAdmin):
  ordering = ("email",)
  list_display = ("email", "full_name", "display_name", "is_staff", "is_superuser", "is_active")
  search_fields = ("email", "display_name", "full_name")
  list_filter = ("is_staff", "is_superuser", "is_active", "is_verified")
  fieldsets = (
    (None, {"fields": ("email", "password")}),
    ("Profile", {"fields": ("full_name", "display_name", "timezone")}),
    ("Account Status", {"fields": ("is_verified", "is_active")}),
    ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
  )
  add_fieldsets = (
    (
      None,
      {
        "classes": ("wide",),
        "fields": (
          "email",
          "full_name",
          "display_name",
          "password1",
          "password2",
          "timezone",
          "is_verified",
          "is_active",
          "is_staff",
          "is_superuser",
        ),
      },
    ),
  )

  def get_queryset(self, request):
    return super().get_queryset(request).filter(role="admin")

  def save_model(self, request, obj, form, change):
    obj.role = "admin"
    super().save_model(request, obj, form, change)


class TutorProfileAdminForm(forms.ModelForm):
  email_address = forms.EmailField(label="Email", required=False, disabled=True)
  full_name = forms.CharField(label="Full Name", max_length=255, required=False)
  display_name = forms.CharField(label="Display Name", max_length=255, required=False)
  mobile_number = forms.CharField(label="Mobile Number", max_length=32, required=False)
  date_of_birth = forms.DateField(
    label="Date of Birth",
    required=False,
    widget=forms.DateInput(attrs={"type": "date"}),
  )

  class Meta:
    model = TutorProfile
    exclude = ("verification_status", "document_urls", "additional_document_urls")

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if self.instance and self.instance.pk and self.instance.user_id:
      self.fields["email_address"].initial = self.instance.user.email
      self.fields["full_name"].initial = self.instance.user.full_name
      self.fields["display_name"].initial = self.instance.user.display_name
      self.fields["mobile_number"].initial = self.instance.user.mobile_number
      self.fields["date_of_birth"].initial = self.instance.user.date_of_birth


class VerificationRequestAdminForm(forms.ModelForm):
  email_address = forms.EmailField(label="Email", required=False, disabled=True)
  full_name = forms.CharField(label="Full Name", max_length=255, required=False)
  mobile_number = forms.CharField(label="Mobile Number", max_length=32, required=False)
  date_of_birth = forms.DateField(
    label="Date of Birth",
    required=False,
    widget=forms.DateInput(attrs={"type": "date"}),
  )
  profile_photo_url = forms.CharField(
    label="Profile Photo URL",
    required=False,
    help_text="Accepts relative upload paths such as /uploads/images/...",
  )
  status = forms.ChoiceField(
    label="Verification Status",
    choices=TUTOR_VERIFICATION_STATUS_CHOICES,
    required=True,
  )

  class Meta:
    model = VerificationRequest
    fields = "__all__"

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if self.instance and self.instance.pk and self.instance.tutor_profile_id:
      tutor_user = self.instance.tutor_profile.user
      self.fields["email_address"].initial = tutor_user.email
      self.fields["full_name"].initial = tutor_user.full_name
      self.fields["mobile_number"].initial = tutor_user.mobile_number
      self.fields["date_of_birth"].initial = tutor_user.date_of_birth
      self.fields["status"].initial = normalize_verification_status(self.instance.status)


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
  form = TutorProfileAdminForm
  list_display = ("user_email", "display_name_value", "full_name_value", "headline", "is_listed")
  search_fields = ("user__email", "user__display_name", "user__full_name", "headline", "subjects_csv")
  list_filter = ("is_listed", "gender", "home_state")
  raw_id_fields = ("user",)
  fieldsets = (
    (
      "Tutor Account",
      {"fields": ("user", "email_address", "full_name", "display_name", "mobile_number", "date_of_birth")},
    ),
    (
      "Basic Information",
      {
        "fields": (
          "home_state",
          "home_city",
          "home_address",
          "state_of_origin",
          "profile_photo_url",
        )
      },
    ),
    (
      "Professional Information",
      {
        "fields": (
          "qualification",
          "nin_number",
          "bvn_number",
        )
      },
    ),
    (
      "Payout Account",
      {
        "fields": (
          "bank_name",
          "bank_code",
          "bank_account_number",
          "bank_account_name",
        )
      },
    ),
    (
      "Tutor Profile",
      {
        "fields": (
          "headline",
          "bio",
          "subjects_csv",
          "languages_csv",
          "hourly_rate_cents",
          "gender",
          "response_time",
          "first_lesson_free",
          "offers_face_to_face",
          "offers_webcam",
          "is_listed",
        )
      },
    ),
  )

  @admin.display(description="Email", ordering="user__email")
  def user_email(self, obj: TutorProfile):
    return obj.user.email if obj.user_id else ""

  @admin.display(description="Display Name", ordering="user__display_name")
  def display_name_value(self, obj: TutorProfile):
    return obj.user.display_name if obj.user_id else ""

  @admin.display(description="Full Name", ordering="user__full_name")
  def full_name_value(self, obj: TutorProfile):
    return obj.user.full_name if obj.user_id else ""

  def save_model(self, request, obj, form, change):
    super().save_model(request, obj, form, change)
    if not obj.user_id:
      return

    tutor_user = obj.user
    changed_fields = []
    full_name = (form.cleaned_data.get("full_name") or "").strip()
    display_name = (form.cleaned_data.get("display_name") or "").strip()
    mobile_number = (form.cleaned_data.get("mobile_number") or "").strip()
    date_of_birth = form.cleaned_data.get("date_of_birth")
    profile_photo_url = (obj.profile_photo_url or "").strip()

    if tutor_user.full_name != full_name:
      tutor_user.full_name = full_name
      changed_fields.append("full_name")
    if tutor_user.display_name != display_name:
      tutor_user.display_name = display_name
      changed_fields.append("display_name")
    if tutor_user.mobile_number != mobile_number:
      tutor_user.mobile_number = mobile_number
      changed_fields.append("mobile_number")
    if tutor_user.date_of_birth != date_of_birth:
      tutor_user.date_of_birth = date_of_birth
      changed_fields.append("date_of_birth")
    if tutor_user.location != obj.home_city:
      tutor_user.location = obj.home_city
      changed_fields.append("location")
    if tutor_user.state != obj.home_state:
      tutor_user.state = obj.home_state
      changed_fields.append("state")
    if tutor_user.address != obj.home_address:
      tutor_user.address = obj.home_address
      changed_fields.append("address")
    if tutor_user.profile_photo_url != profile_photo_url:
      tutor_user.profile_photo_url = profile_photo_url
      changed_fields.append("profile_photo_url")

    if changed_fields:
      tutor_user.save(update_fields=changed_fields)


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
  form = VerificationRequestAdminForm
  list_display = ("user_email", "verification_request", "status", "submitted_at", "decided_at")
  search_fields = (
    "tutor_profile__user__email",
    "tutor_profile__user__display_name",
    "tutor_profile__user__full_name",
    "home_state",
    "home_city",
    "home_address",
    "qualification",
    "nin_number",
    "bvn_number",
  )
  list_filter = ("status", "submitted_at", "decided_at")
  raw_id_fields = ("tutor_profile",)
  readonly_fields = ("submitted_at", "decided_at")
  fieldsets = (
    (
      "Tutor Account",
      {"fields": ("tutor_profile", "email_address", "full_name", "mobile_number", "date_of_birth")},
    ),
    (
      "Verification Request",
      {
        "fields": (
          "status",
          "home_state",
          "home_city",
          "home_address",
          "qualification",
          "nin_number",
          "bvn_number",
          "profile_photo_url",
          "document_urls",
          "notes",
        )
      },
    ),
    ("Review History", {"fields": ("submitted_at", "decided_at")}),
  )

  @admin.display(description="Email", ordering="tutor_profile__user__email")
  def user_email(self, obj: VerificationRequest):
    return obj.tutor_profile.user.email if obj.tutor_profile_id else ""

  @admin.display(description="Verification Request")
  def verification_request(self, obj: VerificationRequest):
    if not obj.tutor_profile_id:
      return "Verification request"
    display_name = obj.tutor_profile.user.display_name or obj.tutor_profile.user.full_name or "Tutor"
    return f"{display_name} verification"

  def get_queryset(self, request):
    return super().get_queryset(request).select_related("tutor_profile__user")

  def save_model(self, request, obj, form, change):
    next_status = normalize_verification_status(form.cleaned_data.get("status"))
    previous_status = normalize_verification_status(
      VerificationRequest.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
      if change and obj.pk
      else obj.status
    )
    status_changed = previous_status != next_status
    obj.status = next_status
    if next_status in {"approved", "rejected"}:
      obj.decided_at = timezone.now() if status_changed or obj.decided_at is None else obj.decided_at
    else:
      obj.decided_at = None

    super().save_model(request, obj, form, change)

    if not obj.tutor_profile_id:
      return

    tutor_profile = obj.tutor_profile
    tutor_user = tutor_profile.user
    normalized_photo_url = (obj.profile_photo_url or "").strip()
    full_name = (form.cleaned_data.get("full_name") or "").strip()
    mobile_number = (form.cleaned_data.get("mobile_number") or "").strip()
    date_of_birth = form.cleaned_data.get("date_of_birth")
    apply_verified_tutor_fields(
      tutor_user,
      tutor_profile,
      full_name=full_name,
      mobile_number=mobile_number,
      date_of_birth=date_of_birth,
      home_state=obj.home_state,
      home_city=obj.home_city,
      home_address=obj.home_address,
      qualification=obj.qualification,
      nin_number=obj.nin_number,
      bvn_number=obj.bvn_number,
      profile_photo_url=normalized_photo_url,
      document_urls=obj.document_urls or "",
      verification_status=next_status,
      is_listed=tutor_profile.is_listed if next_status == "approved" else False,
    )

admin.site.register(AvailabilitySlot)
admin.site.register(Booking)
admin.site.register(Conversation)
admin.site.register(Message)


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
  list_display = (
    "ticket", "kind", "topic", "user", "role", "priority", "status", "assigned_to", "created_at", "resolved_at",
  )
  list_filter = ("kind", "status", "priority", "role", "created_at", "resolved_at")
  search_fields = ("id", "topic", "message", "related_reference", "user__email", "user__display_name", "user__full_name")
  readonly_fields = (
    "id", "ticket", "user", "kind", "role", "topic", "message", "related_reference", "metadata", "created_at", "updated_at",
  )
  raw_id_fields = ("assigned_to",)
  ordering = ("-created_at",)
  fieldsets = (
    ("Request", {"fields": ("id", "ticket", "kind", "priority", "status", "user", "role", "topic", "message", "related_reference", "metadata")}),
    ("Resolution", {"fields": ("assigned_to", "admin_notes", "resolved_at")}),
    ("Audit", {"fields": ("created_at", "updated_at")}),
  )

  @admin.display(description="Ticket")
  def ticket(self, obj):
    return obj.ticket_number

  def get_queryset(self, request):
    return super().get_queryset(request).select_related("user", "assigned_to")

  def save_model(self, request, obj, form, change):
    if obj.status in {SupportRequest.Status.RESOLVED, SupportRequest.Status.CLOSED}:
      obj.resolved_at = obj.resolved_at or timezone.now()
    else:
      obj.resolved_at = None
    super().save_model(request, obj, form, change)


class ImmutableFinancialAdmin(admin.ModelAdmin):
  """Payment audit records are maintained only by verified provider workflows."""

  def get_readonly_fields(self, request, obj=None):
    return tuple(field.name for field in self.model._meta.concrete_fields)

  def has_add_permission(self, request):
    return False

  def has_delete_permission(self, request, obj=None):
    return False


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(ImmutableFinancialAdmin):
  list_display = (
    "transaction_id", "user", "plan", "amount", "currency", "payment_method", "status", "paid_at", "created_at"
  )
  list_filter = ("status", "plan", "currency", "payment_method", "provider", "created_at")
  search_fields = ("transaction_id", "provider_transaction_id", "user__email", "user__display_name")
  ordering = ("-created_at",)


@admin.register(BookingPayment)
class BookingPaymentAdmin(ImmutableFinancialAdmin):
  list_display = (
    "transaction_id", "booking", "student_user", "tutor_profile", "amount", "platform_fee_amount",
    "tutor_amount", "currency", "payment_method", "status", "paid_at", "released_at",
  )
  list_filter = ("status", "currency", "payment_method", "provider", "created_at")
  search_fields = (
    "transaction_id", "provider_transaction_id", "student_user__email", "tutor_profile__user__email",
  )
  ordering = ("-created_at",)


@admin.register(TutorPayout)
class TutorPayoutAdmin(ImmutableFinancialAdmin):
  list_display = (
    "transfer_reference", "booking_payment", "tutor_profile", "amount", "currency", "status",
    "processed_at", "completed_at", "failed_at",
  )
  list_filter = ("status", "currency", "created_at")
  search_fields = (
    "transfer_reference", "provider_transfer_id", "booking_payment__transaction_id", "tutor_profile__user__email",
  )
  ordering = ("-created_at",)


@admin.register(PlatformFeeTransfer)
class PlatformFeeAdmin(ImmutableFinancialAdmin):
  list_display = ("booking_payment", "amount", "currency", "status", "created_at")
  list_filter = ("status", "currency", "created_at")
  search_fields = ("booking_payment__transaction_id", "booking_payment__student_user__email")
  ordering = ("-created_at",)


@admin.register(PaymentLedgerEntry)
class PaymentLedgerEntryAdmin(ImmutableFinancialAdmin):
  list_display = ("reference", "entry_type", "amount", "currency", "status", "provider_reference", "created_at")
  list_filter = ("entry_type", "status", "currency", "created_at")
  search_fields = (
    "reference", "provider_reference", "subscription_payment__transaction_id", "booking_payment__transaction_id",
  )
  ordering = ("-created_at",)


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(ImmutableFinancialAdmin):
  list_display = (
    "provider_event_id", "event_type", "transaction_reference", "provider_transaction_id", "status", "received_at",
  )
  list_filter = ("event_type", "status", "received_at")
  search_fields = (
    "provider_event_id", "transaction_reference", "provider_transaction_id", "transfer_reference", "event_key",
  )
  ordering = ("-received_at",)
