import datetime as dt
import json
import hashlib
import hmac
import logging
import os
import re
import secrets
import string
import uuid
import base64
import time
from urllib.parse import urlencode, quote, unquote, urlparse
from urllib.request import Request, urlopen
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import connections, transaction
from django.db.models import Min, Avg, Count
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

from .models import (
    AccountFreezeRequest,
    AccountDeleteRequest,
    MeOtpChallenge,
    PendingSignupChallenge,
    AppUser,
    AvailabilitySlot,
    Booking,
    BookingPayment,
    Conversation,
    FavoriteTutor,
    Message,
    MobileNumberChangeRequest,
    PasswordResetToken,
    Review,
    StudentVerificationRequest,
    SubscriptionPayment,
    SupportRequest,
    TutorPayout,
    TutorProfile,
    VerificationRequest,
)
from .permissions import IsStudent, IsTutor
from .tutor_sync import (
    APPROVED_TUTOR_STATUSES,
    apply_verified_tutor_fields,
    normalize_tutor_verification_status,
)
from django.db.models import Q

logger = logging.getLogger(__name__)
NIGERIAN_MOBILE_NUMBER_RE = re.compile(r"^\+234\d{10}$")
NIN_NUMBER_RE = re.compile(r"^\d{11}$")
PREPVILLA_ROOM_PREFIX = "prepvilla-"
BOOKING_ROOM_EARLY_ACCESS_MINUTES = 15
BVN_NUMBER_RE = NIN_NUMBER_RE

from .serializers import (
    BookingRowSerializer,
    BookingSerializer,
    ConversationSerializer,
    TutorCardSerializer,
    TutorDetailsSerializer,
    TutorMeProfileSerializer,
    AvailabilitySlotSerializer,
    VerificationStateSerializer,
)
from .flutterwave import FlutterwaveError, verify_webhook_signature
from .payment_queue import TASK_FLUTTERWAVE_WEBHOOK, enqueue_payment_task
from .payments import (
    create_booking_checkout,
    create_subscription_checkout,
    queue_tutor_payout,
    record_flutterwave_webhook,
    verify_customer_payment,
)
from .subscription_plans import get_subscription_plan, get_subscription_plan_catalog
from .dikript_verification import DikriptVerificationUnavailable
from .prembly_verification import PremblyVerificationUnavailable
from .verification_service import is_verification_configured, verify_nin_and_bvn, verify_nin_identity

def _bad_request(msg: str, status: int = 400):
    return JsonResponse({"error": msg, "detail": msg}, status=status)

def _send_email(subject, message, recipients, html_message=None):
    from django.core.mail import EmailMessage
    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        if html_message:
            email.content_subtype = "html"
            email.body = html_message
        email.send()
        return True
    except Exception:
        logger.exception("Email send failed")
        return False


def _generate_email_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def _issue_email_code(user: AppUser, subject: str, message: str) -> bool:
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    otp = _generate_email_code()
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((settings.SECRET_KEY + salt + otp).encode("utf-8")).hexdigest()
    expires_at = timezone.now() + timedelta(minutes=15)
    challenge = PasswordResetToken.objects.create(
        user=user,
        code_salt=salt,
        code_hash=digest,
        expires_at=expires_at,
    )
    sent = _send_email(subject, f"{message}\n\n{otp}\n\nThis code will expire in 15 minutes.\n", [user.email])
    if not sent:
        challenge.used_at = timezone.now()
        challenge.save(update_fields=["used_at"])
    return sent


def _ensure_tutor_profile(user: AppUser):
    if user.role == "tutor" and not hasattr(user, "tutor_profile"):
        TutorProfile.objects.create(
            user=user,
            headline="",
            bio="",
            subjects_csv="",
            hourly_rate_cents=0,
            languages_csv="",
        )


def _normalize_tutor_verification_status(value: str | None) -> str:
    return normalize_tutor_verification_status(value)


def _tutor_is_approved(
    tutor_profile: TutorProfile | None,
    verification: VerificationRequest | None = None,
) -> bool:
    if tutor_profile and _normalize_tutor_verification_status(tutor_profile.verification_status) == "approved":
        return True
    if verification and _normalize_tutor_verification_status(verification.status) == "approved":
        return True
    return False


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_mobile_number(value, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError("Mobile number is required")
        return None
    if not isinstance(value, str):
        raise ValueError("Mobile number is required")
    normalized = re.sub(r"\s+", "", value.strip())
    if not normalized:
        if required:
            raise ValueError("Mobile number is required")
        return ""
    if not NIGERIAN_MOBILE_NUMBER_RE.fullmatch(normalized):
        raise ValueError("Mobile number must start with +234 and contain 13 digits excluding the + sign.")
    return normalized


def _normalize_nin_number(value, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError("NIN number is required")
        return None
    if not isinstance(value, str):
        raise ValueError("NIN number is required")
    normalized = re.sub(r"\s+", "", value.strip())
    if not normalized:
        if required:
            raise ValueError("NIN number is required")
        return ""
    if not NIN_NUMBER_RE.fullmatch(normalized):
        raise ValueError("NIN number must be exactly 11 digits.")
    return normalized


def _normalize_bvn_number(value, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError("BVN number is required")
        return None
    if not isinstance(value, str):
        raise ValueError("BVN number is required")
    normalized = re.sub(r"\s+", "", value.strip())
    if not normalized:
        if required:
            raise ValueError("BVN number is required")
        return ""
    if not BVN_NUMBER_RE.fullmatch(normalized):
        raise ValueError("BVN number must be exactly 11 digits.")
    return normalized


def _load_string_list(value: str | None) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    raw = value.strip()
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = None
    if isinstance(parsed, list):
        results: list[str] = []
        for item in parsed:
            text = str(item).strip()
            if text:
                results.append(text)
        return results
    return [item.strip() for item in raw.split(",") if item.strip()]


def _dump_string_list(items) -> str:
    values: list[str] = []
    if isinstance(items, list):
        for item in items:
            text = str(item).strip()
            if text:
                values.append(text)
    return json.dumps(values)


def _optional_date_iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str):
        normalized = value.strip()
        return normalized[:10] if normalized else None
    return None


def _split_full_name(value: str | None) -> tuple[str, str, str]:
    parts = [part for part in re.split(r"\s+", str(value or "").strip()) if part]
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def _compose_full_name(first_name: str | None, middle_name: str | None, last_name: str | None) -> str:
    return " ".join(
        part.strip()
        for part in (first_name or "", middle_name or "", last_name or "")
        if isinstance(part, str) and part.strip()
    )


def _tutor_teaching_modes(tutor_profile: TutorProfile) -> list[str]:
    modes: list[str] = []
    if tutor_profile.offers_face_to_face or not tutor_profile.offers_webcam:
        modes.append("face_to_face")
    if tutor_profile.offers_webcam:
        modes.append("webcam")
    return modes


def _tutor_video_call_url(tutor_profile: TutorProfile) -> str | None:
    if not tutor_profile.offers_webcam:
        return None
    return "/dashboard/video-room"


def _booking_video_call_url(booking: Booking) -> str | None:
    lesson_type = (booking.lesson_type or "").strip().lower()
    if "webcam" not in lesson_type:
        return None
    return f"/dashboard/video-room?bookingId={quote(str(booking.id))}"


def _normalize_google_meet_url(value) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    try:
        parsed = urlparse(normalized)
    except Exception:
        return None
    if parsed.scheme != "https" or parsed.netloc != "meet.google.com":
        return None
    if not parsed.path or parsed.path == "/":
        return None
    return normalized


def _normalize_video_meeting_space(value) -> str | None:
    if value is None:
        return ""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return ""
    if not re.fullmatch(r"spaces/[A-Za-z0-9_-]+", normalized):
        return None
    return normalized


def _sanitize_room_segment(value: str) -> str:
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9-]+", "-", value.lower()))[:80]


def _build_managed_room_name(seed: str) -> str:
    normalized = _sanitize_room_segment(seed)
    return f"{PREPVILLA_ROOM_PREFIX}{normalized}" if normalized else f"{PREPVILLA_ROOM_PREFIX}room"


def _extract_managed_room_name(meeting_url: str | None) -> str | None:
    if not isinstance(meeting_url, str) or not meeting_url.strip():
        return None
    try:
        parsed = urlparse(meeting_url.strip())
    except Exception:
        return None
    if parsed.scheme != "https" or not parsed.path or parsed.path == "/":
        return None
    room_name = unquote(parsed.path.replace("/", "", 1)).strip().lower()
    return room_name if room_name.startswith(PREPVILLA_ROOM_PREFIX) else None


def _parse_booking_room_id(room_name: str) -> str | None:
    match = re.fullmatch(r"prepvilla-booking-([0-9a-f-]{36})", room_name)
    return match.group(1) if match else None


def _parse_tutor_lobby_user_id(room_name: str) -> str | None:
    match = re.fullmatch(r"prepvilla-tutor-([0-9a-f-]{36})-lobby", room_name)
    return match.group(1) if match else None


def _booking_room_names(booking: Booking) -> set[str]:
    names = {_build_managed_room_name(f"booking-{booking.id}")}
    stored_room_name = _extract_managed_room_name(booking.video_meeting_url or None)
    if stored_room_name:
        names.add(stored_room_name)
    return names


def _tutor_lobby_room_names(tutor_profile: TutorProfile) -> set[str]:
    names = {_build_managed_room_name(f"tutor-{tutor_profile.user_id}-lobby")}
    stored_room_name = _extract_managed_room_name(tutor_profile.video_meeting_url or None)
    if stored_room_name:
        names.add(stored_room_name)
    return names


def _room_access_payload(
    *,
    room_name: str,
    source: str,
    title: str,
    starts_at=None,
    opens_at=None,
    ends_at=None,
):
    return {
        "roomName": room_name,
        "source": source,
        "title": title,
        "startsAt": starts_at.isoformat() if starts_at else None,
        "opensAt": opens_at.isoformat() if opens_at else None,
        "endsAt": ends_at.isoformat() if ends_at else None,
        "expiresAt": ends_at.isoformat() if ends_at else None,
    }


def _find_booking_for_room_name(room_name: str) -> Booking | None:
    booking_id = _parse_booking_room_id(room_name)
    if booking_id:
        return Booking.objects.select_related("tutor_profile__user", "student_user").filter(id=booking_id).first()
    return (
        Booking.objects.select_related("tutor_profile__user", "student_user")
        .filter(video_meeting_url__icontains=room_name)
        .first()
    )


def _find_tutor_lobby_for_room_name(room_name: str) -> TutorProfile | None:
    tutor_user_id = _parse_tutor_lobby_user_id(room_name)
    if tutor_user_id:
        return TutorProfile.objects.select_related("user").filter(user_id=tutor_user_id, offers_webcam=True).first()
    return TutorProfile.objects.select_related("user").filter(offers_webcam=True, video_meeting_url__icontains=room_name).first()


def _default_dashboard_path(user: AppUser) -> str:
    if user.role == "student":
        return "/dashboard/profile"
    if user.role == "tutor":
        _ensure_tutor_profile(user)
        tutor_profile = TutorProfile.objects.filter(user=user).first()
        verification = VerificationRequest.objects.filter(tutor_profile=tutor_profile).first() if tutor_profile else None
        return "/dashboard/profile" if _tutor_is_approved(tutor_profile, verification) else "/dashboard/verification"
    if user.role == "admin":
        return "/admin/verification"
    return "/dashboard"


def _apply_tutor_verification_decision(
    tutor_profile: TutorProfile,
    verification: VerificationRequest,
    *,
    approved: bool,
    notes: str = "",
):
    status = "approved" if approved else "rejected"
    verification.status = status
    verification.decided_at = timezone.now()
    verification.notes = notes
    verification.save(update_fields=["status", "decided_at", "notes"])

    tutor_user = tutor_profile.user
    apply_verified_tutor_fields(
        tutor_user,
        tutor_profile,
        full_name=tutor_user.full_name,
        mobile_number=tutor_user.mobile_number,
        date_of_birth=tutor_user.date_of_birth,
        home_state=verification.home_state,
        home_city=verification.home_city,
        home_address=verification.home_address,
        qualification=verification.qualification,
        nin_number=verification.nin_number,
        bvn_number=verification.bvn_number,
        state_of_origin=tutor_profile.state_of_origin,
        lga_of_origin=tutor_profile.lga_of_origin,
        country_of_birth=tutor_profile.country_of_birth,
        nationality=tutor_profile.nationality,
        profile_photo_url=verification.profile_photo_url,
        document_urls=verification.document_urls,
        verification_status=status,
        is_listed=approved and tutor_profile.is_listed,
    )


def _issue_pending_signup_code(email: str, role: str, full_name: str, password: str) -> bool:
    now = timezone.now()
    PendingSignupChallenge.objects.filter(email=email, used_at__isnull=True).update(used_at=now)
    otp = _generate_email_code()
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((settings.SECRET_KEY + salt + otp).encode("utf-8")).hexdigest()
    challenge = PendingSignupChallenge.objects.create(
        email=email,
        role=role,
        full_name=full_name,
        password_hash=make_password(password),
        code_salt=salt,
        code_hash=digest,
        expires_at=now + timedelta(minutes=15),
    )
    subject = "Verify your email"
    message = "Welcome to PrepVilla!\nPlease use the verification code below to verify your email."
    sent = _send_email(subject, f"{message}\n\n{otp}\n\nThis code will expire in 15 minutes.\n", [email])
    if not sent:
        challenge.used_at = now
        challenge.save(update_fields=["used_at"])
    return sent


def _auth_response(user: AppUser):
    from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

    access = AccessToken.for_user(user)
    refresh = RefreshToken.for_user(user)
    first_name, middle_name, last_name = _split_full_name(user.full_name or user.display_name)
    return {
        "accessToken": str(access),
        "refreshToken": str(refresh),
        "user": {
            "id": str(user.id),
            "role": user.role,
            "displayName": user.display_name,
            "email": user.email,
            "fullName": user.full_name or user.display_name,
            "firstName": first_name,
            "middleName": middle_name,
            "lastName": last_name,
        },
        "defaultDashboardPath": _default_dashboard_path(user),
    }


def _invalid_token_response(message: str = "Given token not valid for any token type"):
    return JsonResponse(
        {
            "detail": message,
            "code": "token_not_valid",
            "messages": [
                {
                    "token_class": "RefreshToken",
                    "token_type": "refresh",
                    "message": message,
                }
            ],
        },
        status=401,
    )


def _review_summary_payload(reviews):
    avg = reviews.aggregate(avg=Avg("rating"))["avg"] or 0
    counts = {rating: reviews.filter(rating=rating).count() for rating in range(1, 6)}
    return {
        "averageRating": round(avg, 1),
        "totalReviews": reviews.count(),
        "ratingCounts": counts,
    }

def _parse_dt(value: str):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timezone.is_aware(parsed):
            return parsed
        return timezone.make_aware(parsed)
    except Exception:
        return None


def _parse_uuid_or_none(value):
    if value is None:
        return None
    try:
        return uuid.UUID(str(value).strip())
    except (AttributeError, TypeError, ValueError):
        return None


def _frontend_base_url() -> str:
    return (
        os.environ.get("WEB_PUBLIC_URL", "")
        or "http://localhost:3500"
    ).rstrip("/")


def _is_approved_listed_tutor(user: AppUser) -> bool:
    if getattr(user, "role", None) != "tutor":
        return False
    tutor_profile = TutorProfile.objects.filter(user=user).only("verification_status", "is_listed").first()
    if not tutor_profile:
        return False
    return _normalize_tutor_verification_status(tutor_profile.verification_status) == "approved" and tutor_profile.is_listed


def _google_oauth_config():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    return client_id, client_secret, redirect_uri


def _missing_google_oauth_env():
    required = ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"]
    return [name for name in required if not os.environ.get(name, "").strip()]


def _google_user_from_token_info(token_info: dict, client_id: str, mode: str, role: str):
    if str(token_info.get("aud", "")).strip() != client_id:
        return None, "google_audience_mismatch"
    if str(token_info.get("email_verified", "")).strip().lower() not in {"true", "1"}:
        return None, "email_not_verified"

    email = str(token_info.get("email", "")).strip().lower()
    if not email:
        return None, "google_email_missing"

    full_name = str(token_info.get("name") or token_info.get("given_name") or email.split("@")[0]).strip()
    display_name = full_name.split()[0].capitalize() if full_name else email.split("@")[0]
    user = AppUser.objects.filter(email=email).first()

    if mode == "login":
        if not user:
            return None, "account_not_found"
    elif user and user.role != role:
        return None, "account_role_mismatch"
    elif not user:
        user = AppUser.objects.create_user(
            email=email,
            password=secrets.token_urlsafe(24),
            role=role,
            display_name=display_name,
            timezone="UTC",
            full_name=full_name or display_name,
            is_verified=True,
        )

    update_fields = []
    if not user.is_verified:
        user.is_verified = True
        update_fields.append("is_verified")
    if not user.full_name and full_name:
        user.full_name = full_name
        update_fields.append("full_name")
    if not user.display_name and display_name:
        user.display_name = display_name
        update_fields.append("display_name")
    if update_fields:
        user.save(update_fields=update_fields)

    _ensure_tutor_profile(user)
    return user, None


def _google_popup_origin(request) -> str | None:
    origin = request.headers.get("Origin", "").strip().rstrip("/")
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.netloc or parsed.path not in {"", "/"}:
        return None

    configured_origins = {
        str(value).strip().rstrip("/")
        for value in getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        if str(value).strip()
    }
    configured_origins.add(settings.WEB_PUBLIC_URL.rstrip("/"))
    web_public_url = os.environ.get("WEB_PUBLIC_URL", "").strip().rstrip("/")
    if web_public_url:
        configured_origins.add(web_public_url)
    return origin if origin in configured_origins else None


def _encode_google_state(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{raw}.{signature}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii")


def _decode_google_state(state: str):
    try:
        decoded = base64.urlsafe_b64decode(state.encode("ascii")).decode("utf-8")
        raw, signature = decoded.rsplit(".", 1)
    except Exception:
        return None
    expected = hmac.new(settings.SECRET_KEY.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    exp = payload.get("exp")
    if isinstance(exp, int) and exp < int(time.time()):
        return None
    return payload


def _http_json(url: str, data: bytes | None = None, headers: dict | None = None):
    req = Request(url, data=data, headers=headers or {})
    with urlopen(req, timeout=20) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def _signup_path(role: str) -> str:
    return "/signup/tutor" if role == "tutor" else "/signup"


def _redirect_signup_error(role: str, reason: str):
    target = f"{_frontend_base_url()}{_signup_path(role)}?{urlencode({'error': reason})}"
    return HttpResponseRedirect(target)


def _redirect_login_error(reason: str):
    target = f"{_frontend_base_url()}/login?{urlencode({'error': reason})}"
    return HttpResponseRedirect(target)

def _is_student_verified(user: AppUser) -> bool:
    """Check if a student user is verified and can contact tutors"""
    if user.role != "student":
        return True  # Non-students are not restricted
    try:
        verification = user.student_verification
        return verification.status == "approved"
    except StudentVerificationRequest.DoesNotExist:
        return False


def _serialize_tutor_card(
    tutor: TutorProfile,
    ratings: dict,
    review_counts: dict,
    is_favorited: bool = False,
):
    verification = None
    try:
        verification = tutor.verificationrequest
    except VerificationRequest.DoesNotExist:
        verification = None

    return {
        "id": str(tutor.id),
        "displayName": tutor.user.display_name,
        "headline": tutor.headline,
        "bio": tutor.bio,
        "subjects": tutor.subjects_csv.split(",") if tutor.subjects_csv else [],
        "hourlyRate": float(tutor.hourly_rate_cents) / 100 if tutor.hourly_rate_cents else None,
        "profilePhotoUrl": _resolve_tutor_photo_url(tutor, verification),
        "averageRating": ratings.get(tutor.id, 0),
        "totalReviews": review_counts.get(tutor.id, 0),
        "timezone": tutor.user.timezone,
        "location": tutor.home_state or tutor.home_city or tutor.user.timezone,
        "verificationStatus": _normalize_tutor_verification_status(tutor.verification_status),
        "nextAvailableAt": None,
        "isFavorited": is_favorited,
        "firstLessonFree": tutor.first_lesson_free,
        "teachingModes": _tutor_teaching_modes(tutor),
        "videoCallUrl": _tutor_video_call_url(tutor),
    }


def _normalize_public_media_url(value: str) -> str:
    normalized = value.strip()
    public_endpoint = str(
        getattr(settings, "AWS_S3_PUBLIC_ENDPOINT_URL", "") or ""
    ).strip().rstrip("/")
    if not public_endpoint:
        return normalized

    public = urlparse(public_endpoint)
    parsed = urlparse(normalized)
    if not public.scheme or not public.netloc:
        return normalized

    internal_endpoint = str(
        getattr(settings, "AWS_S3_ENDPOINT_URL", "") or ""
    ).strip().rstrip("/")
    internal = urlparse(internal_endpoint)
    if parsed.netloc == public.netloc:
        return parsed._replace(scheme=public.scheme).geturl()
    if internal.netloc and parsed.netloc == internal.netloc:
        return parsed._replace(
            scheme=public.scheme,
            netloc=public.netloc,
        ).geturl()
    return normalized


def _resolve_tutor_photo_url(tutor: TutorProfile, verification: VerificationRequest | None = None) -> str:
    candidates = [
        tutor.profile_photo_url,
        tutor.user.profile_photo_url,
    ]
    if verification is not None:
        candidates.append(verification.profile_photo_url)

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return _normalize_public_media_url(candidate)
    return ""


def health(request):
    return JsonResponse({"ok": True, "timestamp": timezone.now().isoformat()})


def api_root(request):
    return JsonResponse(
        {
            "ok": True,
            "service": "api",
            "health": "/api/health",
            "ready": "/api/health/ready",
            "timestamp": timezone.now().isoformat(),
        }
    )


def health_live(request):
    return JsonResponse({"ok": True, "service": "api", "timestamp": timezone.now().isoformat()})


def health_ready(request):
    required_tables = {
        "core_appuser",
        "core_tutorprofile",
        "core_pendingsignupchallenge",
    }

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            existing_tables = set(connections["default"].introspection.table_names(cursor))
            missing_tables = sorted(required_tables - existing_tables)
            if missing_tables:
                return JsonResponse(
                    {"ok": False, "error": "schema_incomplete", "missingTables": missing_tables},
                    status=503,
                )
    except Exception as exc:
        logger.exception("Readiness check failed")
        return JsonResponse({"ok": False, "error": str(exc)}, status=503)

    return JsonResponse({"ok": True, "service": "api", "timestamp": timezone.now().isoformat()})

@api_view(["GET"])
@permission_classes([AllowAny])
def tutor_reviews(request, tutor_id):
    tp = TutorProfile.objects.filter(id=tutor_id).first()
    if not tp:
        return _bad_request("Tutor not found", status=404)
    reviews = Review.objects.filter(tutor_profile=tp).order_by("-created_at")[:50]
    data = [{"id": str(r.id), "rating": r.rating, "comment": r.comment, "studentName": r.student_user.display_name, "createdAt": r.created_at.isoformat()} for r in reviews]
    return JsonResponse({"results": data})

@api_view(["GET"])
@permission_classes([AllowAny])
def tutor_review_summary(request, tutor_id):
    parsed_tutor_id = _parse_uuid_or_none(tutor_id)
    if not parsed_tutor_id:
        return _bad_request("Tutor not found", status=404)
    tp = TutorProfile.objects.filter(id=parsed_tutor_id).first()
    if not tp:
        return _bad_request("Tutor not found", status=404)
    reviews = Review.objects.filter(tutor_profile=tp)
    avg = reviews.aggregate(avg=Avg("rating"))["avg"] or 0
    counts = {1: reviews.filter(rating=1).count(), 2: reviews.filter(rating=2).count(), 3: reviews.filter(rating=3).count(), 4: reviews.filter(rating=4).count(), 5: reviews.filter(rating=5).count()}
    return JsonResponse({"averageRating": round(avg, 1), "totalReviews": reviews.count(), "ratingCounts": counts})

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def submit_review(request, booking_id):
    user: AppUser = request.user
    b = Booking.objects.filter(id=booking_id, student_user=user, status="completed").first()
    if not b:
        return _bad_request("Booking not found or not completed", status=404)
    if Review.objects.filter(booking=b).exists():
        return _bad_request("Review already submitted for this booking", status=400)
    rating = request.data.get("rating")
    comment = request.data.get("comment")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return _bad_request("Rating must be an integer between 1 and 5")
    Review.objects.create(tutor_profile=b.tutor_profile, student_user=user, booking=b, rating=rating, comment=comment if isinstance(comment, str) else None)
    return JsonResponse({"ok": True})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_reviews(request):
    user: AppUser = request.user
    if user.role == "student":
        reviews = Review.objects.filter(student_user=user).order_by("-created_at")
    elif user.role == "tutor":
        reviews = Review.objects.filter(tutor_profile__user=user).order_by("-created_at")
    else:
        reviews = Review.objects.order_by("-created_at")
    data = [{"id": str(r.id), "rating": r.rating, "comment": r.comment, "tutorId": str(r.tutor_profile_id), "tutorName": r.tutor_profile.user.display_name, "studentId": str(r.student_user_id), "studentName": r.student_user.display_name, "createdAt": r.created_at.isoformat()} for r in reviews]
    return JsonResponse({"results": data})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload(request):
    from django.core.files.storage import default_storage
    file = request.FILES.get("file")
    if not file:
        return _bad_request("No file provided")

    user: AppUser = request.user
    if user.role not in {"student", "tutor"}:
        return _bad_request("Unsupported role", status=403)

    kind = request.data.get("kind", "photo")
    if kind not in {"photo", "id_document", "qualification_document", "additional_document"}:
        return _bad_request("Invalid kind")

    def safe_part(value: str, fallback: str) -> str:
        v = (value or "").strip().lower()
        v = re.sub(r"\s+", "_", v)
        v = re.sub(r"[^a-z0-9_]+", "_", v)
        v = re.sub(r"_+", "_", v).strip("_")
        return v or fallback

    orig_name = os.path.basename(getattr(file, "name", "") or "file")
    _, ext = os.path.splitext(orig_name)
    ext = safe_part(ext.lstrip("."), "bin")

    full_name = (user.full_name or "").strip()
    parts = [p for p in re.split(r"\s+", full_name) if p]
    first_name = parts[0] if parts else (user.display_name or "user")
    last_name = parts[-1] if len(parts) > 1 else "user"
    first_part = safe_part(first_name, "user")
    last_part = safe_part(last_name, "user")

    prefix = "photo"
    if kind == "id_document":
        prefix = "id"
    elif kind == "qualification_document":
        prefix = "qualification"
    elif kind == "additional_document":
        prefix = "additional"

    stable_id = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        str(user.id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:32]
    filename = f"{prefix}_{first_part}_{last_part}_{stable_id}.{ext}"

    folder = "tutors" if user.role == "tutor" else "students"
    subfolder = "documents" if kind == "additional_document" else "images"
    path = default_storage.save(f"{subfolder}/{folder}/{filename}", file)
    url = _normalize_public_media_url(default_storage.url(path))
    return JsonResponse(
        {
            "url": url,
            "name": filename,
            "contentType": getattr(file, "content_type", None),
            "size": getattr(file, "size", None),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def auth_google_start(request):
    mode = (request.GET.get("mode") or "signup").strip().lower()
    if mode not in {"signup", "login"}:
        return _bad_request("Mode must be signup or login")

    role = (request.GET.get("role") or "tutor").strip().lower()
    if role not in {"student", "tutor"}:
        return _bad_request("Role must be student or tutor")

    client_id, client_secret, redirect_uri = _google_oauth_config()
    missing_env = _missing_google_oauth_env()
    if missing_env:
        return JsonResponse(
            {
                "error": "Google SSO is not configured",
                "missing": missing_env,
            },
            status=503,
        )
    if not redirect_uri:
        redirect_uri = request.build_absolute_uri("/api/auth/google/callback")

    state_payload = {
        "mode": mode,
        "exp": int(time.time()) + 600,
    }
    if mode == "signup":
        state_payload["role"] = role
    state = _encode_google_state(state_payload)
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "consent select_account",
            "include_granted_scopes": "true",
        }
    )
    return JsonResponse({
        "clientId": client_id,
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}",
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def auth_google_callback(request):
    code = request.GET.get("code")
    state_raw = request.GET.get("state")
    state = _decode_google_state(state_raw) if state_raw else None
    mode = state.get("mode") if isinstance(state, dict) and state.get("mode") in {"signup", "login"} else "signup"
    role = state.get("role") if isinstance(state, dict) and state.get("role") in {"student", "tutor"} else "tutor"
    if not code:
        if mode == "login":
            return _redirect_login_error("google_auth_failed")
        return _redirect_signup_error(role, "google_auth_failed")
    if not state:
        if mode == "login":
            return _redirect_login_error("invalid_state")
        return _redirect_signup_error(role, "invalid_state")

    client_id, client_secret, redirect_uri = _google_oauth_config()
    if not client_id or not client_secret:
        if mode == "login":
            return _redirect_login_error("google_not_configured")
        return _redirect_signup_error(role, "google_not_configured")
    if not redirect_uri:
        redirect_uri = request.build_absolute_uri("/api/auth/google/callback")

    try:
        token_payload = urlencode(
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        token_data = _http_json(
            "https://oauth2.googleapis.com/token",
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        id_token = token_data.get("id_token")
        if not isinstance(id_token, str) or not id_token.strip():
            if mode == "login":
                return _redirect_login_error("google_token_missing")
            return _redirect_signup_error(role, "google_token_missing")

        token_info = _http_json(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={quote(id_token)}"
        )
    except Exception:
        if mode == "login":
            return _redirect_login_error("google_auth_failed")
        return _redirect_signup_error(role, "google_auth_failed")

    user, error_code = _google_user_from_token_info(token_info, client_id, mode, role)
    if error_code:
        if mode == "login":
            return _redirect_login_error(error_code)
        return _redirect_signup_error(role, error_code)

    auth_payload = _auth_response(user)
    callback_query = urlencode(
        {
            "accessToken": auth_payload["accessToken"],
            "refreshToken": auth_payload["refreshToken"],
            "userId": str(user.id),
            "role": user.role,
            "displayName": user.display_name,
            "redirectTo": auth_payload["defaultDashboardPath"],
        }
    )
    return HttpResponseRedirect(f"{_frontend_base_url()}/auth/google/callback?{callback_query}")


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_google_exchange(request):
    mode = str(request.data.get("mode") or "signup").strip().lower()
    if mode not in {"signup", "login"}:
        return _bad_request("Mode must be signup or login")

    role = str(request.data.get("role") or "tutor").strip().lower()
    if role not in {"student", "tutor"}:
        return _bad_request("Role must be student or tutor")

    code = str(request.data.get("code") or "").strip()
    if not code:
        return _bad_request("google_token_missing")
    if request.headers.get("X-Requested-With") != "XmlHttpRequest":
        return _bad_request("google_auth_failed", status=403)

    origin = _google_popup_origin(request)
    if not origin:
        return _bad_request("google_auth_failed", status=403)

    client_id, client_secret, _ = _google_oauth_config()
    if not client_id or not client_secret:
        return _bad_request("google_not_configured", status=503)

    try:
        token_payload = urlencode(
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": origin,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        token_data = _http_json(
            "https://oauth2.googleapis.com/token",
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        id_token = token_data.get("id_token")
        if not isinstance(id_token, str) or not id_token.strip():
            return _bad_request("google_token_missing")
        token_info = _http_json(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={quote(id_token)}"
        )
    except Exception:
        logger.exception("Google popup authorization code exchange failed")
        return _bad_request("google_auth_failed")

    user, error_code = _google_user_from_token_info(token_info, client_id, mode, role)
    if error_code:
        return _bad_request(error_code)
    return JsonResponse(_auth_response(user))


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    email = request.data.get("email")
    password = request.data.get("password")
    role = request.data.get("role")
    full_name = request.data.get("fullName")
    first_name = request.data.get("firstName")
    middle_name = request.data.get("middleName")
    last_name = request.data.get("lastName")
    
    if not isinstance(email, str) or not email.strip():
        return _bad_request("Email is required")
    if not isinstance(password, str) or len(password) < 6:
        return _bad_request("Password must be at least 6 characters")
    if role not in {"student", "tutor"}:
        return _bad_request("Role must be student or tutor")
    if role == "tutor" and any(value is not None for value in (first_name, middle_name, last_name)):
        if not isinstance(first_name, str) or not first_name.strip() or not isinstance(last_name, str) or not last_name.strip():
            return _bad_request("First name and last name are required")
        normalized_full_name = _compose_full_name(first_name, middle_name, last_name)
    else:
        if not isinstance(full_name, str) or not full_name.strip():
            return _bad_request("Full name is required")
        normalized_full_name = full_name.strip()

    normalized = email.strip().lower()
    user = AppUser.objects.filter(email=normalized).first()

    if user:
        if user.role != role:
            return _bad_request("Email already registered with a different account type")
        if user.is_verified:
            return _bad_request("Email already registered")
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())

    if not _issue_pending_signup_code(
        email=normalized,
        role=role,
        full_name=normalized_full_name,
        password=password,
    ):
        return _bad_request("We could not send the verification code right now. Please try again.", status=503)

    return JsonResponse({"message": "OTP sent", "pendingEmail": normalized})

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get("email")
    otp = request.data.get("otp")
    if not isinstance(email, str) or not email.strip():
        return _bad_request("Email is required")
    if not isinstance(otp, str) or len(otp) != 6:
        return _bad_request("OTP must be 6 characters")
    
    normalized_code = otp.strip().upper()
    normalized_email = email.strip().lower()

    pending = PendingSignupChallenge.objects.filter(
        email=normalized_email,
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).order_by("-created_at").first()
    if pending:
        if pending.attempts >= 5:
            return _bad_request("Too many attempts. Request a new code.", status=429)
        digest = hashlib.sha256((settings.SECRET_KEY + pending.code_salt + normalized_code).encode("utf-8")).hexdigest()
        if not hmac.compare_digest(digest, pending.code_hash):
            pending.attempts += 1
            pending.save(update_fields=["attempts"])
            return _bad_request("Invalid or expired code")

        display_name = pending.full_name.split()[0].capitalize() if pending.full_name else ""
        with transaction.atomic():
            user = AppUser.objects.filter(email=normalized_email).first()
            if user:
                if user.is_verified:
                    PendingSignupChallenge.objects.filter(email=normalized_email, used_at__isnull=True).update(used_at=timezone.now())
                    return _bad_request("Email already registered")
                if user.role != pending.role:
                    PendingSignupChallenge.objects.filter(email=normalized_email, used_at__isnull=True).update(used_at=timezone.now())
                    return _bad_request("Email already registered with a different account type")
                user.password = pending.password_hash
                user.role = pending.role
                user.full_name = pending.full_name
                user.display_name = display_name
                user.timezone = user.timezone or "UTC"
                user.is_verified = True
                user.is_active = True
                user.save(
                    update_fields=[
                        "password",
                        "role",
                        "full_name",
                        "display_name",
                        "timezone",
                        "is_verified",
                        "is_active",
                    ]
                )
            else:
                user = AppUser.objects.create(
                    email=normalized_email,
                    password=pending.password_hash,
                    role=pending.role,
                    display_name=display_name,
                    timezone="UTC",
                    full_name=pending.full_name,
                    is_verified=True,
                    is_active=True,
                )

            _ensure_tutor_profile(user)
            PendingSignupChallenge.objects.filter(email=normalized_email, used_at__isnull=True).update(used_at=timezone.now())
            PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        return JsonResponse(_auth_response(user))

    user = AppUser.objects.filter(email=normalized_email).first()
    if not user:
        return _bad_request("Invalid or expired code")
    if user.is_verified:
        return _bad_request("Invalid or expired code")

    token = PasswordResetToken.objects.filter(user=user, used_at__isnull=True, expires_at__gt=timezone.now()).order_by("-created_at").first()
    if not token:
        return _bad_request("Invalid or expired code")
    digest = hashlib.sha256((settings.SECRET_KEY + token.code_salt + normalized_code).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(digest, token.code_hash):
        return _bad_request("Invalid or expired code")

    with transaction.atomic():
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())

    return JsonResponse(_auth_response(user))

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get("email")
    password = request.data.get("password")
    if not isinstance(email, str) or not email.strip():
        return _bad_request("Email is required")
    if not isinstance(password, str) or len(password) < 6:
        return _bad_request("Invalid credentials")
    user = AppUser.objects.filter(email=email.strip().lower()).first()
    if not user or not user.check_password(password):
        return _bad_request("Invalid credentials", status=401)
    if not user.is_verified:
        return _bad_request("Email not verified. Please check your email for OTP.", status=403)

    payload = _auth_response(user)
    payload["user"]["isVerified"] = user.is_verified
    return JsonResponse(payload)

@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_auth_token(request):
    from rest_framework_simplejwt.tokens import RefreshToken, TokenError

    refresh_token = str(request.data.get("refreshToken") or request.data.get("refresh") or "").strip()
    if not refresh_token:
        return _bad_request("Refresh token is required")

    try:
        refresh = RefreshToken(refresh_token)
    except TokenError:
        return _invalid_token_response("Refresh token is invalid or expired")

    return JsonResponse({
        "accessToken": str(refresh.access_token),
        "refreshToken": str(refresh),
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    return JsonResponse({"ok": True})

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = request.data.get("email")
    if not isinstance(email, str) or not email.strip():
        return _bad_request("Email is required")
    normalized = email.strip().lower()
    user = AppUser.objects.filter(email=normalized).first()
    if not user:
        logger.warning("Password reset requested for unknown email=%s", normalized)
        payload = {"ok": True}
        if settings.DEBUG:
            payload["sent"] = False
            payload["email"] = normalized
        return JsonResponse(payload)
    otp = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((settings.SECRET_KEY + salt + otp).encode("utf-8")).hexdigest()
    expires_at = timezone.now() + timedelta(minutes=15)
    PasswordResetToken.objects.create(user=user, code_salt=salt, code_hash=digest, expires_at=expires_at)
    subject = "Password reset code"
    message = f"Use the code below to reset your password:\n\n{otp}\n\nThis code expires in 15 minutes.\n"
    sent = _send_email(subject, message, [user.email])
    if not sent:
        logger.error("Password reset email failed for email=%s", normalized)
    payload = {"ok": True}
    if settings.DEBUG:
        payload["sent"] = sent
        payload["email"] = normalized
    return JsonResponse(payload)

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    email = request.data.get("email")
    code = request.data.get("code")
    new_password = request.data.get("newPassword")
    if not isinstance(email, str) or not email.strip():
        return _bad_request("Email is required")
    if not isinstance(code, str) or not code.strip():
        return _bad_request("Code is required")
    if not isinstance(new_password, str) or len(new_password) < 6:
        return _bad_request("Password must be at least 6 characters")
    user = AppUser.objects.filter(email=email.strip().lower()).first()
    if not user:
        return _bad_request("Invalid or expired code")
    token = PasswordResetToken.objects.filter(user=user, used_at__isnull=True, expires_at__gt=timezone.now()).order_by("-created_at").first()
    if not token:
        return _bad_request("Invalid or expired code")
    if token.attempts >= 5:
        return _bad_request("Too many attempts. Request a new code.", status=429)
    normalized_code = code.strip().upper()
    digest = hashlib.sha256((settings.SECRET_KEY + token.code_salt + normalized_code).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(digest, token.code_hash):
        token.attempts += 1
        token.save(update_fields=["attempts"])
        return _bad_request("Invalid or expired code")
    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    return JsonResponse({"ok": True})

@api_view(["GET"])
@permission_classes([AllowAny])
def tutor_detail(request, tutor_id):
    parsed_tutor_id = _parse_uuid_or_none(tutor_id)
    if not parsed_tutor_id:
        return _bad_request("Tutor not found", status=404)
    tp = TutorProfile.objects.filter(
        id=parsed_tutor_id,
        is_listed=True,
        verification_status__in=APPROVED_TUTOR_STATUSES,
    ).select_related("user").first()
    if not tp:
        return _bad_request("Tutor not found", status=404)
    
    # Get availability
    availability = AvailabilitySlot.objects.filter(tutor_profile=tp, starts_at__gt=timezone.now()).order_by("starts_at")[:50]
    
    # Get rating summary
    reviews = Review.objects.filter(tutor_profile=tp)
    avg_rating = reviews.aggregate(avg=Avg("rating"))["avg"] or 0
    total_reviews = reviews.count()
    
    data = {
        "tutor": {
            "id": str(tp.id),
            "displayName": tp.user.display_name,
            "headline": tp.headline,
            "bio": tp.bio,
            "subjects": tp.subjects_csv.split(",") if tp.subjects_csv else [],
            "hourlyRate": float(tp.hourly_rate_cents) / 100 if tp.hourly_rate_cents else None,
            "profilePhotoUrl": _resolve_tutor_photo_url(tp),
            "verificationStatus": _normalize_tutor_verification_status(tp.verification_status),
            "location": tp.home_state or tp.home_city,
            "timezone": tp.user.timezone,
            "averageRating": round(avg_rating, 1),
            "totalReviews": total_reviews,
            "languages": tp.languages_csv.split(",") if tp.languages_csv else [],
            "responseTime": tp.response_time,
            "firstLessonFree": tp.first_lesson_free,
            "teachingModes": _tutor_teaching_modes(tp),
            "videoCallUrl": _tutor_video_call_url(tp),
        },
        "availability": [{
            "id": str(s.id),
            "startsAt": s.starts_at.isoformat(),
            "endsAt": s.ends_at.isoformat(),
        } for s in availability],
        "averageRating": round(avg_rating, 1),
        "totalReviews": total_reviews,
    }
    return JsonResponse(data)

@api_view(["GET"])
@permission_classes([AllowAny])
def tutors_list(request):
    tutors = TutorProfile.objects.filter(
        is_listed=True,
        verification_status__in=APPROVED_TUTOR_STATUSES,
    ).select_related("user")
    
    # Apply filters
    q = request.GET.get('q', '').strip()
    state = request.GET.get('state', '').strip()
    location = request.GET.get('location', '').strip()
    minRate = request.GET.get('minRate', '').strip()
    maxRate = request.GET.get('maxRate', '').strip()
    qualification = request.GET.get('qualification', '').strip()
    gender = request.GET.get('gender', '').strip()
    language = request.GET.get('language', '').strip()
    
    if q:
        tutors = tutors.filter(
            Q(headline__icontains=q) | 
            Q(bio__icontains=q) | 
            Q(subjects_csv__icontains=q) | 
            Q(user__display_name__icontains=q) | 
            Q(home_city__icontains=q) | 
            Q(home_state__icontains=q)
        )
    
    if state:
        tutors = tutors.filter(
            Q(home_state__icontains=state) | 
            Q(user__state__icontains=state)
        )
    
    if location:
        tutors = tutors.filter(
            Q(home_city__icontains=location) | 
            Q(user__location__icontains=location)
        )
    
    if minRate:
        try:
            min_rate_cents = float(minRate) * 100
            tutors = tutors.filter(hourly_rate_cents__gte=min_rate_cents)
        except ValueError:
            pass
    
    if maxRate:
        try:
            max_rate_cents = float(maxRate) * 100
            tutors = tutors.filter(hourly_rate_cents__lte=max_rate_cents)
        except ValueError:
            pass
    
    if qualification:
        tutors = tutors.filter(
            Q(verificationrequest__qualification__icontains=qualification)
            | Q(qualification__icontains=qualification)
        )
    
    if gender:
        tutors = tutors.filter(gender__iexact=gender)
    
    if language:
        tutors = tutors.filter(languages_csv__icontains=language)
    
    tutors = list(tutors)
    tutor_ids = [t.id for t in tutors]

    ratings = Review.objects.filter(tutor_profile_id__in=tutor_ids).values("tutor_profile_id").annotate(avg=Avg("rating"), count=Count("id"))
    ratings_dict = {r["tutor_profile_id"]: round(r["avg"], 1) for r in ratings}
    counts_dict = {r["tutor_profile_id"]: int(r["count"]) for r in ratings}

    favorite_ids = set()
    user = request.user
    if getattr(user, "is_authenticated", False) and getattr(user, "role", None) == "student" and tutor_ids:
        favorite_ids = set(
            FavoriteTutor.objects.filter(student_user=user, tutor_profile_id__in=tutor_ids).values_list("tutor_profile_id", flat=True)
        )

    data = [_serialize_tutor_card(t, ratings_dict, counts_dict, is_favorited=t.id in favorite_ids) for t in tutors]
    return JsonResponse({"results": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def my_favorite_tutors(request):
    user: AppUser = request.user
    favorites = (
        FavoriteTutor.objects.filter(
            student_user=user,
            tutor_profile__is_listed=True,
            tutor_profile__verification_status__in=APPROVED_TUTOR_STATUSES,
        )
        .select_related("tutor_profile__user")
        .order_by("-created_at")
    )

    tutors = [item.tutor_profile for item in favorites]
    tutor_ids = [t.id for t in tutors]
    ratings = Review.objects.filter(tutor_profile_id__in=tutor_ids).values("tutor_profile_id").annotate(avg=Avg("rating"), count=Count("id"))
    ratings_dict = {r["tutor_profile_id"]: round(r["avg"], 1) for r in ratings}
    counts_dict = {r["tutor_profile_id"]: int(r["count"]) for r in ratings}

    data = [_serialize_tutor_card(t, ratings_dict, counts_dict, is_favorited=True) for t in tutors]
    return JsonResponse({"results": data})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated, IsStudent])
def favorite_tutor(request, tutor_id):
    user: AppUser = request.user
    parsed_tutor_id = _parse_uuid_or_none(tutor_id)
    if not parsed_tutor_id:
        return _bad_request("Tutor not found", status=404)
    tutor = TutorProfile.objects.filter(
        id=parsed_tutor_id,
        is_listed=True,
        verification_status__in=APPROVED_TUTOR_STATUSES,
    ).first()
    if not tutor:
        return _bad_request("Tutor not found", status=404)

    if request.method == "POST":
        FavoriteTutor.objects.get_or_create(student_user=user, tutor_profile=tutor)
        return JsonResponse({"ok": True, "isFavorited": True})

    FavoriteTutor.objects.filter(student_user=user, tutor_profile=tutor).delete()
    return JsonResponse({"ok": True, "isFavorited": False})

@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def me(request):
    user: AppUser = request.user
    if request.method == "GET":
        first_name, middle_name, last_name = _split_full_name(user.full_name or user.display_name)
        return JsonResponse({
            "id": str(user.id), "email": user.email, "role": user.role, "displayName": user.display_name,
            "timezone": user.timezone, "fullName": user.full_name, "firstName": first_name, "middleName": middle_name, "lastName": last_name, "mobileNumber": user.mobile_number,
            "dateOfBirth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "profilePhotoUrl": user.profile_photo_url, "location": user.location, "city": user.location, "state": user.state, "address": user.address,
            "isVerified": user.is_verified, "isFrozen": user.is_frozen,
            "freezeUntil": user.frozen_until.isoformat() if user.frozen_until else None,
            "isPendingDeletion": user.is_pending_deletion,
            "defaultDashboardPath": _default_dashboard_path(user),
        })
    display_name = request.data.get("displayName")
    full_name = request.data.get("fullName")
    timezone_str = request.data.get("timezone")
    profile_photo_url = request.data.get("profilePhotoUrl")
    mobile_number = request.data.get("mobileNumber")
    date_of_birth = request.data.get("dateOfBirth")
    state = request.data.get("state")
    address = request.data.get("address")
    location = request.data.get("location")
    city = request.data.get("city")

    if user.role == "tutor":
        tutor_profile = TutorProfile.objects.filter(user=user).first()
        if (
            tutor_profile
            and _normalize_tutor_verification_status(tutor_profile.verification_status) == "approved"
            and tutor_profile.is_listed
        ):
            restricted_user_fields = [
                full_name,
                timezone_str,
                profile_photo_url,
                mobile_number,
                date_of_birth,
            ]
            if any(value is not None for value in restricted_user_fields):
                return _bad_request(
                    "Only approved tutor display names and home location fields can be updated here",
                    status=403,
                )
    
    if not isinstance(display_name, str) or not display_name.strip():
        return _bad_request("Display name is required")
    
    # Timezone is now optional since we have separate location fields
    # if not isinstance(timezone_str, str) or not timezone_str.strip():
    #     return _bad_request("Timezone is required")
    
    user.display_name = display_name.strip()
    if full_name is not None:
        if not isinstance(full_name, str) or not full_name.strip():
            return _bad_request("Full name is required")
        user.full_name = full_name.strip()
    if timezone_str:
        user.timezone = timezone_str.strip()
    
    if profile_photo_url is not None:
        user.profile_photo_url = profile_photo_url.strip()
    
    if mobile_number is not None:
        try:
            normalized_mobile_number = _normalize_mobile_number(mobile_number, required=False)
        except ValueError as exc:
            return _bad_request(str(exc))
        user.mobile_number = normalized_mobile_number or ""
    
    if date_of_birth is not None:
        if date_of_birth.strip():
            user.date_of_birth = _parse_dt(date_of_birth.strip())
        else:
            user.date_of_birth = None
    
    if address is not None:
        user.address = address.strip()
    
    if state is not None:
        user.state = state.strip()
    
    if location is not None:
        user.location = location.strip()
    elif city is not None:
        user.location = city.strip()
    
    user.save(update_fields=["display_name", "full_name", "timezone", "profile_photo_url", "mobile_number", "date_of_birth", "location", "state", "address"])
    
    first_name, middle_name, last_name = _split_full_name(user.full_name or user.display_name)
    return JsonResponse({
        "id": str(user.id), "email": user.email, "role": user.role, "displayName": user.display_name, 
        "timezone": user.timezone, "fullName": user.full_name, "firstName": first_name, "middleName": middle_name, "lastName": last_name, "mobileNumber": user.mobile_number, 
        "dateOfBirth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        "profilePhotoUrl": user.profile_photo_url, "location": user.location, "city": user.location, "state": user.state, "address": user.address,
        "isVerified": user.is_verified, "isFrozen": user.is_frozen,
        "freezeUntil": user.frozen_until.isoformat() if user.frozen_until else None,
        "isPendingDeletion": user.is_pending_deletion,
        "defaultDashboardPath": _default_dashboard_path(user),
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def account_delete_request(request):
    action = request.data.get("action")
    freeze_months = request.data.get("freezeMonths", 0)
    confirm_delete = request.data.get("confirmDelete", False)
    
    user: AppUser = request.user
    
    if action == "freeze":
        months = min(int(freeze_months) if freeze_months else 1, 3)
        frozen_until = timezone.now() + timedelta(days=30 * months)
        user.is_frozen = True
        user.frozen_until = frozen_until
        user.is_pending_deletion = False
        user.deletion_scheduled_at = None
        user.save()
        if hasattr(user, 'tutor_profile'):
            tp = user.tutor_profile
            tp.is_listed = False
            tp.save()
        return JsonResponse({"ok": True, "message": f"Account frozen for {months} month(s).", "frozenUntil": frozen_until.isoformat()})
    
    elif action == "delete":
        if not confirm_delete:
            return _bad_request("Please confirm you want to delete your account")
        user.is_pending_deletion = True
        user.deletion_scheduled_at = timezone.now() + timedelta(days=30)
        user.save()
        return JsonResponse({"ok": True, "message": "Account scheduled for deletion in 30 days."})

    return _bad_request("Invalid action")


def _add_months(date_value: dt.date, months: int) -> dt.date:
    month = date_value.month - 1 + months
    year = date_value.year + month // 12
    month = month % 12 + 1
    first_of_next = dt.date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    last_day = first_of_next - dt.timedelta(days=1)
    return dt.date(year, month, min(date_value.day, last_day.day))


def _extract_storage_path(url: str) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    raw = url.strip()
    if raw.startswith(settings.MEDIA_URL):
        return raw[len(settings.MEDIA_URL):].lstrip("/")
    try:
        from urllib.parse import urlparse

        parsed = urlparse(raw)
        if parsed.path.startswith(settings.MEDIA_URL):
            return parsed.path[len(settings.MEDIA_URL):].lstrip("/")
    except Exception:
        return None
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def freeze_account_request(request):
    user: AppUser = request.user
    if user.role != "tutor":
        return _bad_request("Only tutors can freeze their account", status=403)

    starts_on_raw = request.data.get("startsOn")
    ends_on_raw = request.data.get("endsOn")
    if not isinstance(starts_on_raw, str) or not isinstance(ends_on_raw, str):
        return _bad_request("startsOn and endsOn are required")
    try:
        starts_on = dt.date.fromisoformat(starts_on_raw)
        ends_on = dt.date.fromisoformat(ends_on_raw)
    except Exception:
        return _bad_request("startsOn and endsOn must be YYYY-MM-DD")

    today = timezone.localdate()
    if starts_on < today:
        return _bad_request("Start date must be today or later")
    if ends_on < starts_on:
        return _bad_request("End date must be after start date")
    if ends_on > _add_months(starts_on, 3):
        return _bad_request("Freeze period cannot exceed 3 months")

    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    now = timezone.now()
    AccountFreezeRequest.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    req = AccountFreezeRequest.objects.create(
        user=user,
        starts_on=starts_on,
        ends_on=ends_on,
        code=code,
        expires_at=now + timedelta(minutes=15),
    )

    days = (req.ends_on - req.starts_on).days + 1
    subject = "PrepVilla: Freeze account OTP"
    message = (
        "You requested to freeze your PrepVilla account.\n\n"
        f"Freeze start: {req.starts_on.isoformat()}\n"
        f"Freeze end: {req.ends_on.isoformat()}\n"
        f"Duration: {days} day(s)\n\n"
        f"OTP code: {code}\n\n"
        "This code expires in 15 minutes. If you did not request this, ignore this email.\n"
    )
    sent = _send_email(subject, message, [user.email])
    if not sent:
        return _bad_request("Failed to send OTP email", status=500)

    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def freeze_account_confirm(request):
    user: AppUser = request.user
    if user.role != "tutor":
        return _bad_request("Only tutors can freeze their account", status=403)

    code = request.data.get("code")
    if not isinstance(code, str) or len(code.strip()) != 6:
        return _bad_request("code must be 6 characters")
    normalized = code.strip().upper()

    now = timezone.now()
    req = AccountFreezeRequest.objects.filter(user=user, used_at__isnull=True, expires_at__gt=now).order_by("-created_at").first()
    if not req:
        return _bad_request("No pending freeze request found")
    if req.code != normalized:
        return _bad_request("Invalid OTP")

    freeze_until = timezone.make_aware(dt.datetime.combine(req.ends_on, dt.time.max))
    with transaction.atomic():
        user.is_frozen = True
        user.frozen_until = freeze_until
        user.is_pending_deletion = False
        user.deletion_scheduled_at = None
        user.save(update_fields=["is_frozen", "frozen_until", "is_pending_deletion", "deletion_scheduled_at"])
        req.used_at = now
        req.save(update_fields=["used_at"])
        if hasattr(user, "tutor_profile"):
            tp = user.tutor_profile
            tp.is_listed = False
            tp.save(update_fields=["is_listed"])

    return JsonResponse({"ok": True, "isFrozen": True, "freezeUntil": freeze_until.isoformat()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unfreeze_account(request):
    user: AppUser = request.user
    with transaction.atomic():
        user.is_frozen = False
        user.frozen_until = None
        user.save(update_fields=["is_frozen", "frozen_until"])
        if hasattr(user, "tutor_profile"):
            tp = user.tutor_profile
            if _normalize_tutor_verification_status(tp.verification_status) == "approved":
                tp.is_listed = True
                tp.save(update_fields=["is_listed"])
    return JsonResponse({"ok": True, "isFrozen": False})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_account(request):
    confirm = request.data.get("confirm")
    code = request.data.get("code")
    if confirm is not True:
        return _bad_request("Please confirm you want to delete your account")
    if not isinstance(code, str) or len(code.strip()) != 6:
        return _bad_request("code must be 6 characters")

    user: AppUser = request.user
    now = timezone.now()
    req = AccountDeleteRequest.objects.filter(user=user, used_at__isnull=True, expires_at__gt=now).order_by("-created_at").first()
    if not req:
        return _bad_request("No pending delete request found")
    normalized = code.strip().upper()
    digest = hashlib.sha256((settings.SECRET_KEY + req.code_salt + normalized).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(digest, req.code_hash):
        return _bad_request("Invalid OTP")
    urls: list[str] = []
    if isinstance(user.profile_photo_url, str) and user.profile_photo_url:
        urls.append(user.profile_photo_url)
    if hasattr(user, "tutor_profile"):
        tp = user.tutor_profile
        if isinstance(tp.profile_photo_url, str) and tp.profile_photo_url:
            urls.append(tp.profile_photo_url)
        if isinstance(tp.document_urls, str) and tp.document_urls:
            urls.extend([u.strip() for u in tp.document_urls.split(",") if u.strip()])
        vr = VerificationRequest.objects.filter(tutor_profile=tp).first()
        if vr:
            if isinstance(vr.profile_photo_url, str) and vr.profile_photo_url:
                urls.append(vr.profile_photo_url)
            if isinstance(vr.document_urls, str) and vr.document_urls:
                urls.extend([u.strip() for u in vr.document_urls.split(",") if u.strip()])

    from django.core.files.storage import default_storage
    storage_paths = [p for p in (_extract_storage_path(u) for u in urls) if p]

    with transaction.atomic():
        AccountDeleteRequest.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
        user.delete()

    for p in storage_paths:
        try:
            default_storage.delete(p)
        except Exception:
            logger.exception("Failed to delete media file path=%s", p)

    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_account_request(request):
    user: AppUser = request.user
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((settings.SECRET_KEY + salt + code).encode("utf-8")).hexdigest()
    now = timezone.now()

    AccountDeleteRequest.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    AccountDeleteRequest.objects.create(
        user=user,
        code_salt=salt,
        code_hash=digest,
        expires_at=now + timedelta(minutes=15),
    )

    subject = "PrepVilla: Delete account OTP"
    message = (
        "You requested to permanently delete your PrepVilla account.\n\n"
        f"OTP code: {code}\n\n"
        "This code expires in 15 minutes. If you did not request this, ignore this email.\n"
    )
    sent = _send_email(subject, message, [user.email])
    if not sent:
        return _bad_request("Failed to send OTP email", status=500)
    return JsonResponse({"ok": True})


def _issue_me_otp(user: AppUser, purpose: str, payload: dict, subject: str, message: str):
    if purpose not in {"change_password", "change_email", "change_phone"}:
        return None
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((settings.SECRET_KEY + salt + code).encode("utf-8")).hexdigest()
    now = timezone.now()

    MeOtpChallenge.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=now)
    challenge = MeOtpChallenge.objects.create(
        user=user,
        purpose=purpose,
        payload=json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        code_salt=salt,
        code_hash=digest,
        expires_at=now + timedelta(minutes=15),
    )

    sent = _send_email(subject, message.replace("{OTP}", code), [user.email])
    if not sent:
        MeOtpChallenge.objects.filter(id=challenge.id).update(used_at=now)
        return None
    return challenge


def _consume_me_otp(user: AppUser, purpose: str, code: str) -> MeOtpChallenge | None:
    now = timezone.now()
    challenge = MeOtpChallenge.objects.filter(
        user=user, purpose=purpose, used_at__isnull=True, expires_at__gt=now
    ).order_by("-created_at").first()
    if not challenge:
        return None
    normalized = code.strip().upper()
    digest = hashlib.sha256((settings.SECRET_KEY + challenge.code_salt + normalized).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(digest, challenge.code_hash):
        return None
    challenge.used_at = now
    challenge.save(update_fields=["used_at"])
    return challenge


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_request(request):
    user: AppUser = request.user
    new_password = request.data.get("newPassword")
    if not isinstance(new_password, str) or len(new_password) < 6:
        return _bad_request("Password must be at least 6 characters")
    subject = "PrepVilla: Change password OTP"
    message = (
        "You requested to change your PrepVilla password.\n\n"
        "OTP code: {OTP}\n\n"
        "This code expires in 15 minutes. If you did not request this, ignore this email.\n"
    )
    challenge = _issue_me_otp(user, "change_password", {"newPassword": new_password}, subject, message)
    if not challenge:
        return _bad_request("Failed to send OTP email", status=500)
    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_confirm(request):
    user: AppUser = request.user
    code = request.data.get("code")
    if not isinstance(code, str) or len(code.strip()) != 6:
        return _bad_request("code must be 6 characters")
    challenge = _consume_me_otp(user, "change_password", code)
    if not challenge:
        return _bad_request("Invalid or expired code")
    try:
        payload = json.loads(challenge.payload or "{}")
    except Exception:
        return _bad_request("Invalid or expired code")
    new_password = payload.get("newPassword")
    if not isinstance(new_password, str) or len(new_password) < 6:
        return _bad_request("Invalid or expired code")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_email_request(request):
    user: AppUser = request.user
    if _is_approved_listed_tutor(user):
        return _bad_request("Approved tutor email changes require support assistance", status=403)
    new_email = request.data.get("newEmail")
    if not isinstance(new_email, str) or not new_email.strip():
        return _bad_request("Email is required")
    normalized = new_email.strip().lower()
    if normalized == user.email:
        return _bad_request("Email is unchanged")
    if AppUser.objects.filter(email=normalized).exists():
        return _bad_request("Email already registered")
    subject = "PrepVilla: Change email OTP"
    message = (
        "You requested to change your PrepVilla email.\n\n"
        f"New email: {normalized}\n"
        "OTP code: {OTP}\n\n"
        "This code expires in 15 minutes. If you did not request this, ignore this email.\n"
    )
    challenge = _issue_me_otp(user, "change_email", {"newEmail": normalized}, subject, message)
    if not challenge:
        return _bad_request("Failed to send OTP email", status=500)
    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_email_confirm(request):
    user: AppUser = request.user
    if _is_approved_listed_tutor(user):
        return _bad_request("Approved tutor email changes require support assistance", status=403)
    code = request.data.get("code")
    if not isinstance(code, str) or len(code.strip()) != 6:
        return _bad_request("code must be 6 characters")
    challenge = _consume_me_otp(user, "change_email", code)
    if not challenge:
        return _bad_request("Invalid or expired code")
    try:
        payload = json.loads(challenge.payload or "{}")
    except Exception:
        return _bad_request("Invalid or expired code")
    new_email = payload.get("newEmail")
    if not isinstance(new_email, str) or not new_email.strip():
        return _bad_request("Invalid or expired code")
    normalized = new_email.strip().lower()
    if AppUser.objects.filter(email=normalized).exclude(id=user.id).exists():
        return _bad_request("Email already registered")
    user.email = normalized
    user.save(update_fields=["email"])
    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_phone_request(request):
    user: AppUser = request.user
    if _is_approved_listed_tutor(user):
        return _bad_request("Approved tutor phone changes require support assistance", status=403)
    new_phone = request.data.get("newPhone")
    try:
        normalized = _normalize_mobile_number(new_phone, required=True)
    except ValueError as exc:
        return _bad_request(str(exc))
    if normalized == (user.mobile_number or ""):
        return _bad_request("Phone number is unchanged")
    subject = "PrepVilla: Change phone number OTP"
    message = (
        "You requested to change your PrepVilla phone number.\n\n"
        f"New phone: {normalized}\n"
        "OTP code: {OTP}\n\n"
        "This code expires in 15 minutes. If you did not request this, ignore this email.\n"
    )
    challenge = _issue_me_otp(user, "change_phone", {"newPhone": normalized}, subject, message)
    if not challenge:
        return _bad_request("Failed to send OTP email", status=500)
    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_phone_confirm(request):
    user: AppUser = request.user
    if _is_approved_listed_tutor(user):
        return _bad_request("Approved tutor phone changes require support assistance", status=403)
    code = request.data.get("code")
    if not isinstance(code, str) or len(code.strip()) != 6:
        return _bad_request("code must be 6 characters")
    challenge = _consume_me_otp(user, "change_phone", code)
    if not challenge:
        return _bad_request("Invalid or expired code")
    try:
        payload = json.loads(challenge.payload or "{}")
    except Exception:
        return _bad_request("Invalid or expired code")
    new_phone = payload.get("newPhone")
    try:
        normalized_phone = _normalize_mobile_number(new_phone, required=True)
    except ValueError:
        return _bad_request("Invalid or expired code")
    user.mobile_number = normalized_phone
    user.save(update_fields=["mobile_number"])
    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTutor])
def support_contact(request):
    user: AppUser = request.user
    subject = request.data.get("subject")
    message = request.data.get("message")

    if not isinstance(subject, str) or not subject.strip():
        return _bad_request("Subject is required")
    if not isinstance(message, str) or not message.strip():
        return _bad_request("Message is required")

    cleaned_subject = subject.strip()[:160]
    cleaned_message = message.strip()
    support_body = (
        "PrepVilla support request\n\n"
        f"Role: {user.role}\n"
        f"Display name: {user.display_name}\n"
        f"Full name: {user.full_name or user.display_name}\n"
        f"Email: {user.email}\n"
        f"Mobile number: {user.mobile_number or 'Not provided'}\n"
        f"User ID: {user.id}\n\n"
        "Message:\n"
        f"{cleaned_message}\n"
    )

    from django.core.mail import EmailMessage

    try:
        email = EmailMessage(
            subject=f"[PrepVilla Support] {cleaned_subject}",
            body=support_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=["support@prepvilla.info"],
            reply_to=[user.email] if user.email else None,
        )
        email.send()
    except Exception:
        logger.exception("Support email send failed")
        return _bad_request("Failed to send support request", status=500)

    return JsonResponse({"ok": True})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def support_requests(request):
    user: AppUser = request.user
    if user.role not in {"student", "tutor"}:
        return _bad_request("Support requests are available to student and tutor accounts", status=403)

    if request.method == "GET":
        results = [
            {
                "id": str(item.id),
                "ticketNumber": item.ticket_number,
                "kind": item.kind,
                "topic": item.topic,
                "status": item.status,
                "priority": item.priority,
                "relatedReference": item.related_reference,
                "createdAt": item.created_at.isoformat(),
                "updatedAt": item.updated_at.isoformat(),
                "resolvedAt": item.resolved_at.isoformat() if item.resolved_at else None,
            }
            for item in SupportRequest.objects.filter(user=user).order_by("-created_at")[:50]
        ]
        return JsonResponse({"results": results})

    kind = str(request.data.get("kind") or "").strip().lower()
    topic = str(request.data.get("topic") or "").strip()
    message = str(request.data.get("message") or "").strip()
    related_reference = str(request.data.get("relatedReference") or "").strip()
    metadata = request.data.get("metadata") or {}

    if kind not in SupportRequest.Kind.values:
        return _bad_request("kind must be feedback, complaint, or issue")
    if not topic:
        return _bad_request("Topic is required")
    if len(topic) > 160:
        return _bad_request("Topic must be 160 characters or fewer")
    if len(message) < 10:
        return _bad_request("Message must be at least 10 characters")
    if len(message) > 10000:
        return _bad_request("Message must be 10,000 characters or fewer")
    if len(related_reference) > 160:
        return _bad_request("Related reference must be 160 characters or fewer")
    if not isinstance(metadata, dict):
        return _bad_request("metadata must be an object")
    try:
        serialized_metadata = json.dumps(metadata, default=str)
    except (TypeError, ValueError):
        return _bad_request("metadata must contain valid JSON values")
    if len(serialized_metadata) > 10000:
        return _bad_request("metadata is too large")

    severity = str(metadata.get("severity") or "").strip().lower()
    if kind == SupportRequest.Kind.FEEDBACK:
        priority = SupportRequest.Priority.NORMAL
    elif severity == "urgent":
        priority = SupportRequest.Priority.URGENT
    else:
        priority = SupportRequest.Priority.HIGH

    support_request = SupportRequest.objects.create(
        user=user,
        kind=kind,
        status=SupportRequest.Status.OPEN,
        priority=priority,
        role=user.role,
        topic=topic,
        message=message,
        related_reference=related_reference,
        metadata=metadata,
    )

    from django.core.mail import EmailMessage

    support_body = (
        f"PrepVilla {support_request.get_kind_display()} request\n\n"
        f"Ticket: {support_request.ticket_number}\n"
        f"Priority: {support_request.get_priority_display()}\n"
        f"Role: {user.role}\n"
        f"Display name: {user.display_name}\n"
        f"Full name: {user.full_name or user.display_name}\n"
        f"Email: {user.email}\n"
        f"Mobile number: {user.mobile_number or 'Not provided'}\n"
        f"User ID: {user.id}\n"
        f"Topic: {topic}\n"
        f"Related reference: {related_reference or 'Not provided'}\n\n"
        f"Message:\n{message}\n\n"
        f"Additional details:\n{serialized_metadata}\n"
    )
    try:
        EmailMessage(
            subject=f"[PrepVilla {support_request.get_kind_display()}] {support_request.ticket_number}: {topic}",
            body=support_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=["support@prepvilla.info"],
            reply_to=[user.email] if user.email else None,
        ).send()
    except Exception:
        logger.exception("Support request notification failed for %s", support_request.id)

    return JsonResponse(
        {
            "ok": True,
            "id": str(support_request.id),
            "ticketNumber": support_request.ticket_number,
            "status": support_request.status,
        },
        status=201,
    )

@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated, IsTutor])
def my_profile(request):
    user: AppUser = request.user
    tp = TutorProfile.objects.filter(user=user).select_related('user').first()
    if not tp:
        return _bad_request("Tutor profile not found", status=404)
    
    if request.method == "GET":
        data = {
            "id": str(tp.id),
            "headline": tp.headline,
            "bio": tp.bio,
            "subjects": tp.subjects_csv.split(",") if tp.subjects_csv else [],
            "hourlyRate": float(tp.hourly_rate_cents) / 100 if tp.hourly_rate_cents else None,
            "profilePhotoUrl": _resolve_tutor_photo_url(tp),
            "gender": tp.gender,
            "homeCity": tp.home_city,
            "homeState": tp.home_state,
            "homeAddress": tp.home_address,
            "stateOfOrigin": tp.state_of_origin,
            "verificationStatus": _normalize_tutor_verification_status(tp.verification_status),
            "isListed": tp.is_listed,
            "languages": tp.languages_csv.split(",") if tp.languages_csv else [],
            "responseTime": tp.response_time,
            "firstLessonFree": tp.first_lesson_free,
            "offersFaceToFace": tp.offers_face_to_face,
            "offersWebcam": tp.offers_webcam,
            "teachingModes": _tutor_teaching_modes(tp),
            "videoCallUrl": _tutor_video_call_url(tp),
            "videoMeetingUrl": tp.video_meeting_url or None,
            "additionalDocumentUrls": _load_string_list(tp.additional_document_urls),
            "bankName": tp.bank_name,
            "bankCode": tp.bank_code,
            "bankAccountNumber": tp.bank_account_number,
            "bankAccountName": tp.bank_account_name,
        }
        return JsonResponse(data)
    
    # PUT
    headline = request.data.get("headline")
    bio = request.data.get("bio")
    subjects = request.data.get("subjects")
    hourlyRate = request.data.get("hourlyRate")
    gender = request.data.get("gender")
    homeCity = request.data.get("homeCity")
    homeState = request.data.get("homeState")
    homeAddress = request.data.get("homeAddress")
    stateOfOrigin = request.data.get("stateOfOrigin")
    languages = request.data.get("languages")
    responseTime = request.data.get("responseTime")
    firstLessonFree = request.data.get("firstLessonFree")
    profilePhotoUrl = request.data.get("profilePhotoUrl")
    offersFaceToFace = request.data.get("offersFaceToFace")
    offersWebcam = request.data.get("offersWebcam")
    teachingModes = request.data.get("teachingModes")
    additionalDocumentUrls = request.data.get("additionalDocumentUrls")

    current_status = _normalize_tutor_verification_status(tp.verification_status)
    if current_status != "approved":
        return _bad_request("Tutor profile editing is only available after verification is approved", status=403)

    if tp.is_listed:
        restricted_profile_fields = [
            stateOfOrigin,
            responseTime,
            additionalDocumentUrls,
        ]
        if any(value is not None for value in restricted_profile_fields):
            return _bad_request(
                "Only the allowed approved tutor profile fields can be updated here",
                status=403,
            )
    
    if headline is not None:
        tp.headline = headline.strip()[:140]
    if bio is not None:
        tp.bio = bio.strip()
    if subjects is not None:
        tp.subjects_csv = ",".join([s.strip() for s in subjects] if isinstance(subjects, list) else [])
    if hourlyRate is not None:
        if not isinstance(hourlyRate, (int, float)) or hourlyRate <= 0:
            return _bad_request("Invalid hourly rate")
        tp.hourly_rate_cents = int(hourlyRate * 100)
    if gender is not None:
        tp.gender = gender.strip()
    if homeCity is not None:
        tp.home_city = homeCity.strip()
    if homeState is not None:
        tp.home_state = homeState.strip()
    if homeAddress is not None:
        tp.home_address = homeAddress.strip()
    if stateOfOrigin is not None:
        tp.state_of_origin = stateOfOrigin.strip()
    if languages is not None:
        tp.languages_csv = ",".join([l.strip() for l in languages] if isinstance(languages, list) else [])
    if responseTime is not None:
        tp.response_time = responseTime.strip()
    if firstLessonFree is not None:
        if isinstance(firstLessonFree, bool):
            tp.first_lesson_free = firstLessonFree
        elif isinstance(firstLessonFree, str):
            tp.first_lesson_free = firstLessonFree.strip().lower() in {"1", "true", "yes", "on"}
        else:
            tp.first_lesson_free = bool(firstLessonFree)
    if isinstance(teachingModes, list):
        normalized_modes = {str(item).strip().lower() for item in teachingModes if str(item).strip()}
        tp.offers_face_to_face = "face_to_face" in normalized_modes or "face-to-face" in normalized_modes
        tp.offers_webcam = "webcam" in normalized_modes
    else:
        if offersFaceToFace is not None:
            tp.offers_face_to_face = _coerce_bool(offersFaceToFace)
        if offersWebcam is not None:
            tp.offers_webcam = _coerce_bool(offersWebcam)
    if not tp.offers_face_to_face and not tp.offers_webcam:
        return _bad_request("Select at least one teaching method")
    if additionalDocumentUrls is not None:
        if not isinstance(additionalDocumentUrls, list):
            return _bad_request("additionalDocumentUrls must be a list")
        tp.additional_document_urls = _dump_string_list(additionalDocumentUrls)
    if profilePhotoUrl is not None:
        normalized_photo_url = profilePhotoUrl.strip()
        tp.profile_photo_url = normalized_photo_url

    if not tp.is_listed:
        missing_profile_fields: list[str] = []
        if not user.display_name.strip():
            missing_profile_fields.append("display name")
        if not tp.headline.strip():
            missing_profile_fields.append("headline")
        if not tp.bio.strip():
            missing_profile_fields.append("about")
        if not tp.subjects_csv.strip():
            missing_profile_fields.append("subjects")
        if not tp.languages_csv.strip():
            missing_profile_fields.append("languages")
        if tp.hourly_rate_cents <= 0:
            missing_profile_fields.append("hourly rate")
        if not tp.home_city.strip():
            missing_profile_fields.append("home city")
        if not tp.home_state.strip():
            missing_profile_fields.append("home state")
        if not tp.home_address.strip():
            missing_profile_fields.append("home address")
        if not tp.state_of_origin.strip():
            missing_profile_fields.append("state of origin")

        if missing_profile_fields:
            field_label = ", ".join(missing_profile_fields)
            return _bad_request(f"Complete your tutor profile before saving: {field_label}")

        tp.is_listed = True

    tp.save()
    user_changed_fields: list[str] = []
    if user.state != tp.home_state:
        user.state = tp.home_state
        user_changed_fields.append("state")
    if user.location != tp.home_city:
        user.location = tp.home_city
        user_changed_fields.append("location")
    if user.address != tp.home_address:
        user.address = tp.home_address
        user_changed_fields.append("address")
    if user.profile_photo_url != tp.profile_photo_url:
        user.profile_photo_url = tp.profile_photo_url
        user_changed_fields.append("profile_photo_url")
    if user_changed_fields:
        user.save(update_fields=user_changed_fields)

    data = {
        "id": str(tp.id),
        "headline": tp.headline,
        "bio": tp.bio,
        "subjects": tp.subjects_csv.split(",") if tp.subjects_csv else [],
        "hourlyRate": float(tp.hourly_rate_cents) / 100 if tp.hourly_rate_cents else None,
        "profilePhotoUrl": _resolve_tutor_photo_url(tp),
        "gender": tp.gender,
        "homeCity": tp.home_city,
        "homeState": tp.home_state,
        "homeAddress": tp.home_address,
        "stateOfOrigin": tp.state_of_origin,
        "verificationStatus": _normalize_tutor_verification_status(tp.verification_status),
        "isListed": tp.is_listed,
        "languages": tp.languages_csv.split(",") if tp.languages_csv else [],
        "responseTime": tp.response_time,
        "firstLessonFree": tp.first_lesson_free,
        "offersFaceToFace": tp.offers_face_to_face,
        "offersWebcam": tp.offers_webcam,
        "teachingModes": _tutor_teaching_modes(tp),
        "videoCallUrl": _tutor_video_call_url(tp),
        "videoMeetingUrl": tp.video_meeting_url or None,
        "additionalDocumentUrls": _load_string_list(tp.additional_document_urls),
    }
    return JsonResponse(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTutor])
def my_video_room(request):
    user: AppUser = request.user
    tp = TutorProfile.objects.filter(user=user).first()
    if not tp:
        return _bad_request("Tutor profile not found", status=404)
    if _normalize_tutor_verification_status(tp.verification_status) != "approved":
        return _bad_request("Only approved tutors can manage Google Meet rooms", status=403)

    meeting_url = _normalize_google_meet_url(request.data.get("videoMeetingUrl"))
    if not meeting_url:
        return _bad_request("videoMeetingUrl must be a valid Google Meet URL")

    meeting_space = _normalize_video_meeting_space(request.data.get("videoMeetingSpace"))
    if meeting_space is None:
        return _bad_request("videoMeetingSpace must use the spaces/{space} format")

    tp.video_meeting_url = meeting_url
    tp.video_meeting_space = meeting_space or ""
    tp.save(update_fields=["video_meeting_url", "video_meeting_space"])
    return JsonResponse(
        {
            "videoCallUrl": _tutor_video_call_url(tp),
            "videoMeetingUrl": tp.video_meeting_url,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def public_video_room_access(request, room_name: str):
    normalized_room_name = room_name.strip().lower()
    if not normalized_room_name.startswith(PREPVILLA_ROOM_PREFIX):
        return _bad_request("Video room not found", status=404)

    parsed_booking_id = _parse_booking_room_id(normalized_room_name)
    booking = _find_booking_for_room_name(normalized_room_name)
    if parsed_booking_id and not booking:
        return _bad_request("Video room not found", status=404)
    if booking:
        if normalized_room_name not in _booking_room_names(booking):
            return _bad_request("Video room not found", status=404)

        opens_at = booking.starts_at - timedelta(minutes=BOOKING_ROOM_EARLY_ACCESS_MINUTES) if booking.starts_at else None
        if booking.starts_at and booking.ends_at:
            now = timezone.now()
            if opens_at and now < opens_at:
                payload = _room_access_payload(
                    room_name=normalized_room_name,
                    source="booking",
                    title=f"{booking.student_user.display_name} lesson",
                    starts_at=booking.starts_at,
                    opens_at=opens_at,
                    ends_at=booking.ends_at,
                )
                payload["error"] = "This room is not open yet."
                return JsonResponse(payload, status=403)
            if now >= booking.ends_at:
                payload = _room_access_payload(
                    room_name=normalized_room_name,
                    source="booking",
                    title=f"{booking.student_user.display_name} lesson",
                    starts_at=booking.starts_at,
                    opens_at=opens_at,
                    ends_at=booking.ends_at,
                )
                payload["error"] = "This room link has expired."
                return JsonResponse(payload, status=410)

        return JsonResponse(
            _room_access_payload(
                room_name=normalized_room_name,
                source="booking",
                title=f"{booking.student_user.display_name} lesson",
                starts_at=booking.starts_at,
                opens_at=opens_at,
                ends_at=booking.ends_at,
            )
        )

    parsed_tutor_user_id = _parse_tutor_lobby_user_id(normalized_room_name)
    tutor_profile = _find_tutor_lobby_for_room_name(normalized_room_name)
    if parsed_tutor_user_id and not tutor_profile:
        return _bad_request("Video room not found", status=404)
    if tutor_profile:
        if normalized_room_name not in _tutor_lobby_room_names(tutor_profile):
            return _bad_request("Video room not found", status=404)
        return JsonResponse(
            _room_access_payload(
                room_name=normalized_room_name,
                source="tutor_lobby",
                title=f"{tutor_profile.user.display_name} Lobby",
            )
        )

    return JsonResponse(
        _room_access_payload(
            room_name=normalized_room_name,
            source="unmanaged",
            title="PrepVilla room",
        )
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsTutor])
def my_verification(request):
    user: AppUser = request.user
    tp = TutorProfile.objects.filter(user=user).first()
    if not tp:
        return _bad_request("Tutor profile not found", status=404)

    verification = VerificationRequest.objects.filter(tutor_profile=tp).first()

    if request.method == "GET":
        current_status = _normalize_tutor_verification_status(verification.status if verification else tp.verification_status)
        first_name, middle_name, last_name = _split_full_name(user.full_name or user.display_name)
        data = {
            "status": current_status,
            "notes": verification.notes if verification else "",
            "submittedAt": verification.submitted_at.isoformat() if verification and verification.submitted_at else None,
            "decidedAt": verification.decided_at.isoformat() if verification and verification.decided_at else None,
            "fullName": user.full_name or user.display_name,
            "firstName": first_name,
            "middleName": middle_name,
            "lastName": last_name,
            "email": user.email,
            "mobileNumber": user.mobile_number,
            "dateOfBirth": _optional_date_iso(user.date_of_birth),
            "countryOfBirth": tp.country_of_birth,
            "nationality": tp.nationality,
            "stateOfOrigin": tp.state_of_origin,
            "lgaOfOrigin": tp.lga_of_origin,
            "profilePhotoUrl": _resolve_tutor_photo_url(tp, verification),
            "homeState": verification.home_state if verification and verification.home_state else tp.home_state,
            "homeCity": verification.home_city if verification and verification.home_city else tp.home_city,
            "homeAddress": verification.home_address if verification and verification.home_address else tp.home_address,
            "qualification": verification.qualification if verification and verification.qualification else tp.qualification,
            "ninNumber": verification.nin_number if verification and verification.nin_number else tp.nin_number,
            "bvnNumber": verification.bvn_number if verification and verification.bvn_number else tp.bvn_number,
            "languages": tp.languages_csv.split(",") if tp.languages_csv else [],
            "documentUrls": _load_string_list(verification.document_urls if verification else tp.document_urls),
            "bankName": tp.bank_name,
            "bankCode": tp.bank_code,
            "bankAccountNumber": tp.bank_account_number,
            "bankAccountName": tp.bank_account_name,
        }
        return JsonResponse(data)

    existing_document_urls = _load_string_list(verification.document_urls if verification else tp.document_urls)

    homeState = request.data.get("homeState")
    if homeState is None:
        homeState = (verification.home_state if verification and verification.home_state else tp.home_state or user.state)

    homeCity = request.data.get("homeCity")
    if homeCity is None:
        homeCity = (verification.home_city if verification and verification.home_city else tp.home_city or user.location)

    homeAddress = request.data.get("homeAddress")
    if homeAddress is None:
        homeAddress = (verification.home_address if verification and verification.home_address else tp.home_address or user.address)

    qualification = request.data.get("qualification")
    if qualification is None:
        qualification = verification.qualification if verification and verification.qualification else tp.qualification

    ninNumber = request.data.get("ninNumber")
    if ninNumber is None:
        ninNumber = verification.nin_number if verification and verification.nin_number else tp.nin_number

    bvnNumber = request.data.get("bvnNumber")
    if bvnNumber is None:
        bvnNumber = verification.bvn_number if verification and verification.bvn_number else tp.bvn_number

    countryOfBirth = request.data.get("countryOfBirth")
    if countryOfBirth is None:
        countryOfBirth = tp.country_of_birth

    nationality = request.data.get("nationality")
    if nationality is None:
        nationality = tp.nationality

    stateOfOrigin = request.data.get("stateOfOrigin")
    if stateOfOrigin is None:
        stateOfOrigin = tp.state_of_origin

    lgaOfOrigin = request.data.get("lgaOfOrigin")
    if lgaOfOrigin is None:
        lgaOfOrigin = tp.lga_of_origin

    dateOfBirth = request.data.get("dateOfBirth")
    if dateOfBirth is None:
        dateOfBirth = _optional_date_iso(user.date_of_birth)

    profilePhotoUrl = request.data.get("profilePhotoUrl")
    if profilePhotoUrl is None:
        profilePhotoUrl = (
            verification.profile_photo_url
            if verification and verification.profile_photo_url
            else tp.profile_photo_url or user.profile_photo_url
        )

    documentUrls = request.data.get("documentUrls")
    if documentUrls is None:
        documentUrls = existing_document_urls
    elif isinstance(documentUrls, list):
        documentUrls = [str(item).strip() for item in documentUrls if str(item).strip()]
    elif isinstance(documentUrls, str):
        documentUrls = _load_string_list(documentUrls)

    notes = request.data.get("notes")

    bankName = request.data.get("bankName")
    if bankName is None:
        bankName = tp.bank_name
    bankCode = request.data.get("bankCode")
    if bankCode is None:
        bankCode = tp.bank_code
    bankAccountNumber = request.data.get("bankAccountNumber")
    if bankAccountNumber is None:
        bankAccountNumber = tp.bank_account_number
    bankAccountName = request.data.get("bankAccountName")
    if bankAccountName is None:
        bankAccountName = tp.bank_account_name
    
    has_split_name_fields = any(
        field in request.data for field in ("firstName", "middleName", "lastName")
    )
    if has_split_name_fields:
        firstName = request.data.get("firstName")
        middleName = request.data.get("middleName")
        lastName = request.data.get("lastName")
        fullName = _compose_full_name(firstName, middleName, lastName)
    else:
        fullName = request.data.get("fullName")
        if fullName is None:
            fullName = user.full_name or user.display_name
        firstName, middleName, lastName = _split_full_name(fullName)

    mobileNumber = request.data.get("mobileNumber")
    if mobileNumber is None:
        mobileNumber = user.mobile_number

    submitted_email = request.data.get("email")
    if submitted_email is not None and str(submitted_email).strip().lower() != user.email.strip().lower():
        return _bad_request("Email must match the authenticated account email")

    is_approved_verification = _normalize_tutor_verification_status(tp.verification_status) == "approved"
    is_locked_approved_tutor = is_approved_verification and tp.is_listed

    if is_locked_approved_tutor:
        locked_field_errors: list[str] = []
        current_full_name = (user.full_name or user.display_name or "").strip()
        if (request.data.get("fullName") is not None or has_split_name_fields) and str(fullName).strip() != current_full_name:
            locked_field_errors.append("name")
        if request.data.get("mobileNumber") is not None and str(mobileNumber).strip() != (user.mobile_number or "").strip():
            locked_field_errors.append("mobileNumber")
        if request.data.get("dateOfBirth") is not None and str(dateOfBirth).strip() != (_optional_date_iso(user.date_of_birth) or "").strip():
            locked_field_errors.append("dateOfBirth")
        for field_name, submitted_value, current_value in (
            ("countryOfBirth", countryOfBirth, tp.country_of_birth),
            ("nationality", nationality, tp.nationality),
            ("stateOfOrigin", stateOfOrigin, tp.state_of_origin),
            ("lgaOfOrigin", lgaOfOrigin, tp.lga_of_origin),
        ):
            if request.data.get(field_name) is not None and str(submitted_value).strip() != (current_value or "").strip():
                locked_field_errors.append(field_name)
        if request.data.get("qualification") is not None and str(qualification).strip() != (tp.qualification or "").strip():
            locked_field_errors.append("qualification")
        if request.data.get("ninNumber") is not None and str(ninNumber).strip() != (tp.nin_number or "").strip():
            locked_field_errors.append("ninNumber")
        if request.data.get("bvnNumber") is not None and str(bvnNumber).strip() != (tp.bvn_number or "").strip():
            locked_field_errors.append("bvnNumber")
        if locked_field_errors:
            return _bad_request(
                "The following approved tutor fields are locked and can only be changed through support: "
                + ", ".join(locked_field_errors),
                status=403,
            )

    missing_fields: list[str] = []
    if not isinstance(homeState, str) or not homeState.strip():
        missing_fields.append("homeState")
    if not isinstance(homeCity, str) or not homeCity.strip():
        missing_fields.append("homeCity")
    if not isinstance(homeAddress, str) or not homeAddress.strip():
        missing_fields.append("homeAddress")
    if not isinstance(qualification, str) or not qualification.strip():
        missing_fields.append("qualification")
    if not isinstance(ninNumber, str) or not ninNumber.strip():
        missing_fields.append("ninNumber")
    if not isinstance(bvnNumber, str) or not bvnNumber.strip():
        missing_fields.append("bvnNumber")
    if not isinstance(profilePhotoUrl, str) or not profilePhotoUrl.strip():
        missing_fields.append("profilePhotoUrl")
    if not isinstance(firstName, str) or not firstName.strip():
        missing_fields.append("firstName")
    if not isinstance(lastName, str) or not lastName.strip():
        missing_fields.append("lastName")
    if not isinstance(mobileNumber, str) or not mobileNumber.strip():
        missing_fields.append("mobileNumber")
    if not isinstance(dateOfBirth, str) or not dateOfBirth.strip():
        missing_fields.append("dateOfBirth")
    if not isinstance(documentUrls, list) or (not documentUrls and not is_approved_verification):
        missing_fields.append("documentUrls")
    bank_fields = (bankName, bankCode, bankAccountNumber, bankAccountName)
    if any(str(value or "").strip() for value in bank_fields) and not all(str(value or "").strip() for value in bank_fields):
        missing_fields.append("complete payout bank details")

    if missing_fields:
        return _bad_request(f"Missing required fields: {', '.join(missing_fields)}")

    if not isinstance(documentUrls, list) or (not documentUrls and not is_approved_verification):
        return _bad_request("At least one verification document is required")
    try:
        normalized_mobile_number = _normalize_mobile_number(mobileNumber, required=True)
        normalized_nin_number = _normalize_nin_number(ninNumber, required=True)
        normalized_bvn_number = _normalize_bvn_number(bvnNumber, required=True)
    except ValueError as exc:
        return _bad_request(str(exc))

    parsed_date_of_birth = None
    if isinstance(dateOfBirth, str) and dateOfBirth.strip():
        try:
            parsed_date_of_birth = dt.date.fromisoformat(dateOfBirth.strip()[:10])
        except ValueError:
            return _bad_request("Invalid date of birth")

    normalized_profile_photo_url = profilePhotoUrl.strip()[:500]

    if (
        not getattr(settings, "BYPASS_VERIFICATION", False)
        and is_verification_configured()
    ):
        name_parts = str(fullName).strip().split()
        identity_data = {
            "first_name": name_parts[0] if name_parts else "",
            "last_name": name_parts[-1] if len(name_parts) > 1 else "",
            "middle_name": " ".join(name_parts[1:-1]),
            "date_of_birth": parsed_date_of_birth,
            "mobile": normalized_mobile_number or "",
            "country_of_birth": countryOfBirth.strip(),
            "nationality": nationality.strip(),
            "gender": tp.gender,
            "state_of_origin": stateOfOrigin.strip(),
            "lga": lgaOfOrigin.strip(),
        }
        try:
            verify_nin_and_bvn(identity_data, normalized_nin_number, normalized_bvn_number)
        except (ValidationError, PremblyVerificationUnavailable, DikriptVerificationUnavailable) as exc:
            detail = getattr(exc, "detail", str(exc))
            return _bad_request(
                str(detail),
                status=503 if isinstance(exc, (PremblyVerificationUnavailable, DikriptVerificationUnavailable)) else 400,
            )

    normalized_bank_account_number = str(bankAccountNumber or "").strip()
    if normalized_bank_account_number and (
        len(normalized_bank_account_number) != 10 or not normalized_bank_account_number.isdigit()
    ):
        return _bad_request("bankAccountNumber must be a 10-digit Nigerian bank account number")

    if not verification:
        verification = VerificationRequest(tutor_profile=tp)

    verification.status = "approved" if is_approved_verification else "pending"
    verification.home_state = homeState.strip()
    verification.home_city = homeCity.strip()
    verification.home_address = homeAddress.strip()
    verification.qualification = qualification
    verification.nin_number = normalized_nin_number
    verification.bvn_number = normalized_bvn_number
    verification.profile_photo_url = normalized_profile_photo_url
    verification.document_urls = _dump_string_list(documentUrls)
    if not is_approved_verification:
        verification.notes = notes.strip() if isinstance(notes, str) else ""
    verification.decided_at = (verification.decided_at or timezone.now()) if is_approved_verification else None
    verification.submitted_at = timezone.now()
    verification.save()

    apply_verified_tutor_fields(
        user,
        tp,
        full_name=fullName,
        mobile_number=normalized_mobile_number,
        date_of_birth=parsed_date_of_birth,
        home_state=verification.home_state,
        home_city=verification.home_city,
        home_address=verification.home_address,
        qualification=qualification.strip(),
        nin_number=normalized_nin_number,
        bvn_number=normalized_bvn_number,
        state_of_origin=stateOfOrigin.strip(),
        lga_of_origin=lgaOfOrigin.strip(),
        country_of_birth=countryOfBirth.strip(),
        nationality=nationality.strip(),
        profile_photo_url=normalized_profile_photo_url,
        document_urls=verification.document_urls,
        verification_status="approved" if is_approved_verification else "pending",
        is_listed=tp.is_listed if is_approved_verification else False,
    )
    payout_fields = {
        "bank_name": str(bankName or "").strip(),
        "bank_code": str(bankCode or "").strip(),
        "bank_account_number": normalized_bank_account_number,
        "bank_account_name": str(bankAccountName or "").strip(),
    }
    if any(getattr(tp, field) != value for field, value in payout_fields.items()):
        for field, value in payout_fields.items():
            setattr(tp, field, value)
        tp.save(update_fields=[*payout_fields.keys()])

    if not is_approved_verification:
        subject = "Verification Submitted"
        message = (
            "Your verification documents have been submitted successfully.\n\n\n"
            "Residence:\n"
            f"{verification.home_address}\n"
            f"{verification.home_city}, {verification.home_state}\n\n"
            f"Qualification: {qualification}\n\n"
            f"NIN: {normalized_nin_number}"
            "\n\n\nOur team will review your credentials and update your status soon. Please allow 1-3 business days for processing."
        )
        _send_email(subject, message, [user.email])

    data = {
        "status": _normalize_tutor_verification_status(verification.status),
        "notes": verification.notes,
        "submittedAt": verification.submitted_at.isoformat() if verification.submitted_at else None,
        "decidedAt": verification.decided_at.isoformat() if verification.decided_at else None,
        "fullName": user.full_name or user.display_name,
        "firstName": firstName,
        "middleName": middleName,
        "lastName": lastName,
        "email": user.email,
        "mobileNumber": user.mobile_number,
        "dateOfBirth": _optional_date_iso(user.date_of_birth),
        "countryOfBirth": tp.country_of_birth,
        "nationality": tp.nationality,
        "stateOfOrigin": tp.state_of_origin,
        "lgaOfOrigin": tp.lga_of_origin,
        "profilePhotoUrl": verification.profile_photo_url,
        "homeState": verification.home_state,
        "homeCity": verification.home_city,
        "homeAddress": verification.home_address,
        "qualification": verification.qualification,
        "ninNumber": verification.nin_number,
        "bvnNumber": verification.bvn_number,
        "languages": tp.languages_csv.split(",") if tp.languages_csv else [],
        "documentUrls": _load_string_list(verification.document_urls),
        "bankName": tp.bank_name,
        "bankCode": tp.bank_code,
        "bankAccountNumber": tp.bank_account_number,
        "bankAccountName": tp.bank_account_name,
    }
    return JsonResponse(data)

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTutor])
def my_verification_resend(request):
    user: AppUser = request.user
    tp = TutorProfile.objects.filter(user=user).first()
    if not tp:
        return _bad_request("Tutor profile not found", status=404)
    
    verification = VerificationRequest.objects.filter(tutor_profile=tp).first()
    if not verification or verification.status != "pending":
        return _bad_request("No pending verification to resend", status=400)
    
    # Send email
    subject = "Verification Submitted (Reminder)"
    message = (
        "This is a reminder that your verification documents have been submitted.\n\n"
        "Residence:\n"
        f"{verification.home_address}\n"
        f"{verification.home_city}, {verification.home_state}\n\n"
        f"Qualification: {verification.qualification}\n"
        f"NIN: {verification.nin_number}\n\n"
        "Status: Pending Review\n\n"
        "We will notify you once the review is complete."
    )
    html_message = f"""
    <html>
    <body>
    <h2>Verification Re-Submitted Successfully</h2>
    <p>Your verification documents have been re-submitted successfully.</p>
    <ul>
    <li><strong>Residence:</strong> {verification.home_address}, {verification.home_city}, {verification.home_state}</li>
    <li><strong>Qualification:</strong> {verification.qualification}</li>
    <li><strong>NIN:</strong> {verification.nin_number}</li>
    </ul>
    <p><strong>Status:</strong> Pending Review</p>
    <p>Please click one of the buttons below to approve or reject the verification:</p>
    <a href="http://localhost:8500/api/verification/approve?tutor_id={tp.id}&action=approve" style="background-color: green; color: white; padding: 10px 20px; text-decoration: none; margin-right: 10px;">Approve</a>
    <a href="http://localhost:8500/api/verification/approve?tutor_id={tp.id}&action=reject" style="background-color: red; color: white; padding: 10px 20px; text-decoration: none;">Reject</a>
    <p>We will notify you once the review is complete.</p>
    </body>
    </html>
    """
    _send_email(subject, message, [user.email], html_message)
    
    return JsonResponse({"message": "Email resent"})

@api_view(["GET"])
def verification_approve(request):
    tutor_id = request.GET.get('tutor_id')
    action = request.GET.get('action')
    if not tutor_id or action not in ['approve', 'reject']:
        return HttpResponse("Invalid request", status=400)
    
    try:
        tp = TutorProfile.objects.get(id=tutor_id)
    except TutorProfile.DoesNotExist:
        return HttpResponse("Tutor not found", status=404)
    
    verification = VerificationRequest.objects.filter(tutor_profile=tp).first()
    if not verification or verification.status != "pending":
        return HttpResponse("No pending verification", status=400)

    if action == 'approve':
        _apply_tutor_verification_decision(tp, verification, approved=True, notes="Approved via email link")
        return HttpResponse("Verification approved! You are now listed and visible to students.")
    elif action == 'reject':
        _apply_tutor_verification_decision(tp, verification, approved=False, notes="Rejected via email link")
        return HttpResponse("Verification rejected. Please resubmit your documents.")

    return HttpResponse("Status updated.")


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_verification_requests(request):
    status_filter = (request.GET.get("status") or "all").strip().lower()
    requests = VerificationRequest.objects.select_related("tutor_profile__user").order_by("-submitted_at")
    if status_filter != "all":
        requests = requests.filter(status=status_filter)

    data = []
    for item in requests:
        document_urls = _load_string_list(item.document_urls)
        data.append(
            {
                "id": str(item.id),
                "tutorId": str(item.tutor_profile.id),
                "tutorName": item.tutor_profile.user.display_name,
                "status": _normalize_tutor_verification_status(item.status),
                "submittedAt": item.submitted_at.isoformat() if item.submitted_at else None,
                "decidedAt": item.decided_at.isoformat() if item.decided_at else None,
                "notes": item.notes,
                "documentUrl": document_urls[0] if document_urls else None,
                "documentUrls": document_urls,
            }
        )
    return JsonResponse({"results": data})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_verification_request_decision(request, request_id, action):
    if action not in {"approve", "reject"}:
        return _bad_request("Invalid action")

    verification = (
        VerificationRequest.objects.select_related("tutor_profile__user")
        .filter(id=request_id)
        .first()
    )
    if not verification:
        return _bad_request("Verification request not found", status=404)
    if _normalize_tutor_verification_status(verification.status) != "pending":
        return _bad_request("Verification request has already been processed")

    notes = request.data.get("notes", "")
    normalized_notes = notes.strip() if isinstance(notes, str) else ""
    approved = action == "approve"
    _apply_tutor_verification_decision(
        verification.tutor_profile,
        verification,
        approved=approved,
        notes=normalized_notes,
    )

    decision_label = "approved" if approved else "rejected"
    subject = f"Verification {decision_label.title()}"
    message = (
        f"Your tutor verification has been {decision_label}."
        if not normalized_notes
        else f"Your tutor verification has been {decision_label}.\n\nNotes: {normalized_notes}"
    )
    _send_email(subject, message, [verification.tutor_profile.user.email])

    return JsonResponse({"ok": True, "status": decision_label})

@api_view(["GET", "POST", "PUT"])
@permission_classes([IsAuthenticated, IsTutor])
def my_availability(request):
    user: AppUser = request.user
    tp = TutorProfile.objects.filter(user=user).first()
    if not tp:
        return _bad_request("Tutor profile not found", status=404)
    
    if request.method in ("POST", "PUT"):
        slots = request.data.get("slots")
        if not isinstance(slots, list):
            return _bad_request("slots must be a list")
        if len(slots) > 50:
            return _bad_request("Too many slots (max 50)")

        now = timezone.now()
        to_create: list[AvailabilitySlot] = []
        for raw in slots:
            if not isinstance(raw, dict):
                return _bad_request("Each slot must be an object")
            starts_at = _parse_dt(str(raw.get("startsAt") or ""))
            ends_at = _parse_dt(str(raw.get("endsAt") or ""))
            if not starts_at or not ends_at:
                return _bad_request("startsAt and endsAt must be ISO datetimes")
            if ends_at <= starts_at:
                return _bad_request("endsAt must be after startsAt")
            if starts_at <= now:
                return _bad_request("startsAt must be in the future")
            to_create.append(AvailabilitySlot(tutor_profile=tp, starts_at=starts_at, ends_at=ends_at))

        with transaction.atomic():
            AvailabilitySlot.objects.filter(tutor_profile=tp, starts_at__gt=timezone.now()).delete()
            AvailabilitySlot.objects.bulk_create(to_create)

    availability = AvailabilitySlot.objects.filter(tutor_profile=tp, starts_at__gt=timezone.now()).order_by("starts_at")[:50]
    data = [{"id": str(s.id), "startsAt": s.starts_at.isoformat(), "endsAt": s.ends_at.isoformat()} for s in availability]
    return JsonResponse({"results": data})

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def tutor_booking_requests(request, tutor_id):
    user = request.user
    if not _is_student_verified(user):
        return _bad_request("You must complete profile verification before booking sessions", status=403)
    
    try:
        tp = TutorProfile.objects.get(id=tutor_id, is_listed=True)
    except TutorProfile.DoesNotExist:
        return _bad_request("Tutor not found", status=404)
    
    slot_id = request.data.get("slotId")
    lesson_type = request.data.get("lessonType")
    notes = request.data.get("notes", "")
    requested_range = request.data.get("requestedStartRange")

    if not isinstance(lesson_type, str) or not lesson_type.strip():
        return _bad_request("lessonType required")
    if not isinstance(notes, str):
        return _bad_request("notes must be a string")

    normalized_lesson_type = lesson_type.strip().lower()
    if "webcam" in normalized_lesson_type and not tp.offers_webcam:
        return _bad_request("This tutor does not currently offer webcam lessons")
    if ("face-to-face" in normalized_lesson_type or "face to face" in normalized_lesson_type) and not tp.offers_face_to_face:
        return _bad_request("This tutor does not currently offer face-to-face lessons")

    starts_at = None
    ends_at = None
    requested_from = None
    requested_to = None

    if isinstance(slot_id, str) and slot_id.strip():
        try:
            slot = AvailabilitySlot.objects.get(id=slot_id.strip(), tutor_profile=tp, starts_at__gt=timezone.now())
        except AvailabilitySlot.DoesNotExist:
            return _bad_request("Slot not found or not available", status=400)
        starts_at = slot.starts_at
        ends_at = slot.ends_at
    elif isinstance(requested_range, dict):
        raw_from = requested_range.get("from")
        raw_to = requested_range.get("to")
        if not isinstance(raw_from, str) or not isinstance(raw_to, str):
            return _bad_request("requestedStartRange.from and requestedStartRange.to required")
        requested_from = _parse_dt(raw_from.strip())
        requested_to = _parse_dt(raw_to.strip())
        if not requested_from or not requested_to:
            return _bad_request("requestedStartRange must be ISO datetimes")
        if requested_to <= requested_from:
            return _bad_request("requestedStartRange.to must be after from")
        if requested_from <= timezone.now():
            return _bad_request("requestedStartRange.from must be in the future")
    else:
        return _bad_request("slotId or requestedStartRange required")

    booking = Booking.objects.create(
        student_user=user,
        tutor_profile=tp,
        status="requested",
        lesson_type=lesson_type.strip(),
        starts_at=starts_at,
        ends_at=ends_at,
        requested_from=requested_from,
        requested_to=requested_to,
        notes=notes.strip(),
    )

    conversation = Conversation.objects.filter(student_user=user, tutor_profile=tp).first()
    if not conversation:
        conversation = Conversation.objects.create(student_user=user, tutor_profile=tp)
    if hasattr(conversation, "participants"):
        conversation.participants.add(user, tp.user)

    if notes.strip():
        Message.objects.create(conversation=conversation, sender_user=user, body=notes.strip())

    conv = {
        "id": str(conversation.id),
        "tutorId": str(tp.id),
        "tutorName": tp.user.display_name,
        "studentId": str(user.id),
        "studentName": user.display_name,
        "createdAt": conversation.created_at.isoformat(),
        "isBlocked": conversation.is_blocked,
    }

    return JsonResponse({"bookingId": str(booking.id), "conversation": conv})

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def conversations_list(request):
    user: AppUser = request.user
    if user.role == "student" and not _is_student_verified(user):
        return _bad_request("You must complete profile verification before contacting tutors", status=403)
    
    if request.method == "POST":
        tutor_id = request.data.get("tutorId")
        other_user_id = request.data.get("otherUserId")

        tutor_profile = None
        if isinstance(tutor_id, str) and tutor_id.strip():
            parsed_tutor_id = _parse_uuid_or_none(tutor_id)
            if not parsed_tutor_id:
                return _bad_request("Tutor not found", status=404)
            tutor_profile = TutorProfile.objects.filter(id=parsed_tutor_id, is_listed=True).select_related("user").first()
            if not tutor_profile:
                return _bad_request("Tutor not found", status=404)
        elif isinstance(other_user_id, str) and other_user_id.strip():
            other_user = AppUser.objects.filter(id=other_user_id.strip()).first()
            if not other_user:
                return _bad_request("User not found", status=404)
            tutor_profile = TutorProfile.objects.filter(user=other_user, is_listed=True).select_related("user").first()
            if not tutor_profile:
                return _bad_request("Tutor not found", status=404)
        else:
            return _bad_request("tutorId required")

        if user.role != "student":
            return _bad_request("Only students can start a conversation", status=403)

        conversation = Conversation.objects.filter(student_user=user, tutor_profile=tutor_profile).first()
        if not conversation:
            conversation = Conversation.objects.create(student_user=user, tutor_profile=tutor_profile)
        if hasattr(conversation, "participants"):
            conversation.participants.add(user, tutor_profile.user)

        conv = {
            "id": str(conversation.id),
            "tutorId": str(tutor_profile.id),
            "tutorName": tutor_profile.user.display_name,
            "studentId": str(user.id),
            "studentName": user.display_name,
            "createdAt": conversation.created_at.isoformat(),
            "isBlocked": conversation.is_blocked,
        }
        return JsonResponse({"conversation": conv})
    
    # GET
    if user.role == "student":
        conversations = Conversation.objects.filter(student_user=user).select_related("tutor_profile__user").order_by("-created_at")
    elif user.role == "tutor":
        conversations = Conversation.objects.filter(tutor_profile__user=user).select_related("tutor_profile__user", "student_user").order_by("-created_at")
    else:
        conversations = Conversation.objects.select_related("tutor_profile__user", "student_user").order_by("-created_at")

    data = [
        {
            "id": str(c.id),
            "tutorId": str(c.tutor_profile_id),
            "tutorName": c.tutor_profile.user.display_name,
            "studentId": str(c.student_user_id),
            "studentName": c.student_user.display_name,
            "createdAt": c.created_at.isoformat(),
            "isBlocked": c.is_blocked,
        }
        for c in conversations
    ]
    return JsonResponse({"results": data})

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def send_message(request, conversation_id):
    user: AppUser = request.user
    if user.role == "student" and not _is_student_verified(user):
        return _bad_request("You must complete profile verification before contacting tutors", status=403)
    
    try:
        conversation = Conversation.objects.select_related("tutor_profile__user", "student_user").get(id=conversation_id)
    except Conversation.DoesNotExist:
        return _bad_request("Conversation not found or you don't have access", status=404)

    if user.role == "student" and conversation.student_user_id != user.id:
        return _bad_request("Conversation not found or you don't have access", status=404)
    if user.role == "tutor" and conversation.tutor_profile.user_id != user.id:
        return _bad_request("Conversation not found or you don't have access", status=404)
    if conversation.is_blocked:
        return _bad_request("Conversation is blocked", status=403)

    if request.method == "GET":
        msgs = Message.objects.filter(conversation=conversation).order_by("created_at")[:200]
        data = [
            {
                "id": str(m.id),
                "conversationId": str(conversation.id),
                "senderUserId": str(m.sender_user_id),
                "body": m.body,
                "createdAt": m.created_at.isoformat(),
                "readAt": m.read_at.isoformat() if m.read_at else None,
            }
            for m in msgs
        ]
        return JsonResponse({"results": data})

    body = request.data.get("body") or request.data.get("content")
    if not isinstance(body, str) or not body.strip():
        return _bad_request("Message body is required")
    
    message = Message.objects.create(conversation=conversation, sender_user=user, body=body.strip())

    payload = {
        "id": str(message.id),
        "conversationId": str(conversation.id),
        "senderUserId": str(message.sender_user_id),
        "body": message.body,
        "createdAt": message.created_at.isoformat(),
        "readAt": message.read_at.isoformat() if message.read_at else None,
    }

    try:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"conv_{conversation.id}",
                {"type": "message_created", "payload": payload},
            )
    except Exception:
        logger.exception("Failed to broadcast websocket message")

    return JsonResponse({"message": payload})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def message_tutor(request, tutor_id):
    user: AppUser = request.user
    if user.role == "student" and not _is_student_verified(user):
        return _bad_request("You must complete profile verification before contacting tutors", status=403)
    
    content = request.data.get("content") or request.data.get("initialMessage")
    if not content:
        return _bad_request("Message content required")

    parsed_tutor_id = _parse_uuid_or_none(tutor_id)
    if not parsed_tutor_id:
        return _bad_request("Tutor not found", status=404)
    
    try:
        tutor_profile = TutorProfile.objects.get(id=parsed_tutor_id)
        other_user = tutor_profile.user
    except TutorProfile.DoesNotExist:
        return _bad_request("Tutor not found")
    
    if other_user == user:
        return _bad_request("Cannot message yourself")
    
    conversation = Conversation.objects.filter(participants=user).filter(participants=other_user).first()
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(user, other_user)
    
    message = Message.objects.create(conversation=conversation, sender=user, content=content)
    
    return JsonResponse({
        "id": str(message.id),
        "content": message.content,
        "createdAt": message.created_at.isoformat(),
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def message_user(request, other_user_id):
    user: AppUser = request.user
    if user.role == "student" and not _is_student_verified(user):
        return _bad_request("You must complete profile verification before contacting tutors", status=403)
    
    content = request.data.get("content") or request.data.get("initialMessage")
    if not content:
        return _bad_request("Message content required")
    
    try:
        other_user = AppUser.objects.get(id=other_user_id)
    except AppUser.DoesNotExist:
        return _bad_request("User not found")
    if other_user == user:
        return _bad_request("Cannot message yourself")
    
    conversation = Conversation.objects.filter(participants=user).filter(participants=other_user).first()
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(user, other_user)
    
    message = Message.objects.create(conversation=conversation, sender=user, content=content)
    
    return JsonResponse({
        "id": str(message.id),
        "content": message.content,
        "createdAt": message.created_at.isoformat(),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bookings_list(request):
    user: AppUser = request.user
    if user.role == "student":
        bookings = Booking.objects.filter(student_user=user).select_related(
            "tutor_profile__user",
            "student_user",
            "review",
        )
    elif user.role == "tutor":
        bookings = Booking.objects.filter(tutor_profile__user=user).select_related(
            "tutor_profile__user",
            "student_user",
            "review",
        )
    else:
        return _bad_request("Unauthorized", status=403)
    
    data = [{
        "id": str(b.id),
        "student": {"id": str(b.student_user.id), "displayName": b.student_user.display_name},
        "tutor": {"id": str(b.tutor_profile.user.id), "displayName": b.tutor_profile.user.display_name},
        "tutorProfileId": str(b.tutor_profile.id),
        "status": b.status,
        "lessonType": b.lesson_type,
        "startsAt": b.starts_at.isoformat() if b.starts_at else None,
        "endsAt": b.ends_at.isoformat() if b.ends_at else None,
        "studentCompletedAt": b.student_completed_at.isoformat() if b.student_completed_at else None,
        "tutorCompletedAt": b.tutor_completed_at.isoformat() if b.tutor_completed_at else None,
        "requestedStartRange": (
            {
                "from": b.requested_from.isoformat(),
                "to": b.requested_to.isoformat(),
            }
            if b.requested_from and b.requested_to
            else None
        ),
        "notes": b.notes,
        "createdAt": b.created_at.isoformat(),
        "tutorName": b.tutor_profile.user.display_name,
        "studentName": b.student_user.display_name,
        "tutorPhotoUrl": _resolve_tutor_photo_url(b.tutor_profile),
        "reviewId": str(b.review.id) if hasattr(b, "review") else None,
        "teachingModes": _tutor_teaching_modes(b.tutor_profile),
        "videoCallUrl": _booking_video_call_url(b),
        "videoMeetingUrl": b.video_meeting_url or None,
    } for b in bookings.order_by("-created_at")]
    
    return JsonResponse({"results": data})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTutor])
def booking_video_room(request, booking_id):
    user: AppUser = request.user
    booking = _get_booking_for_action(booking_id)
    if not booking:
        return _bad_request("Booking not found", status=404)
    if not _can_manage_booking_as_tutor(user, booking):
        return _bad_request("You can only manage video rooms for your own bookings", status=403)
    if "webcam" not in (booking.lesson_type or "").strip().lower():
        return _bad_request("Google Meet links can only be attached to webcam bookings")

    meeting_url = _normalize_google_meet_url(request.data.get("videoMeetingUrl"))
    if not meeting_url:
        return _bad_request("videoMeetingUrl must be a valid Google Meet URL")

    meeting_space = _normalize_video_meeting_space(request.data.get("videoMeetingSpace"))
    if meeting_space is None:
        return _bad_request("videoMeetingSpace must use the spaces/{space} format")

    booking.video_meeting_url = meeting_url
    booking.video_meeting_space = meeting_space or ""
    booking.save(update_fields=["video_meeting_url", "video_meeting_space"])
    return JsonResponse(
        {
            "videoCallUrl": _booking_video_call_url(booking),
            "videoMeetingUrl": booking.video_meeting_url,
        }
    )


def _get_booking_for_action(booking_id: str) -> Booking | None:
    return Booking.objects.select_related("tutor_profile__user", "student_user").filter(id=booking_id).first()


def _can_manage_booking_as_tutor(user: AppUser, booking: Booking) -> bool:
    return user.role == "tutor" and booking.tutor_profile.user_id == user.id


def _can_manage_booking_as_participant(user: AppUser, booking: Booking) -> bool:
    if user.role == "student":
        return booking.student_user_id == user.id
    if user.role == "tutor":
        return booking.tutor_profile.user_id == user.id
    return False


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTutor])
def confirm_booking(request, booking_id):
    user: AppUser = request.user
    booking = _get_booking_for_action(booking_id)
    if not booking:
        return _bad_request("Booking not found", status=404)
    if not _can_manage_booking_as_tutor(user, booking):
        return _bad_request("You can only confirm your own booking requests", status=403)
    if booking.status != "requested":
        return _bad_request("Only requested bookings can be confirmed")

    booking.status = "confirmed"
    booking.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": booking.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def complete_booking(request, booking_id):
    user: AppUser = request.user
    booking = Booking.objects.select_for_update().select_related("tutor_profile__user", "student_user").filter(id=booking_id).first()
    if not booking:
        return _bad_request("Booking not found", status=404)
    if not _can_manage_booking_as_participant(user, booking):
        return _bad_request("Only the student or tutor on this booking can confirm completion", status=403)
    if booking.status == "completed":
        payout = BookingPayment.objects.filter(booking=booking).first()
        payout_record = TutorPayout.objects.filter(booking_payment=payout).first() if payout else None
        return JsonResponse({
            "ok": True,
            "status": booking.status,
            "studentConfirmed": bool(booking.student_completed_at),
            "tutorConfirmed": bool(booking.tutor_completed_at),
            "payoutStatus": payout_record.status if payout_record else "queued",
        })
    if booking.status != "confirmed":
        return _bad_request("Only confirmed bookings can have completion confirmed")
    if booking.ends_at and booking.ends_at > timezone.now():
        return _bad_request("A booking can only be completed after the lesson ends")

    payment = BookingPayment.objects.filter(
        booking=booking,
        status=BookingPayment.Status.COMPLETED,
    ).first()
    if not payment:
        return _bad_request("The student payment must be completed before the lesson can be released")

    now = timezone.now()
    update_fields = []
    if user.id == booking.student_user_id:
        if booking.student_completed_at:
            return _bad_request("You have already confirmed this lesson")
        booking.student_completed_at = now
        update_fields.append("student_completed_at")
    else:
        if booking.tutor_completed_at:
            return _bad_request("You have already confirmed this lesson")
        booking.tutor_completed_at = now
        update_fields.append("tutor_completed_at")

    if booking.student_completed_at and booking.tutor_completed_at:
        booking.status = "completed"
        update_fields.append("status")
    booking.save(update_fields=update_fields)
    payout = queue_tutor_payout(payment, enqueue=bool(booking.student_completed_at))
    return JsonResponse({
        "ok": True,
        "status": booking.status,
        "studentConfirmed": bool(booking.student_completed_at),
        "tutorConfirmed": bool(booking.tutor_completed_at),
        "payoutStatus": payout.status,
        "awaitingOtherConfirmation": booking.status != "completed",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTutor])
def reject_booking(request, booking_id):
    user: AppUser = request.user
    booking = _get_booking_for_action(booking_id)
    if not booking:
        return _bad_request("Booking not found", status=404)
    if not _can_manage_booking_as_tutor(user, booking):
        return _bad_request("You can only reject your own booking requests", status=403)
    if booking.status != "requested":
        return _bad_request("Only requested bookings can be rejected")

    booking.status = "rejected"
    booking.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": booking.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_booking(request, booking_id):
    user: AppUser = request.user
    booking = _get_booking_for_action(booking_id)
    if not booking:
        return _bad_request("Booking not found", status=404)
    if not _can_manage_booking_as_participant(user, booking):
        return _bad_request("You can only cancel your own bookings", status=403)
    if booking.status in {"cancelled", "completed", "rejected"}:
        return _bad_request("This booking can no longer be cancelled")

    booking.status = "cancelled"
    booking.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": booking.status})

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def submit_review(request, booking_id=None):
    user: AppUser = request.user
    booking_id = booking_id or request.data.get("bookingId")
    rating = request.data.get("rating")
    comment = request.data.get("comment", "")
    
    if not booking_id:
        return _bad_request("Booking ID is required")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return _bad_request("Rating must be an integer between 1 and 5")
    if comment is None:
        comment = ""
    if not isinstance(comment, str):
        return _bad_request("Comment must be a string")
    
    try:
        booking = Booking.objects.select_related("tutor_profile__user", "student_user").get(id=booking_id)
    except Booking.DoesNotExist:
        return _bad_request("Booking not found", status=404)
    if booking.student_user_id != user.id:
        return _bad_request("You can only review your own bookings", status=403)
    
    if booking.status not in ["completed", "paid"]:
        return _bad_request("You can only review completed bookings")
    
    if Review.objects.filter(booking=booking).exists():
        return _bad_request("You have already reviewed this booking")
    
    review = Review.objects.create(
        booking=booking,
        tutor_profile=booking.tutor_profile,
        student_user=user,
        rating=rating,
        comment=comment.strip(),
    )
    
    return JsonResponse({
        "id": str(review.id),
        "bookingId": str(booking.id),
        "rating": review.rating,
        "comment": review.comment,
        "createdAt": review.created_at.isoformat(),
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def tutor_reviews(request, tutor_id):
    parsed_tutor_id = _parse_uuid_or_none(tutor_id)
    if not parsed_tutor_id:
        return _bad_request("Tutor not found", status=404)
    try:
        tutor = TutorProfile.objects.get(id=parsed_tutor_id)
    except TutorProfile.DoesNotExist:
        return _bad_request("Tutor not found", status=404)
    
    reviews = Review.objects.filter(tutor_profile=tutor).select_related("student_user", "booking").order_by("-created_at")
    
    data = [{
        "id": str(r.id),
        "studentName": r.student_user.display_name,
        "rating": r.rating,
        "comment": r.comment,
        "createdAt": r.created_at.isoformat(),
        "bookingId": str(r.booking.id),
    } for r in reviews]
    
    return JsonResponse({"reviews": data, "summary": _review_summary_payload(reviews)})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_mobile_change_request(request):
    user: AppUser = request.user
    
    try:
        requested_mobile = _normalize_mobile_number(request.data.get("newMobileNumber"), required=True)
    except ValueError as exc:
        return _bad_request(str(exc))
    
    # Check if there's already a pending request
    existing_request = MobileNumberChangeRequest.objects.filter(
        user=user, status="pending"
    ).first()
    if existing_request:
        return _bad_request("You already have a pending mobile number change request")
    
    # Create the request
    change_request = MobileNumberChangeRequest.objects.create(
        user=user,
        current_mobile=user.mobile_number or "",
        requested_mobile=requested_mobile,
        status="pending"
    )
    
    return JsonResponse({
        "id": str(change_request.id),
        "message": "Mobile number change request submitted successfully. It will be reviewed by an administrator.",
        "requestedMobile": change_request.requested_mobile,
        "submittedAt": change_request.submitted_at.isoformat(),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_mobile_change_requests(request):
    user: AppUser = request.user
    
    requests = MobileNumberChangeRequest.objects.filter(user=user).order_by("-submitted_at")
    
    data = [{
        "id": str(r.id),
        "currentMobile": r.current_mobile,
        "requestedMobile": r.requested_mobile,
        "status": r.status,
        "submittedAt": r.submitted_at.isoformat(),
        "reviewedAt": r.reviewed_at.isoformat() if r.reviewed_at else None,
        "adminNotes": r.admin_notes,
    } for r in requests]
    
    return JsonResponse({"requests": data})

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_mobile_change_requests(request):
    if request.method == "GET":
        status_filter = request.GET.get("status", "pending")
        requests = MobileNumberChangeRequest.objects.filter(
            status=status_filter if status_filter != "all" else None
        ).select_related("user").order_by("-submitted_at")
        
        data = [{
            "id": str(r.id),
            "userId": str(r.user.id),
            "userName": r.user.display_name,
            "userEmail": r.user.email,
            "currentMobile": r.current_mobile,
            "requestedMobile": r.requested_mobile,
            "status": r.status,
            "submittedAt": r.submitted_at.isoformat(),
            "reviewedAt": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "adminNotes": r.admin_notes,
        } for r in requests]
        
        return JsonResponse({"requests": data})
    
    # POST - Approve/Reject request
    request_id = request.data.get("requestId")
    action = request.data.get("action")  # "approve" or "reject"
    admin_notes = request.data.get("adminNotes", "").strip()
    
    if not request_id or action not in ["approve", "reject"]:
        return _bad_request("Invalid request data")
    
    try:
        change_request = MobileNumberChangeRequest.objects.get(id=request_id, status="pending")
    except MobileNumberChangeRequest.DoesNotExist:
        return _bad_request("Request not found or already processed")
    
    from django.utils import timezone
    
    if action == "approve":
        # Update the user's mobile number
        change_request.user.mobile_number = change_request.requested_mobile
        change_request.user.save(update_fields=["mobile_number"])
        change_request.status = "approved"
    else:
        change_request.status = "rejected"
    
    change_request.reviewed_at = timezone.now()
    change_request.reviewed_by = request.user
    change_request.admin_notes = admin_notes
    change_request.save()
    
    return JsonResponse({
        "id": str(change_request.id),
        "status": change_request.status,
        "message": f"Mobile number change request {action}d successfully",
    })

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def student_verification(request):
    user: AppUser = request.user
    if user.role != "student":
        return _bad_request("Only students can access this endpoint", status=403)

    verification = StudentVerificationRequest.objects.filter(user=user).first()

    if request.method == "GET":
        first_name, middle_name, last_name = _split_full_name(user.full_name or user.display_name)
        return JsonResponse({
            "status": verification.status if verification else "not_submitted",
            "notes": verification.admin_notes if verification else "",
            "submittedAt": verification.submitted_at.isoformat() if verification and verification.submitted_at else None,
            "decidedAt": verification.reviewed_at.isoformat() if verification and verification.reviewed_at else None,
            "reviewedAt": verification.reviewed_at.isoformat() if verification and verification.reviewed_at else None,
            "adminNotes": verification.admin_notes if verification else "",
            "fullName": user.full_name or user.display_name,
            "firstName": first_name,
            "middleName": middle_name,
            "lastName": last_name,
            "email": user.email,
            "profilePhotoUrl": verification.profile_photo_url if verification else user.profile_photo_url,
            "dateOfBirth": _optional_date_iso(verification.date_of_birth if verification else user.date_of_birth),
            "mobileNumber": verification.mobile_number if verification else user.mobile_number,
            "ninNumber": verification.nin_number if verification else "",
            "bvnNumber": verification.bvn_number if verification else "",
            "countryOfBirth": verification.country_of_birth if verification else "",
            "nationality": verification.nationality if verification else "",
            "stateOfOrigin": verification.state_of_origin if verification else "",
            "lgaOfOrigin": verification.lga_of_origin if verification else "",
            "qualification": verification.qualification if verification else "",
            "documentUrls": _load_string_list(verification.document_urls if verification else ""),
            "homeCity": verification.city if verification else (user.location or ""),
            "homeState": verification.state if verification else (user.state or ""),
            "homeAddress": verification.address if verification else (user.address or ""),
            "city": verification.city if verification else (user.location or ""),
            "state": verification.state if verification else (user.state or ""),
            "address": verification.address if verification else (user.address or ""),
        })

    verification_data_str = request.data.get("verificationData")
    if verification_data_str:
        try:
            verification_data = json.loads(verification_data_str)
        except (TypeError, ValueError):
            return _bad_request("verificationData must be valid JSON")
        if not isinstance(verification_data, dict):
            return _bad_request("verificationData must be an object")
    else:
        verification_data = request.data

    def submitted(name, fallback=""):
        value = verification_data.get(name)
        return fallback if value is None else value

    existing_documents = _load_string_list(verification.document_urls if verification else "")
    profile_photo_url = submitted(
        "profilePhotoUrl",
        verification.profile_photo_url if verification else user.profile_photo_url,
    )
    date_of_birth = submitted(
        "dateOfBirth",
        _optional_date_iso(verification.date_of_birth if verification else user.date_of_birth),
    )
    mobile_number = submitted(
        "mobileNumber",
        verification.mobile_number if verification else user.mobile_number,
    )
    home_city = submitted("homeCity", submitted("city", verification.city if verification else user.location))
    home_state = submitted("homeState", submitted("state", verification.state if verification else user.state))
    home_address = submitted("homeAddress", submitted("address", verification.address if verification else user.address))
    qualification = submitted("qualification", verification.qualification if verification else "")
    nin_number = submitted("ninNumber", submitted("nin_number", verification.nin_number if verification else ""))
    bvn_number = submitted("bvnNumber", submitted("bvn_number", verification.bvn_number if verification else ""))
    country_of_birth = submitted("countryOfBirth", verification.country_of_birth if verification else "")
    nationality = submitted("nationality", verification.nationality if verification else "")
    state_of_origin = submitted("stateOfOrigin", verification.state_of_origin if verification else "")
    lga_of_origin = submitted("lgaOfOrigin", verification.lga_of_origin if verification else "")
    notes = submitted("notes", verification.notes if verification else "")
    document_urls = submitted("documentUrls", existing_documents)
    if isinstance(document_urls, str):
        document_urls = _load_string_list(document_urls)
    elif isinstance(document_urls, list):
        document_urls = [str(item).strip() for item in document_urls if str(item).strip()]

    has_split_name_fields = any(name in verification_data for name in ("firstName", "middleName", "lastName"))
    if has_split_name_fields:
        first_name = submitted("firstName")
        middle_name = submitted("middleName")
        last_name = submitted("lastName")
        full_name = _compose_full_name(first_name, middle_name, last_name)
    else:
        full_name = submitted("fullName", user.full_name or user.display_name)
        first_name, middle_name, last_name = _split_full_name(full_name)

    submitted_email = verification_data.get("email")
    if submitted_email is not None and str(submitted_email).strip().lower() != user.email.strip().lower():
        return _bad_request("Email must match the authenticated account email")

    try:
        normalized_mobile_number = _normalize_mobile_number(mobile_number, required=True)
        normalized_nin_number = _normalize_nin_number(nin_number, required=True)
        normalized_bvn_number = _normalize_bvn_number(bvn_number, required=False)
    except ValueError as exc:
        return _bad_request(str(exc))

    try:
        parsed_date_of_birth = dt.date.fromisoformat(str(date_of_birth).strip()[:10]) if date_of_birth else None
    except (TypeError, ValueError):
        return _bad_request("Invalid date of birth format")

    missing_fields: list[str] = []
    for name, value in (
        ("profilePhotoUrl", profile_photo_url),
        ("dateOfBirth", parsed_date_of_birth),
        ("mobileNumber", normalized_mobile_number),
        ("homeCity", home_city),
        ("homeState", home_state),
        ("homeAddress", home_address),
        ("qualification", qualification),
        ("firstName", first_name),
        ("lastName", last_name),
        ("countryOfBirth", country_of_birth),
        ("nationality", nationality),
        ("stateOfOrigin", state_of_origin),
        ("lgaOfOrigin", lga_of_origin),
        ("ninNumber", normalized_nin_number),
    ):
        if not str(value or "").strip():
            missing_fields.append(name)
    if not isinstance(document_urls, list) or len(document_urls) < 2:
        missing_fields.append("documentUrls")
    if missing_fields:
        return _bad_request(f"Missing required fields: {', '.join(missing_fields)}")

    if not getattr(settings, "BYPASS_VERIFICATION", False) and is_verification_configured():
        identity_data = {
            "first_name": str(first_name).strip(),
            "middle_name": str(middle_name or "").strip(),
            "last_name": str(last_name).strip(),
            "date_of_birth": parsed_date_of_birth,
            "mobile": normalized_mobile_number or "",
            "country_of_birth": str(country_of_birth).strip(),
            "nationality": str(nationality).strip(),
            "state_of_origin": str(state_of_origin).strip(),
            "lga": str(lga_of_origin).strip(),
        }
        try:
            if normalized_bvn_number:
                verify_nin_and_bvn(identity_data, normalized_nin_number, normalized_bvn_number)
            else:
                verify_nin_identity(
                    nin_number=normalized_nin_number,
                    first_name=str(first_name).strip(),
                    middle_name=str(middle_name or "").strip(),
                    last_name=str(last_name).strip(),
                    date_of_birth=parsed_date_of_birth,
                    mobile_number=normalized_mobile_number,
                )
        except (ValidationError, PremblyVerificationUnavailable, DikriptVerificationUnavailable) as exc:
            detail = getattr(exc, "detail", str(exc))
            return _bad_request(
                str(detail),
                status=503 if isinstance(exc, (PremblyVerificationUnavailable, DikriptVerificationUnavailable)) else 400,
            )

    verification, _ = StudentVerificationRequest.objects.update_or_create(
        user=user,
        defaults={
            "profile_photo_url": str(profile_photo_url).strip()[:500],
            "date_of_birth": parsed_date_of_birth,
            "mobile_number": normalized_mobile_number,
            "nin_number": normalized_nin_number,
            "bvn_number": normalized_bvn_number or "",
            "country_of_birth": str(country_of_birth).strip(),
            "nationality": str(nationality).strip(),
            "state_of_origin": str(state_of_origin).strip(),
            "lga_of_origin": str(lga_of_origin).strip(),
            "qualification": str(qualification).strip(),
            "document_urls": _dump_string_list(document_urls),
            "notes": str(notes or "").strip(),
            "city": str(home_city).strip(),
            "state": str(home_state).strip(),
            "address": str(home_address).strip(),
            "status": "approved",
            "reviewed_at": timezone.now(),
        },
    )

    user.full_name = str(full_name).strip()
    user.display_name = str(first_name).strip()
    user.profile_photo_url = verification.profile_photo_url
    user.date_of_birth = parsed_date_of_birth
    user.mobile_number = normalized_mobile_number
    user.location = verification.city
    user.state = verification.state
    user.address = verification.address
    user.save(update_fields=[
        "full_name", "display_name", "profile_photo_url", "date_of_birth", "mobile_number",
        "location", "state", "address",
    ])

    subject = "Profile Verification Confirmation"
    message = f"Hello {user.display_name},\n\nYour profile has been submitted and verified successfully.\n\nProfile Details:\n- Date of Birth: {parsed_date_of_birth}\n- Mobile: {normalized_mobile_number}\n- City: {verification.city}\n- State: {verification.state}\n- Address: {verification.address}\n\nYou can now contact tutors.\n\nBest regards,\nPrepVilla Team"
    _send_email(subject, message, [user.email])

    return JsonResponse({
        "status": verification.status,
        "message": "Profile submitted successfully and automatically verified. You can now contact tutors.",
        "submittedAt": verification.submitted_at.isoformat(),
        "decidedAt": verification.reviewed_at.isoformat() if verification.reviewed_at else None,
        "fullName": user.full_name,
        "firstName": first_name,
        "middleName": middle_name,
        "lastName": last_name,
        "email": user.email,
        "mobileNumber": user.mobile_number,
        "dateOfBirth": _optional_date_iso(user.date_of_birth),
        "countryOfBirth": verification.country_of_birth,
        "nationality": verification.nationality,
        "stateOfOrigin": verification.state_of_origin,
        "lgaOfOrigin": verification.lga_of_origin,
        "profilePhotoUrl": verification.profile_photo_url,
        "homeState": verification.state,
        "homeCity": verification.city,
        "homeAddress": verification.address,
        "qualification": verification.qualification,
        "ninNumber": verification.nin_number,
        "bvnNumber": verification.bvn_number,
        "documentUrls": _load_string_list(verification.document_urls),
    })

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_student_verifications(request):
    if request.method == "GET":
        status_filter = request.GET.get("status", "pending")
        verifications = StudentVerificationRequest.objects.filter(
            status=status_filter if status_filter != "all" else None
        ).select_related("user").order_by("-submitted_at")
        
        data = [{
            "id": str(v.id),
            "userId": str(v.user.id),
            "userName": v.user.display_name,
            "userEmail": v.user.email,
            "profilePhotoUrl": v.profile_photo_url,
            "dateOfBirth": v.date_of_birth.isoformat() if v.date_of_birth else None,
            "mobileNumber": v.mobile_number,
            "city": v.city,
            "state": v.state,
            "address": v.address,
            "status": v.status,
            "submittedAt": v.submitted_at.isoformat(),
            "reviewedAt": v.reviewed_at.isoformat() if v.reviewed_at else None,
            "adminNotes": v.admin_notes,
        } for v in verifications]
        
        return JsonResponse({"verifications": data})
    
    # POST - Approve/Reject verification request
    verification_id = request.data.get("verificationId")
    action = request.data.get("action")  # "approve" or "reject"
    admin_notes = request.data.get("adminNotes", "").strip()
    
    if not verification_id or action not in ["approve", "reject"]:
        return _bad_request("Invalid request data")
    
    try:
        verification = StudentVerificationRequest.objects.get(id=verification_id, status="pending")
    except StudentVerificationRequest.DoesNotExist:
        return _bad_request("Verification request not found or already processed")
    
    from django.utils import timezone
    
    if action == "approve":
        verification.status = "approved"
        # User can now contact tutors
    else:
        verification.status = "rejected"
    
    verification.reviewed_at = timezone.now()
    verification.reviewed_by = request.user
    verification.admin_notes = admin_notes
    verification.save()
    
    return JsonResponse({
        "id": str(verification.id),
        "status": verification.status,
        "message": f"Student verification request {action}d successfully",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscription_payment_checkout(request):
    plan = request.data.get("plan")
    try:
        result = create_subscription_checkout(user=request.user, plan=str(plan or "").strip())
    except (FlutterwaveError, ValidationError) as exc:
        detail = getattr(exc, "detail", str(exc))
        return _bad_request(str(detail), status=400 if isinstance(exc, ValidationError) else 503)
    return JsonResponse(result, status=201)


@api_view(["GET"])
@permission_classes([AllowAny])
def subscription_plans(request):
    return JsonResponse(get_subscription_plan_catalog())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_payments(request):
    payments = SubscriptionPayment.objects.filter(user=request.user).order_by("-created_at")
    results = []
    for payment in payments:
        plan = get_subscription_plan(payment.plan)
        duration_days = int(plan["duration_days"]) if plan else 30
        starts_at = payment.paid_at or payment.created_at
        expires_at = starts_at + timedelta(days=duration_days) if payment.status == SubscriptionPayment.Status.COMPLETED else None
        results.append({
            "id": str(payment.id),
            "plan": payment.plan,
            "planName": plan["name"] if plan else payment.plan.replace("_", " ").title(),
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "transactionId": payment.transaction_id,
            "paymentLink": payment.payment_link,
            "paidAt": payment.paid_at.isoformat() if payment.paid_at else None,
            "createdAt": payment.created_at.isoformat(),
            "expiresAt": expires_at.isoformat() if expires_at else None,
        })
    return JsonResponse({"results": results})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def booking_payment_checkout(request, booking_id):
    try:
        result = create_booking_checkout(user=request.user, booking_id=booking_id)
    except (FlutterwaveError, ValidationError) as exc:
        detail = getattr(exc, "detail", str(exc))
        return _bad_request(str(detail), status=400 if isinstance(exc, ValidationError) else 503)
    return JsonResponse(result, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_verify(request):
    transaction_id = request.GET.get("transaction_id") or request.GET.get("transactionId")
    tx_ref = request.GET.get("tx_ref") or request.GET.get("txRef") or ""
    if not transaction_id:
        return _bad_request("transaction_id is required")
    try:
        result = verify_customer_payment(
            user=request.user,
            transaction_id=str(transaction_id),
            tx_ref=str(tx_ref),
        )
    except (FlutterwaveError, ValidationError) as exc:
        detail = getattr(exc, "detail", str(exc))
        return _bad_request(str(detail), status=400 if isinstance(exc, ValidationError) else 503)
    return JsonResponse(result)


@api_view(["POST"])
@permission_classes([AllowAny])
def flutterwave_payment_webhook(request):
    raw_body = request.body
    signature = request.headers.get("verif-hash", "")
    hmac_signature = request.headers.get("flutterwave-signature", "")
    if not verify_webhook_signature(signature, raw_body, hmac_signature=hmac_signature):
        return _bad_request("Invalid Flutterwave webhook signature", status=401)
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _bad_request("Invalid webhook payload")
    event, created = record_flutterwave_webhook(body, raw_body)
    if not created and event.status in {event.Status.PROCESSED, event.Status.IGNORED}:
        return JsonResponse({"status": "accepted", "eventId": str(event.id), "duplicate": True})
    try:
        result = enqueue_payment_task(TASK_FLUTTERWAVE_WEBHOOK, {"event_id": str(event.id)})
    except (FlutterwaveError, ValidationError, RuntimeError) as exc:
        logger.exception("Flutterwave webhook queue failed")
        return _bad_request(str(getattr(exc, "detail", exc)), status=503)
    return JsonResponse({
        "status": "accepted",
        "eventId": str(event.id),
        "result": result if isinstance(result, dict) else None,
    })
