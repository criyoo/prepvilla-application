import datetime as dt
import hashlib
import json
import logging
import mimetypes
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import OperationalError, ProgrammingError, connection, transaction
from django.utils import timezone

from .models import (
    AppUser,
    SeededStudentAccount,
    SeededTutorAccount,
    StudentVerificationRequest,
    TutorProfile,
    VerificationRequest,
)
from .tutor_sync import apply_verified_tutor_fields

logger = logging.getLogger(__name__)

_startup_sync_attempted = False
_student_startup_sync_attempted = False


@dataclass
class DefaultTutorSeed:
    seed_key: str
    email: str
    password: str
    first_name: str
    last_name: str
    full_name: str
    mobile_number: str
    date_of_birth: dt.date
    home_state: str
    home_city: str
    home_address: str
    qualification: str
    nin_number: str
    state_of_origin: str
    headline: str
    bio: str
    hourly_rate: int
    subjects: list[str]
    languages: list[str]
    gender: str
    first_lesson_free: bool
    offers_face_to_face: bool
    offers_webcam: bool
    profile_photo_source: Path
    id_document_source: Path | None
    qualification_document_source: Path | None
    source_hash: str


@dataclass
class DefaultStudentSeed:
    seed_key: str
    email: str
    password: str
    first_name: str
    last_name: str
    full_name: str
    mobile_number: str
    date_of_birth: dt.date
    state: str
    city: str
    address: str
    profile_photo_source: Path
    source_hash: str


def seed_demo_accounts_tutors_after_migrate(sender, **kwargs):
    if getattr(sender, "label", "") != "core":
        return
    seed_demo_accounts_tutors()


def seed_demo_accounts_tutors_on_startup():
    global _startup_sync_attempted
    if _startup_sync_attempted:
        return
    _startup_sync_attempted = True
    seed_demo_accounts_tutors()


def seed_demo_accounts_students_after_migrate(sender, **kwargs):
    if getattr(sender, "label", "") != "core":
        return
    seed_demo_accounts_students()


def seed_demo_accounts_students_on_startup():
    global _student_startup_sync_attempted
    if _student_startup_sync_attempted:
        return
    _student_startup_sync_attempted = True
    seed_demo_accounts_students()


def seed_demo_accounts_tutors(*, force: bool = False) -> dict[str, int]:
    if not _seed_demo_accounts_tutors_enabled(force=force):
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}
    if not _seed_demo_accounts_tutors_tables_ready():
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    seed_file = _resolve_seed_file_path(settings.DEFAULT_TUTOR_SEED_PATH)
    if not seed_file.exists():
        logger.info("Default tutor seed file not found at %s; skipping sync", seed_file)
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    payload = _load_seed_payload(seed_file, "tutor")
    if payload is None:
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    if not isinstance(payload, dict):
        logger.warning("Default tutor seed file must contain an object keyed by tutor slug")
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    results = {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}
    declared_seed_keys = {str(key).strip() for key in payload.keys() if str(key).strip()}
    trackers = {
        tracker.seed_key: tracker
        for tracker in SeededTutorAccount.objects.select_related("user").all()
    }

    for raw_seed_key, raw_entry in payload.items():
        seed_key = str(raw_seed_key).strip()
        if not seed_key:
            results["skipped"] += 1
            continue

        seed = _parse_default_tutor_seed(seed_key, raw_entry)
        if not seed:
            results["skipped"] += 1
            continue

        outcome = _upsert_seeded_tutor(seed_key, seed, trackers.get(seed_key))
        results[outcome] += 1

    for seed_key, tracker in trackers.items():
        if seed_key in declared_seed_keys:
            continue
        _delete_seeded_tutor(tracker)
        results["deleted"] += 1

    if any(results.values()):
        logger.info("Default tutor seed sync finished: %s", results)
    return results


def seed_demo_accounts_students(*, force: bool = False) -> dict[str, int]:
    if not _seed_demo_accounts_students_enabled(force=force):
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}
    if not _seed_demo_accounts_students_tables_ready():
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    seed_file = _resolve_seed_file_path(settings.DEFAULT_STUDENT_SEED_PATH)
    if not seed_file.exists():
        logger.info("Default student seed file not found at %s; skipping sync", seed_file)
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    payload = _load_seed_payload(seed_file, "student")
    if payload is None:
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    if not isinstance(payload, dict):
        logger.warning("Default student seed file must contain an object keyed by student slug")
        return {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    results = {"created": 0, "updated": 0, "deleted": 0, "skipped": 0}
    declared_seed_keys = {str(key).strip() for key in payload.keys() if str(key).strip()}
    trackers = {
        tracker.seed_key: tracker
        for tracker in SeededStudentAccount.objects.select_related("user").all()
    }

    for raw_seed_key, raw_entry in payload.items():
        seed_key = str(raw_seed_key).strip()
        if not seed_key:
            results["skipped"] += 1
            continue

        seed = _parse_default_student_seed(seed_key, raw_entry)
        if not seed:
            results["skipped"] += 1
            continue

        outcome = _upsert_seeded_student(seed_key, seed, trackers.get(seed_key))
        results[outcome] += 1

    for seed_key, tracker in trackers.items():
        if seed_key in declared_seed_keys:
            continue
        _delete_seeded_student(tracker)
        results["deleted"] += 1

    if any(results.values()):
        logger.info("Default student seed sync finished: %s", results)
    return results


def _seed_demo_accounts_tutors_enabled(*, force: bool = False) -> bool:
    environment = getattr(settings, "ENVIRONMENT", "").lower()
    if environment in {"production", "prod"}:
        return False
    if force:
        return True
    return bool(
        getattr(settings, "SEED_DEMO_ACCOUNTS", False)
        and environment in {"development", "dev", "local"}
        and "test" not in sys.argv
    )


def _seed_demo_accounts_students_enabled(*, force: bool = False) -> bool:
    environment = getattr(settings, "ENVIRONMENT", "").lower()
    if environment in {"production", "prod"}:
        return False
    if force:
        return True
    return bool(
        getattr(settings, "SEED_DEMO_ACCOUNTS", False)
        and environment in {"development", "dev", "local"}
        and "test" not in sys.argv
    )


def _seed_demo_accounts_tutors_tables_ready() -> bool:
    required_tables = {
        AppUser._meta.db_table,
        TutorProfile._meta.db_table,
        VerificationRequest._meta.db_table,
        SeededTutorAccount._meta.db_table,
    }
    try:
        existing_tables = set(connection.introspection.table_names())
    except (OperationalError, ProgrammingError):
        logger.debug("Default tutor seed sync skipped because database tables are not ready", exc_info=True)
        return False
    return required_tables.issubset(existing_tables)


def _seed_demo_accounts_students_tables_ready() -> bool:
    required_tables = {
        AppUser._meta.db_table,
        StudentVerificationRequest._meta.db_table,
        SeededStudentAccount._meta.db_table,
    }
    try:
        existing_tables = set(connection.introspection.table_names())
    except (OperationalError, ProgrammingError):
        logger.debug("Default student seed sync skipped because database tables are not ready", exc_info=True)
        return False
    return required_tables.issubset(existing_tables)


def _load_seed_payload(seed_file: Path, entity_label: str):
    try:
        raw_text = seed_file.read_text(encoding="utf-8")
    except Exception:
        logger.exception("Failed to read default %s seed file at %s", entity_label, seed_file)
        return None

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        normalized_text = re.sub(r",(\s*[}\]])", r"\1", raw_text)
        if normalized_text == raw_text:
            logger.exception("Failed to parse default %s seed file at %s", entity_label, seed_file)
            return None
        try:
            payload = json.loads(normalized_text)
        except Exception:
            logger.exception("Failed to parse default %s seed file at %s", entity_label, seed_file)
            return None
        logger.warning(
            "Default %s seed file at %s contained trailing commas; parsed after normalization",
            entity_label,
            seed_file,
        )
        return payload
    except Exception:
        logger.exception("Failed to parse default %s seed file at %s", entity_label, seed_file)
        return None


def _parse_default_tutor_seed(seed_key: str, raw_entry) -> DefaultTutorSeed | None:
    if not isinstance(raw_entry, dict):
        logger.warning("Skipping tutor seed %s because the entry is not an object", seed_key)
        return None

    sign_up = raw_entry.get("sign_up")
    if not isinstance(sign_up, dict):
        sign_up = {}
    verification = raw_entry.get("verification")
    if not isinstance(verification, dict):
        verification = {}
    residence = verification.get("residence")
    if not isinstance(residence, dict):
        residence = {}
    profile = raw_entry.get("profile")
    if not isinstance(profile, dict):
        profile = {}
    basic_information = profile.get("basic_information")
    if not isinstance(basic_information, dict):
        basic_information = {}
    tutor_profile = profile.get("tutor_profile")
    if not isinstance(tutor_profile, dict):
        tutor_profile = {}
    teaching_methods = tutor_profile.get("teaching_methods")
    if not isinstance(teaching_methods, dict):
        teaching_methods = {}

    raw_full_name = _clean_string(sign_up.get("full_name") or raw_entry.get("full_name"))
    name_parts = [part for part in raw_full_name.split() if part]
    first_name = _clean_string(sign_up.get("first_name") or raw_entry.get("first_name") or (name_parts[0] if name_parts else ""))
    last_name = _clean_string(sign_up.get("last_name") or raw_entry.get("last_name") or (" ".join(name_parts[1:]) if len(name_parts) > 1 else ""))
    password = _clean_string(sign_up.get("password") or raw_entry.get("password"))
    email = _clean_string(raw_entry.get("email") or sign_up.get("email")).lower()
    mobile_number = _clean_string(verification.get("mobile_number"))
    qualification = _clean_string(residence.get("qualification"))
    nin_number = _clean_string(residence.get("nin_number"))
    state_of_origin = _clean_string(basic_information.get("state_of_origin"))
    headline = _clean_string(tutor_profile.get("headline"))
    bio = _clean_string(tutor_profile.get("about"))
    gender = _clean_string(tutor_profile.get("gender"))
    home_state = _clean_string(residence.get("state"))
    home_city = _clean_string(residence.get("city"))
    home_address = _clean_string(residence.get("address"))

    date_of_birth = _parse_seed_date(verification.get("date_of_birth"))
    hourly_rate = _parse_hourly_rate(tutor_profile.get("hourly_rate"))
    subjects = _clean_string_list(tutor_profile.get("subjects"))
    languages = _clean_string_list(tutor_profile.get("languages") or tutor_profile.get("language"))
    first_lesson_free = bool(
        tutor_profile.get("first_lesson_free")
        if "first_lesson_free" in tutor_profile
        else tutor_profile.get("firs_lesson_free")
    )
    offers_face_to_face = bool(teaching_methods.get("face_to_face"))
    offers_webcam = bool(teaching_methods.get("webcam"))

    profile_photo_source = _resolve_seed_asset_path(residence.get("profile_photo"))
    id_document_source = _resolve_seed_asset_path(residence.get("id_document"))
    qualification_document_source = _resolve_seed_asset_path(residence.get("qualification_document"))

    required_values = {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "mobile_number": mobile_number,
        "qualification": qualification,
        "nin_number": nin_number,
        "home_state": home_state,
        "home_city": home_city,
        "home_address": home_address,
        "headline": headline,
        "bio": bio,
    }
    missing_fields = [name for name, value in required_values.items() if not value]
    if date_of_birth is None:
        missing_fields.append("date_of_birth")
    if hourly_rate is None:
        missing_fields.append("hourly_rate")
    if not subjects:
        missing_fields.append("subjects")
    if not languages:
        missing_fields.append("languages")
    if profile_photo_source is None:
        missing_fields.append("profile_photo")

    if missing_fields:
        logger.warning(
            "Skipping tutor seed %s because required fields are missing or invalid: %s",
            seed_key,
            ", ".join(missing_fields),
        )
        return None

    normalized_seed = {
        "seed_key": seed_key,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "mobile_number": mobile_number,
        "date_of_birth": date_of_birth.isoformat(),
        "home_state": home_state,
        "home_city": home_city,
        "home_address": home_address,
        "qualification": qualification,
        "nin_number": nin_number,
        "state_of_origin": state_of_origin,
        "headline": headline,
        "bio": bio,
        "hourly_rate": hourly_rate,
        "subjects": subjects,
        "languages": languages,
        "gender": gender,
        "first_lesson_free": first_lesson_free,
        "offers_face_to_face": offers_face_to_face,
        "offers_webcam": offers_webcam,
        "profile_photo_source": str(profile_photo_source),
        "id_document_source": str(id_document_source) if id_document_source else "",
        "qualification_document_source": str(qualification_document_source) if qualification_document_source else "",
    }
    source_hash = hashlib.sha256(
        json.dumps(normalized_seed, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return DefaultTutorSeed(
        seed_key=seed_key,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        full_name=f"{first_name} {last_name}".strip(),
        mobile_number=mobile_number,
        date_of_birth=date_of_birth,
        home_state=home_state,
        home_city=home_city,
        home_address=home_address,
        qualification=qualification,
        nin_number=nin_number,
        state_of_origin=state_of_origin,
        headline=headline,
        bio=bio,
        hourly_rate=hourly_rate,
        subjects=subjects,
        languages=languages,
        gender=gender,
        first_lesson_free=first_lesson_free,
        offers_face_to_face=offers_face_to_face,
        offers_webcam=offers_webcam,
        profile_photo_source=profile_photo_source,
        id_document_source=id_document_source,
        qualification_document_source=qualification_document_source,
        source_hash=source_hash,
    )


def _parse_default_student_seed(seed_key: str, raw_entry) -> DefaultStudentSeed | None:
    if not isinstance(raw_entry, dict):
        logger.warning("Skipping student seed %s because the entry is not an object", seed_key)
        return None

    sign_up = raw_entry.get("sign_up")
    if not isinstance(sign_up, dict):
        sign_up = {}
    profile = raw_entry.get("profile")
    if not isinstance(profile, dict):
        profile = {}
    basic_information = profile.get("basic_information")
    if not isinstance(basic_information, dict):
        basic_information = {}

    raw_full_name = _clean_string(sign_up.get("full_name") or raw_entry.get("full_name"))
    name_parts = [part for part in raw_full_name.split() if part]
    first_name = _clean_string(sign_up.get("first_name") or raw_entry.get("first_name") or (name_parts[0] if name_parts else ""))
    last_name = _clean_string(sign_up.get("last_name") or raw_entry.get("last_name") or (" ".join(name_parts[1:]) if len(name_parts) > 1 else ""))
    password = _clean_string(sign_up.get("password") or raw_entry.get("password"))
    email = _clean_string(raw_entry.get("email") or sign_up.get("email")).lower()
    state = _clean_string(basic_information.get("state"))
    city = _clean_string(basic_information.get("city"))
    address = _clean_string(basic_information.get("address"))
    mobile_number = _clean_string(basic_information.get("mobile_number"))
    date_of_birth = _parse_seed_date(basic_information.get("date_of_birth"))
    profile_photo_source = _resolve_seed_asset_path(basic_information.get("profile_photo"))

    required_values = {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "mobile_number": mobile_number,
        "state": state,
        "city": city,
        "address": address,
    }
    missing_fields = [name for name, value in required_values.items() if not value]
    if date_of_birth is None:
        missing_fields.append("date_of_birth")
    if profile_photo_source is None:
        missing_fields.append("profile_photo")

    if missing_fields:
        logger.warning(
            "Skipping student seed %s because required fields are missing or invalid: %s",
            seed_key,
            ", ".join(missing_fields),
        )
        return None

    normalized_seed = {
        "seed_key": seed_key,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "mobile_number": mobile_number,
        "date_of_birth": date_of_birth.isoformat(),
        "state": state,
        "city": city,
        "address": address,
        "profile_photo_source": str(profile_photo_source),
    }
    source_hash = hashlib.sha256(
        json.dumps(normalized_seed, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return DefaultStudentSeed(
        seed_key=seed_key,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        full_name=f"{first_name} {last_name}".strip(),
        mobile_number=mobile_number,
        date_of_birth=date_of_birth,
        state=state,
        city=city,
        address=address,
        profile_photo_source=profile_photo_source,
        source_hash=source_hash,
    )


def _upsert_seeded_tutor(seed_key: str, seed: DefaultTutorSeed, tracker: SeededTutorAccount | None) -> str:
    existing_user = tracker.user if tracker else AppUser.objects.filter(email=seed.email).first()
    if existing_user and existing_user.role != "tutor":
        logger.warning(
            "Skipping tutor seed %s because %s already belongs to a non-tutor account",
            seed_key,
            seed.email,
        )
        return "skipped"

    conflicting_user = AppUser.objects.filter(email=seed.email).exclude(
        id=existing_user.id if existing_user else None
    ).first()
    if conflicting_user:
        logger.warning(
            "Skipping tutor seed %s because %s is already used by another account",
            seed_key,
            seed.email,
        )
        return "skipped"

    previously_managed_paths = _load_json_list(tracker.managed_paths if tracker else "")
    managed_paths: list[str] = []

    photo_path, photo_url = _store_seed_asset(
        seed.seed_key,
        "profile_photo",
        seed.profile_photo_source,
        "images/tutors/seed",
    )
    managed_paths.append(photo_path)

    document_urls: list[str] = []
    if seed.id_document_source:
        id_path, id_url = _store_seed_asset(
            seed.seed_key,
            "id_document",
            seed.id_document_source,
            "documents/tutors/seed",
        )
        managed_paths.append(id_path)
        document_urls.append(id_url)
    else:
        logger.warning("Tutor seed %s is missing the ID document asset; continuing without it", seed_key)

    if seed.qualification_document_source:
        qualification_path, qualification_url = _store_seed_asset(
            seed.seed_key,
            "qualification_document",
            seed.qualification_document_source,
            "documents/tutors/seed",
        )
        managed_paths.append(qualification_path)
        document_urls.append(qualification_url)
    else:
        logger.warning(
            "Tutor seed %s is missing the qualification document asset; continuing without it",
            seed_key,
        )

    document_urls_json = json.dumps(document_urls)
    outcome = "updated" if existing_user else "created"
    now = timezone.now()

    with transaction.atomic():
        if existing_user:
            user = existing_user
        else:
            user = AppUser(
                email=seed.email,
                role="tutor",
                display_name=seed.first_name,
                timezone="Africa/Lagos",
            )

        user.email = seed.email
        user.role = "tutor"
        user.timezone = (user.timezone or "Africa/Lagos").strip() or "Africa/Lagos"
        user.is_verified = True
        user.is_active = True
        user.set_password(seed.password)
        user.save()

        tutor_profile, _ = TutorProfile.objects.get_or_create(
            user=user,
            defaults={
                "headline": "",
                "bio": "",
                "subjects_csv": "",
                "hourly_rate_cents": 0,
                "languages_csv": "",
            },
        )
        tutor_profile.headline = seed.headline
        tutor_profile.bio = seed.bio
        tutor_profile.subjects_csv = ",".join(seed.subjects)
        tutor_profile.languages_csv = ",".join(seed.languages)
        tutor_profile.hourly_rate_cents = seed.hourly_rate * 100
        tutor_profile.gender = seed.gender
        tutor_profile.state_of_origin = seed.state_of_origin
        tutor_profile.first_lesson_free = seed.first_lesson_free
        tutor_profile.offers_face_to_face = seed.offers_face_to_face or not seed.offers_webcam
        tutor_profile.offers_webcam = seed.offers_webcam
        tutor_profile.save(
            update_fields=[
                "headline",
                "bio",
                "subjects_csv",
                "languages_csv",
                "hourly_rate_cents",
                "gender",
                "state_of_origin",
                "first_lesson_free",
                "offers_face_to_face",
                "offers_webcam",
            ]
        )

        verification, _ = VerificationRequest.objects.get_or_create(tutor_profile=tutor_profile)
        verification.status = "approved"
        verification.home_state = seed.home_state
        verification.home_city = seed.home_city
        verification.home_address = seed.home_address
        verification.qualification = seed.qualification
        verification.nin_number = seed.nin_number
        verification.profile_photo_url = photo_url
        verification.document_urls = document_urls_json
        verification.notes = "Managed by the default tutor seed sync."
        verification.decided_at = now
        verification.save()

        apply_verified_tutor_fields(
            user,
            tutor_profile,
            full_name=seed.full_name,
            mobile_number=seed.mobile_number,
            date_of_birth=seed.date_of_birth,
            home_state=seed.home_state,
            home_city=seed.home_city,
            home_address=seed.home_address,
            qualification=seed.qualification,
            nin_number=seed.nin_number,
            profile_photo_url=photo_url,
            document_urls=document_urls_json,
            verification_status="approved",
            is_listed=True,
        )

        if tracker is None:
            tracker = SeededTutorAccount(user=user, seed_key=seed_key)
        tracker.user = user
        tracker.seed_key = seed_key
        tracker.source_hash = seed.source_hash
        tracker.managed_paths = json.dumps(managed_paths)
        tracker.save()

    _delete_stale_managed_paths(previously_managed_paths, managed_paths)
    return outcome


def _upsert_seeded_student(seed_key: str, seed: DefaultStudentSeed, tracker: SeededStudentAccount | None) -> str:
    existing_user = tracker.user if tracker else AppUser.objects.filter(email=seed.email).first()
    if existing_user and existing_user.role != "student":
        logger.warning(
            "Skipping student seed %s because %s already belongs to a non-student account",
            seed_key,
            seed.email,
        )
        return "skipped"

    conflicting_user = AppUser.objects.filter(email=seed.email).exclude(
        id=existing_user.id if existing_user else None
    ).first()
    if conflicting_user:
        logger.warning(
            "Skipping student seed %s because %s is already used by another account",
            seed_key,
            seed.email,
        )
        return "skipped"

    previously_managed_paths = _load_json_list(tracker.managed_paths if tracker else "")
    managed_paths: list[str] = []

    photo_path, photo_url = _store_seed_asset(
        seed.seed_key,
        "profile_photo",
        seed.profile_photo_source,
        "images/students/seed",
    )
    managed_paths.append(photo_path)

    outcome = "updated" if existing_user else "created"
    now = timezone.now()

    with transaction.atomic():
        if existing_user:
            user = existing_user
        else:
            user = AppUser(
                email=seed.email,
                role="student",
                display_name=seed.first_name,
                timezone="Africa/Lagos",
            )

        user.email = seed.email
        user.role = "student"
        user.display_name = seed.first_name
        user.full_name = seed.full_name
        user.timezone = (user.timezone or "Africa/Lagos").strip() or "Africa/Lagos"
        user.is_verified = True
        user.is_active = True
        user.mobile_number = seed.mobile_number
        user.date_of_birth = seed.date_of_birth
        user.profile_photo_url = photo_url
        user.location = seed.city
        user.state = seed.state
        user.address = seed.address
        user.set_password(seed.password)
        user.save()

        verification, _ = StudentVerificationRequest.objects.get_or_create(
            user=user,
            defaults={
                "profile_photo_url": photo_url,
                "date_of_birth": seed.date_of_birth,
                "mobile_number": seed.mobile_number,
                "city": seed.city,
                "state": seed.state,
                "address": seed.address,
                "status": "approved",
                "reviewed_at": now,
                "admin_notes": "Managed by the default student seed sync.",
            },
        )
        verification.profile_photo_url = photo_url
        verification.date_of_birth = seed.date_of_birth
        verification.mobile_number = seed.mobile_number
        verification.city = seed.city
        verification.state = seed.state
        verification.address = seed.address
        verification.status = "approved"
        verification.reviewed_at = now
        verification.reviewed_by = None
        verification.admin_notes = "Managed by the default student seed sync."
        verification.save()

        if tracker is None:
            tracker = SeededStudentAccount(user=user, seed_key=seed_key)
        tracker.user = user
        tracker.seed_key = seed_key
        tracker.source_hash = seed.source_hash
        tracker.managed_paths = json.dumps(managed_paths)
        tracker.save()

    _delete_stale_managed_paths(previously_managed_paths, managed_paths)
    return outcome


def _delete_seeded_tutor(tracker: SeededTutorAccount):
    storage_paths = _load_json_list(tracker.managed_paths)
    user = tracker.user
    with transaction.atomic():
        tracker.delete()
        user.delete()
    _delete_stale_managed_paths(storage_paths, [])


def _delete_seeded_student(tracker: SeededStudentAccount):
    storage_paths = _load_json_list(tracker.managed_paths)
    user = tracker.user
    with transaction.atomic():
        tracker.delete()
        user.delete()
    _delete_stale_managed_paths(storage_paths, [])


def _delete_stale_managed_paths(existing_paths: list[str], current_paths: list[str]):
    current_set = set(current_paths)
    for path in existing_paths:
        if path in current_set:
            continue
        try:
            default_storage.delete(path)
        except Exception:
            logger.exception("Failed to delete stale default seed asset %s", path)


def _store_seed_asset(seed_key: str, label: str, source_path: Path, target_dir: str) -> tuple[str, str]:
    extension = source_path.suffix.lower() or ".bin"
    storage_key = f"{_safe_part(seed_key, 'seed')}_{_safe_part(label, 'asset')}{extension}"
    storage_path = f"{target_dir}/{storage_key}"
    if default_storage.exists(storage_path):
        default_storage.delete(storage_path)
    content = ContentFile(source_path.read_bytes(), name=source_path.name)
    content_type, _encoding = mimetypes.guess_type(source_path.name)
    if content_type:
        content.content_type = content_type
    saved_path = default_storage.save(storage_path, content)
    return saved_path, _public_storage_url(saved_path)


def _public_storage_url(path: str) -> str:
    url = default_storage.url(path)
    internal_endpoint = str(getattr(settings, "AWS_S3_ENDPOINT_URL", "") or "").rstrip("/")
    public_endpoint = str(getattr(settings, "AWS_S3_PUBLIC_ENDPOINT_URL", "") or "").rstrip("/")
    if internal_endpoint and public_endpoint:
        parsed = urlparse(url)
        internal = urlparse(internal_endpoint)
        public = urlparse(public_endpoint)
        if parsed.netloc == internal.netloc and public.scheme and public.netloc:
            return parsed._replace(
                scheme=public.scheme,
                netloc=public.netloc,
            ).geturl()
    return url


def _parse_seed_date(value) -> dt.date | None:
    text = _clean_string(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_hourly_rate(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        amount = int(value)
        return amount if amount > 0 else None
    text = _clean_string(value)
    if not text:
        return None
    text = text.replace(",", "")
    if not re.fullmatch(r"\d+", text):
        return None
    amount = int(text)
    return amount if amount > 0 else None


def _resolve_seed_asset_path(value) -> Path | None:
    text = _clean_string(value)
    if not text:
        return None

    base_dir = Path(settings.BASE_DIR)
    repository_root = base_dir
    if len(base_dir.parents) > 1:
        repository_root = base_dir.parents[1]
    candidates = [
        Path(text),
        base_dir / text,
        base_dir.parent / text,
        repository_root / text,
    ]
    for prefix in ("apps/api/", "api/"):
        if prefix in text:
            candidates.append(base_dir / text.split(prefix, 1)[1])

    for candidate in candidates:
        resolved = candidate.expanduser()
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _resolve_seed_file_path(value) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(settings.BASE_DIR) / path


def _load_json_list(value: str | None) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        parsed = None
    if not isinstance(parsed, list):
        return []
    results: list[str] = []
    for item in parsed:
        text = _clean_string(item)
        if text:
            results.append(text)
    return results


def _clean_string(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    results: list[str] = []
    for item in value:
        text = _clean_string(item)
        if text:
            results.append(text)
    return results


def _safe_part(value: str, fallback: str) -> str:
    normalized = re.sub(r"\s+", "_", (value or "").strip().lower())
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or fallback
