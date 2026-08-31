import hashlib
import os
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import dj_database_url


BASE_DIR = Path(__file__).resolve().parents[2]


def env_bool(name: str, default: bool = False) -> bool:
  value = os.environ.get(name)
  if value is None:
    return default
  return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
  value = os.environ.get(name)
  if value is None:
    return default
  try:
    return int(value)
  except (TypeError, ValueError):
    return default


def env_list(name: str, default: str = "") -> list[str]:
  return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def postgres_database_url() -> str:
  explicit_url = os.environ.get("POSTGRES_DATABASE_URL", "").strip()
  if explicit_url:
    return explicit_url

  host = os.environ.get("POSTGRES_HOST", "").strip()
  name = os.environ.get("POSTGRES_DB", "").strip()
  user = os.environ.get("POSTGRES_USER", "").strip()
  password = os.environ.get("POSTGRES_PASSWORD", "")
  port = os.environ.get("POSTGRES_PORT", "5432").strip() or "5432"

  if host and name and user:
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}"

  return f"sqlite:///{BASE_DIR / 'db.sqlite3'}"


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = env_bool("DJANGO_DEBUG", False)
ENVIRONMENT = os.environ.get(
  "DJANGO_ENV",
  os.environ.get("ENVIRONMENT", "development" if DEBUG else "production"),
).strip().lower()
ENFORCE_PRODUCTION_HARDENING = env_bool(
  "ENFORCE_PRODUCTION_HARDENING",
  ENVIRONMENT in {"prod", "production"},
)

if not DEBUG and SECRET_KEY == "dev-secret-key" and ENVIRONMENT in {"prod", "production"}:
  raise RuntimeError("DJANGO_SECRET_KEY must be set when DEBUG is disabled")

ALLOWED_HOSTS = env_list(
  "DJANGO_ALLOWED_HOSTS",
  "localhost,127.0.0.1,api,prepvilla-api,dev.prepvilla.info,api.dev.prepvilla.info,prepvilla.info",
)

INSTALLED_APPS = [
  "django.contrib.admin",
  "django.contrib.auth",
  "django.contrib.contenttypes",
  "django.contrib.sessions",
  "django.contrib.messages",
  "django.contrib.staticfiles",
  "corsheaders",
  "rest_framework",
  "channels",
  "storages",
  "core",
]

MIDDLEWARE = [
  "core.middleware.HealthCheckHostBypassMiddleware",
  "corsheaders.middleware.CorsMiddleware",
  "django.middleware.security.SecurityMiddleware",
  "whitenoise.middleware.WhiteNoiseMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.middleware.common.CommonMiddleware",
  "django.middleware.csrf.CsrfViewMiddleware",
  "django.contrib.auth.middleware.AuthenticationMiddleware",
  "django.contrib.messages.middleware.MessageMiddleware",
  "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
  {
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
      "context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
      ]
    },
  }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
  "default": dj_database_url.parse(
    postgres_database_url(),
    conn_max_age=env_int("POSTGRES_DATABASE_CONN_MAX_AGE", 600),
    ssl_require=env_bool("POSTGRES_DATABASE_SSL_REQUIRE", not DEBUG),
  )
}

AUTH_USER_MODEL = "core.AppUser"
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(os.environ.get("STATIC_ROOT", BASE_DIR / "staticfiles"))
MEDIA_URL = "/uploads/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "uploads"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STORAGES = {
  "default": {
    "BACKEND": "django.core.files.storage.FileSystemStorage",
  },
  "staticfiles": {
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
  },
}

AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "").strip()
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "").strip()
AWS_S3_CUSTOM_DOMAIN = os.environ.get("AWS_S3_CUSTOM_DOMAIN", "").strip()
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", "").strip() or None
AWS_S3_PUBLIC_ENDPOINT_URL = os.environ.get("AWS_S3_PUBLIC_ENDPOINT_URL", "").strip()
AWS_S3_ADDRESSING_STYLE = os.environ.get("AWS_S3_ADDRESSING_STYLE", "").strip() or None
AWS_S3_URL_PROTOCOL = os.environ.get("AWS_S3_URL_PROTOCOL", "").strip().lower() or None
AWS_S3_FILE_OVERWRITE = env_bool("AWS_S3_FILE_OVERWRITE", False)


def storage_url_protocol(default: str = "https:") -> str:
  protocol = (AWS_S3_URL_PROTOCOL or "").removesuffix("://").removesuffix(":")
  if protocol in {"http", "https"}:
    return f"{protocol}:"
  return default


def s3_public_media_base_url() -> tuple[str, str | None, str | None]:
  if AWS_S3_CUSTOM_DOMAIN:
    protocol = storage_url_protocol()
    return f"{protocol}//{AWS_S3_CUSTOM_DOMAIN.rstrip('/')}", AWS_S3_CUSTOM_DOMAIN.rstrip("/"), protocol

  if AWS_S3_PUBLIC_ENDPOINT_URL:
    public_base = f"{AWS_S3_PUBLIC_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}"
    parsed = urlparse(public_base)
    if parsed.scheme and parsed.netloc:
      custom_domain = f"{parsed.netloc}{parsed.path}".rstrip("/")
      return public_base, custom_domain, f"{parsed.scheme}:"
    return public_base, None, None

  if AWS_S3_ENDPOINT_URL:
    return f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}", None, None

  if AWS_S3_REGION_NAME:
    return f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com", None, None

  return f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com", None, None


if AWS_STORAGE_BUCKET_NAME:
  media_base_url, storage_custom_domain, storage_protocol = s3_public_media_base_url()
  storage_options = {
    "bucket_name": AWS_STORAGE_BUCKET_NAME,
    "region_name": AWS_S3_REGION_NAME or None,
    "custom_domain": storage_custom_domain,
    "endpoint_url": AWS_S3_ENDPOINT_URL,
    "default_acl": None,
    "file_overwrite": AWS_S3_FILE_OVERWRITE,
    "querystring_auth": False,
  }
  if AWS_S3_ADDRESSING_STYLE:
    storage_options["addressing_style"] = AWS_S3_ADDRESSING_STYLE
  if storage_protocol:
    storage_options["url_protocol"] = storage_protocol

  STORAGES["default"] = {
    "BACKEND": "storages.backends.s3.S3Storage",
    "OPTIONS": storage_options,
  }
  MEDIA_URL = f"{media_base_url.rstrip('/')}/"

REST_FRAMEWORK = {
  "DEFAULT_AUTHENTICATION_CLASSES": [
    "rest_framework_simplejwt.authentication.JWTAuthentication",
  ],
  "DEFAULT_PERMISSION_CLASSES": [
    "rest_framework.permissions.IsAuthenticated",
  ],
}

SIMPLE_JWT = {
  "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("ACCESS_TOKEN_LIFETIME_MINUTES", 240)),
  "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("REFRESH_TOKEN_LIFETIME_DAYS", 30)),
  # Derive a dedicated, fixed-length HMAC key so JWT signing always meets the
  # 256-bit minimum for HS256 without exposing or duplicating the Django secret.
  "SIGNING_KEY": hashlib.sha256(f"prepvilla.jwt:{SECRET_KEY}".encode("utf-8")).digest(),
}

CORS_ALLOWED_ORIGINS = env_list(
  "CORS_ALLOWED_ORIGINS",
  "http://localhost:3500,http://127.0.0.1:3500,https://dev.prepvilla.info,https://api.dev.prepvilla.info,https://prepvilla.info",
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list(
  "CSRF_TRUSTED_ORIGINS",
  "http://localhost:3500,http://127.0.0.1:3500,https://dev.prepvilla.info,https://prepvilla.info",
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = env_bool("CSRF_COOKIE_HTTPONLY", False)
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = os.environ.get("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")
X_FRAME_OPTIONS = "DENY"
WHITENOISE_MAX_AGE = env_int("WHITENOISE_MAX_AGE", 31536000 if not DEBUG else 0)

def valkey_connection_url() -> str:
  url = (os.environ.get("VALKEY_URL") or os.environ.get("REDIS_URL", "")).strip()
  auth_token = os.environ.get("VALKEY_AUTH_TOKEN", "").strip()
  if not url or not auth_token:
    return url

  parsed = urlparse(url)
  if parsed.password is not None:
    return url

  hostname = parsed.hostname or ""
  if ":" in hostname:
    hostname = f"[{hostname}]"
  host = f"{hostname}:{parsed.port}" if parsed.port else hostname
  return parsed._replace(netloc=f":{quote_plus(auth_token)}@{host}").geturl()


VALKEY_URL = valkey_connection_url()
if VALKEY_URL:
  CHANNEL_LAYERS = {
    "default": {
      "BACKEND": "channels_redis.core.RedisChannelLayer",
      "CONFIG": {"hosts": [VALKEY_URL]},
    }
  }
else:
  CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
  }

if VALKEY_URL:
  CACHES = {
    "default": {
      "BACKEND": "django.core.cache.backends.redis.RedisCache",
      "LOCATION": VALKEY_URL,
    }
  }
else:
  CACHES = {
    "default": {
      "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
      "LOCATION": "prepvilla-local",
    }
  }

RUNNING_TESTS = "test" in sys.argv
PAYMENT_QUEUE_BACKEND = (
  "sync"
  if RUNNING_TESTS
  else os.environ.get("PAYMENT_QUEUE_BACKEND", "sync").strip().lower() or "sync"
)
PAYMENT_QUEUE_NAME = os.environ.get("PAYMENT_QUEUE_NAME", "prepvilla-payments").strip() or "prepvilla-payments"
PAYMENT_QUEUE_REDIS_URL = os.environ.get("PAYMENT_QUEUE_REDIS_URL", VALKEY_URL).strip()
PAYMENT_QUEUE_JOB_TIMEOUT_SECONDS = env_int("PAYMENT_QUEUE_JOB_TIMEOUT_SECONDS", 300)
PAYMENT_QUEUE_RESULT_TTL_SECONDS = env_int("PAYMENT_QUEUE_RESULT_TTL_SECONDS", 3600)
PAYMENT_QUEUE_FAILURE_TTL_SECONDS = env_int("PAYMENT_QUEUE_FAILURE_TTL_SECONDS", 86400)
PAYMENT_QUEUE_READY_PAYOUT_INTERVAL_SECONDS = env_int("PAYMENT_QUEUE_READY_PAYOUT_INTERVAL_SECONDS", 300)
PAYMENT_QUEUE_SUBSCRIPTION_RENEWAL_INTERVAL_SECONDS = env_int(
  "PAYMENT_QUEUE_SUBSCRIPTION_RENEWAL_INTERVAL_SECONDS",
  3600,
)
PAYMENT_QUEUE_RECONCILIATION_INTERVAL_SECONDS = env_int(
  "PAYMENT_QUEUE_RECONCILIATION_INTERVAL_SECONDS",
  300,
)
PAYMENT_QUEUE_WORKER_WAIT_SECONDS = env_int("PAYMENT_QUEUE_WORKER_WAIT_SECONDS", 20)
PAYMENT_QUEUE_WORKER_MAX_MESSAGES = env_int("PAYMENT_QUEUE_WORKER_MAX_MESSAGES", 10)
PAYMENT_QUEUE_VISIBILITY_TIMEOUT_SECONDS = env_int("PAYMENT_QUEUE_VISIBILITY_TIMEOUT_SECONDS", 300)
PAYMENT_QUEUE_AWS_REGION = os.environ.get("PAYMENT_QUEUE_AWS_REGION", "").strip()
PAYMENT_QUEUE_URL = os.environ.get("PAYMENT_QUEUE_URL", "").strip()
PAYMENT_QUEUE_SQS_ENDPOINT_URL = os.environ.get("PAYMENT_QUEUE_SQS_ENDPOINT_URL", "").strip()

API_PUBLIC_URL = os.environ.get("API_PUBLIC_URL", "http://localhost:8500").rstrip("/")
WEB_PUBLIC_URL = os.environ.get("WEB_PUBLIC_URL", "http://localhost:3500").rstrip("/")

FLUTTERWAVE_API_VERSION = os.environ.get("FLUTTERWAVE_API_VERSION", "v4").strip()
FLUTTERWAVE_CLIENT_ID = os.environ.get("FLUTTERWAVE_CLIENT_ID", "").strip()
FLUTTERWAVE_CLIENT_SECRET = os.environ.get("FLUTTERWAVE_CLIENT_SECRET", "").strip()
FLUTTERWAVE_ENCRYPTION_KEY = os.environ.get("FLUTTERWAVE_ENCRYPTION_KEY", "").strip()
FLUTTERWAVE_WEBHOOK_SECRET_HASH = os.environ.get("FLUTTERWAVE_WEBHOOK_SECRET_HASH", "").strip()
FLUTTERWAVE_API_BASE_URL = os.environ.get(
  "FLUTTERWAVE_API_BASE_URL",
  "https://developersandbox-api.flutterwave.com",
).strip().rstrip("/")
FLUTTERWAVE_TOKEN_URL = os.environ.get(
  "FLUTTERWAVE_TOKEN_URL",
  "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token",
).strip()
FLUTTERWAVE_WEBHOOK_URL = os.environ.get("FLUTTERWAVE_WEBHOOK_URL", "").strip()
FLUTTERWAVE_REDIRECT_URL = os.environ.get(
  "FLUTTERWAVE_REDIRECT_URL",
  f"{WEB_PUBLIC_URL}/payments/flutterwave/callback",
).strip()
FLUTTERWAVE_TIMEOUT_SECONDS = env_int("FLUTTERWAVE_TIMEOUT_SECONDS", 20)
FLUTTERWAVE_PAYOUT_BALANCE_DELAY_MINUTES = env_int(
  "FLUTTERWAVE_PAYOUT_BALANCE_DELAY_MINUTES",
  24 * 60,
)
FLUTTERWAVE_PAYOUT_RELEASE_WATCH_INTERVAL_SECONDS = env_int(
  "FLUTTERWAVE_PAYOUT_RELEASE_WATCH_INTERVAL_SECONDS",
  300,
)
TUTOR_PAYOUT_PERCENTAGE = max(0, min(env_int("TUTOR_PAYOUT_PERCENTAGE", 95), 100))
PREPVILLA_ADMIN_FEE_PERCENTAGE = max(0, min(env_int("PREPVILLA_ADMIN_FEE_PERCENTAGE", 5), 100))
PREPVILLA_OPERATIONAL_BANK_CODE = os.environ.get("PREPVILLA_OPERATIONAL_BANK_CODE", "").strip()
PREPVILLA_OPERATIONAL_BANK_NAME = os.environ.get("PREPVILLA_OPERATIONAL_BANK_NAME", "").strip()
PREPVILLA_OPERATIONAL_ACCOUNT_NUMBER = os.environ.get("PREPVILLA_OPERATIONAL_ACCOUNT_NUMBER", "").strip()
PREPVILLA_OPERATIONAL_ACCOUNT_NAME = os.environ.get("PREPVILLA_OPERATIONAL_ACCOUNT_NAME", "").strip()
PREPVILLA_OPERATIONAL_SUBACCOUNT_ID = os.environ.get("PREPVILLA_OPERATIONAL_SUBACCOUNT_ID", "").strip()
PREPVILLA_OPERATIONAL_BUSINESS_EMAIL = os.environ.get("PREPVILLA_OPERATIONAL_BUSINESS_EMAIL", "").strip()
PREPVILLA_OPERATIONAL_BUSINESS_MOBILE = os.environ.get("PREPVILLA_OPERATIONAL_BUSINESS_MOBILE", "").strip()
PREPVILLA_OPERATIONAL_SUBACCOUNT_COUNTRY = os.environ.get("PREPVILLA_OPERATIONAL_SUBACCOUNT_COUNTRY", "NG").strip() or "NG"
PREPVILLA_OPERATIONAL_SUBACCOUNT_SPLIT_TYPE = os.environ.get("PREPVILLA_OPERATIONAL_SUBACCOUNT_SPLIT_TYPE", "flat").strip() or "flat"
PREPVILLA_OPERATIONAL_SUBACCOUNT_SPLIT_VALUE = os.environ.get("PREPVILLA_OPERATIONAL_SUBACCOUNT_SPLIT_VALUE", "0").strip() or "0"
PREPVILLA_SUBSCRIPTION_TRANSACTION_CHARGE_TYPE = os.environ.get("PREPVILLA_SUBSCRIPTION_TRANSACTION_CHARGE_TYPE", "flat").strip() or "flat"
PREPVILLA_SUBSCRIPTION_TRANSACTION_CHARGE = os.environ.get("PREPVILLA_SUBSCRIPTION_TRANSACTION_CHARGE", "0").strip() or "0"
FLUTTERWAVE_ENFORCE_WEBHOOK_SIGNATURE = env_bool(
  "FLUTTERWAVE_ENFORCE_WEBHOOK_SIGNATURE",
  ENFORCE_PRODUCTION_HARDENING,
)

VERIFICATION_SERVICE = os.environ.get("VERIFICATION_SERVICE", "prembly").strip().lower() or "prembly"
PREMBLY_API_BASE_URL = os.environ.get("PREMBLY_API_BASE_URL", "https://api.prembly.com").strip().rstrip("/")
PREMBLY_NIN_API_URL = os.environ.get("PREMBLY_NIN_API_URL", "/verification/vnin").strip()
PREMBLY_BVN_API_URL = os.environ.get("PREMBLY_BVN_API_URL", "/verification/bvn").strip()
PREMBLY_CAC_API_URL = os.environ.get("PREMBLY_CAC_API_URL", "/verification/cac").strip()
PREMBLY_API_KEY = os.environ.get("PREMBLY_API_KEY", "").strip()
PREMBLY_API_PUBLIC_KEY = os.environ.get("PREMBLY_API_PUBLIC_KEY", "").strip()
PREMBLY_API_SECRET_KEY = os.environ.get("PREMBLY_API_SECRET_KEY", "").strip() or PREMBLY_API_KEY
PREMBLY_TIMEOUT_SECONDS = env_int("PREMBLY_TIMEOUT_SECONDS", 10)
PREMBLY_LOOKUP_CACHE_TIMEOUT_SECONDS = env_int("PREMBLY_LOOKUP_CACHE_TIMEOUT_SECONDS", 24 * 60 * 60)
PREMBLY_WEBHOOK_TOKEN_CACHE_SECONDS = env_int("PREMBLY_WEBHOOK_TOKEN_CACHE_SECONDS", 7 * 24 * 60 * 60)

DIKRIPT_API_BASE_URL = os.environ.get("DIKRIPT_API_BASE_URL", "https://api.dikript.com").strip().rstrip("/")
DIKRIPT_NIN_API_URL = os.environ.get("DIKRIPT_NIN_API_URL", "/dikript/verification/api/v1/getnin").strip()
DIKRIPT_BVN_API_URL = os.environ.get("DIKRIPT_BVN_API_URL", "/dikript/verification/api/v1/getbvn").strip()
DIKRIPT_CAC_API_URL = os.environ.get("DIKRIPT_CAC_API_URL", "/dikript/verification/api/v1/getcacbasic").strip()
DIKRIPT_API_PUBLIC_KEY = os.environ.get("DIKRIPT_API_PUBLIC_KEY", "").strip()
DIKRIPT_API_SECRET_KEY = os.environ.get("DIKRIPT_API_SECRET_KEY", "").strip() or DIKRIPT_API_PUBLIC_KEY
DIKRIPT_TIMEOUT_SECONDS = env_int("DIKRIPT_TIMEOUT_SECONDS", 10)
DIKRIPT_LOOKUP_CACHE_TIMEOUT_SECONDS = env_int("DIKRIPT_LOOKUP_CACHE_TIMEOUT_SECONDS", 24 * 60 * 60)

BYPASS_VERIFICATION = env_bool("BYPASS_VERIFICATION", DEBUG)
SEED_DEMO_ACCOUNTS = env_bool(
  "SEED_DEMO_ACCOUNTS",
  ENVIRONMENT in {"development", "dev", "local"} and "test" not in sys.argv,
)
DEFAULT_TUTOR_SEED_PATH = Path(
  os.environ.get("DEFAULT_TUTOR_SEED_PATH", BASE_DIR / "seed_demo_data" / "tutors" / "default_tutors.json")
)
DEFAULT_STUDENT_SEED_PATH = Path(
  os.environ.get("DEFAULT_STUDENT_SEED_PATH", BASE_DIR / "seed_demo_data" / "students" / "default_students.json")
)

DEFAULT_EMAIL_BACKEND = (
  "django.core.mail.backends.locmem.EmailBackend"
  if RUNNING_TESTS
  else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", DEFAULT_EMAIL_BACKEND)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@prepvilla.info")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "criyo.ai@gmail.com")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "criyo.ai@gmail.com")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = env_int("EMAIL_TIMEOUT", 15)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOGGING = {
  "version": 1,
  "disable_existing_loggers": False,
  "formatters": {
    "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
  },
  "handlers": {
    "console": {"class": "logging.StreamHandler", "formatter": "standard"},
  },
  "root": {"handlers": ["console"], "level": LOG_LEVEL},
}
