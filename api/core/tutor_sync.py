import datetime as dt

from .models import AppUser, TutorProfile


APPROVED_TUTOR_STATUSES = {"approved", "verified"}


def normalize_tutor_verification_status(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in APPROVED_TUTOR_STATUSES:
        return "approved"
    if normalized in {"pending", "rejected", "not_submitted"}:
        return normalized
    return "not_submitted"


def first_name_from_full_name(full_name: str | None, fallback: str = "Tutor") -> str:
    normalized = (full_name or "").strip()
    if not normalized:
        return fallback
    return normalized.split()[0]


def apply_verified_tutor_fields(
    user: AppUser,
    tutor_profile: TutorProfile,
    *,
    full_name: str | None,
    mobile_number: str | None,
    date_of_birth: dt.date | None,
    home_state: str | None,
    home_city: str | None,
    home_address: str | None,
    qualification: str | None,
    nin_number: str | None,
    profile_photo_url: str | None,
    document_urls: str | None,
    bvn_number: str | None = None,
    state_of_origin: str | None = None,
    lga_of_origin: str | None = None,
    country_of_birth: str | None = None,
    nationality: str | None = None,
    verification_status: str | None = None,
    is_listed: bool | None = None,
):
    normalized_full_name = (full_name or "").strip()
    normalized_display_name = first_name_from_full_name(
        normalized_full_name,
        fallback=(user.display_name or "Tutor").strip() or "Tutor",
    )
    normalized_home_state = (home_state or "").strip()
    normalized_home_city = (home_city or "").strip()
    normalized_home_address = (home_address or "").strip()
    normalized_qualification = (qualification or "").strip()
    normalized_nin_number = (nin_number or "").strip()
    normalized_bvn_number = (bvn_number or "").strip()
    normalized_state_of_origin = (state_of_origin or "").strip()
    normalized_lga_of_origin = (lga_of_origin or "").strip()
    normalized_country_of_birth = (country_of_birth or "").strip()
    normalized_nationality = (nationality or "").strip()
    normalized_profile_photo_url = (profile_photo_url or "").strip()[:500]
    normalized_user_profile_photo_url = normalized_profile_photo_url[:200]
    normalized_document_urls = document_urls or ""

    user_changed_fields: list[str] = []
    tutor_changed_fields: list[str] = []

    if user.full_name != normalized_full_name:
        user.full_name = normalized_full_name
        user_changed_fields.append("full_name")
    if user.display_name != normalized_display_name:
        user.display_name = normalized_display_name
        user_changed_fields.append("display_name")
    if mobile_number is not None and user.mobile_number != mobile_number:
        user.mobile_number = mobile_number
        user_changed_fields.append("mobile_number")
    if date_of_birth is not None and user.date_of_birth != date_of_birth:
        user.date_of_birth = date_of_birth
        user_changed_fields.append("date_of_birth")
    if user.state != normalized_home_state:
        user.state = normalized_home_state
        user_changed_fields.append("state")
    if user.location != normalized_home_city:
        user.location = normalized_home_city
        user_changed_fields.append("location")
    if user.address != normalized_home_address:
        user.address = normalized_home_address
        user_changed_fields.append("address")
    if user.profile_photo_url != normalized_user_profile_photo_url:
        user.profile_photo_url = normalized_user_profile_photo_url
        user_changed_fields.append("profile_photo_url")

    if tutor_profile.home_state != normalized_home_state:
        tutor_profile.home_state = normalized_home_state
        tutor_changed_fields.append("home_state")
    if tutor_profile.home_city != normalized_home_city:
        tutor_profile.home_city = normalized_home_city
        tutor_changed_fields.append("home_city")
    if tutor_profile.home_address != normalized_home_address:
        tutor_profile.home_address = normalized_home_address
        tutor_changed_fields.append("home_address")
    if tutor_profile.qualification != normalized_qualification:
        tutor_profile.qualification = normalized_qualification
        tutor_changed_fields.append("qualification")
    if tutor_profile.nin_number != normalized_nin_number:
        tutor_profile.nin_number = normalized_nin_number
        tutor_changed_fields.append("nin_number")
    if bvn_number is not None and tutor_profile.bvn_number != normalized_bvn_number:
        tutor_profile.bvn_number = normalized_bvn_number
        tutor_changed_fields.append("bvn_number")
    if state_of_origin is not None and tutor_profile.state_of_origin != normalized_state_of_origin:
        tutor_profile.state_of_origin = normalized_state_of_origin
        tutor_changed_fields.append("state_of_origin")
    if lga_of_origin is not None and tutor_profile.lga_of_origin != normalized_lga_of_origin:
        tutor_profile.lga_of_origin = normalized_lga_of_origin
        tutor_changed_fields.append("lga_of_origin")
    if country_of_birth is not None and tutor_profile.country_of_birth != normalized_country_of_birth:
        tutor_profile.country_of_birth = normalized_country_of_birth
        tutor_changed_fields.append("country_of_birth")
    if nationality is not None and tutor_profile.nationality != normalized_nationality:
        tutor_profile.nationality = normalized_nationality
        tutor_changed_fields.append("nationality")
    if tutor_profile.profile_photo_url != normalized_profile_photo_url:
        tutor_profile.profile_photo_url = normalized_profile_photo_url
        tutor_changed_fields.append("profile_photo_url")
    if tutor_profile.document_urls != normalized_document_urls:
        tutor_profile.document_urls = normalized_document_urls
        tutor_changed_fields.append("document_urls")
    if verification_status is not None and tutor_profile.verification_status != verification_status:
        tutor_profile.verification_status = verification_status
        tutor_changed_fields.append("verification_status")
    if is_listed is not None and tutor_profile.is_listed != is_listed:
        tutor_profile.is_listed = is_listed
        tutor_changed_fields.append("is_listed")

    if user_changed_fields:
        user.save(update_fields=user_changed_fields)
    if tutor_changed_fields:
        tutor_profile.save(update_fields=tutor_changed_fields)
