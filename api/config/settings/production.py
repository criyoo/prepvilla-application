import os

os.environ["DJANGO_ENV"] = "production"
os.environ["DJANGO_DEBUG"] = "False"

from .base import *  # noqa: F403,F401,E402

DEBUG = False
ENVIRONMENT = "production"
ENFORCE_PRODUCTION_HARDENING = True
FLUTTERWAVE_ENFORCE_WEBHOOK_SIGNATURE = env_bool(  # noqa: F405
  "FLUTTERWAVE_ENFORCE_WEBHOOK_SIGNATURE",
  True,
)

if SECRET_KEY == "dev-secret-key":  # noqa: F405
  raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

ALLOWED_HOSTS = env_list(  # noqa: F405
  "DJANGO_ALLOWED_HOSTS",
  "prepvilla.info,www.prepvilla.info,api.prepvilla.info",
)
CORS_ALLOWED_ORIGINS = env_list(  # noqa: F405
  "CORS_ALLOWED_ORIGINS",
  "https://prepvilla.info,https://www.prepvilla.info",
)
CSRF_TRUSTED_ORIGINS = env_list(  # noqa: F405
  "CSRF_TRUSTED_ORIGINS",
  "https://prepvilla.info,https://www.prepvilla.info,https://api.prepvilla.info",
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", False)  # noqa: F405
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)  # noqa: F405
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)  # noqa: F405
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)  # noqa: F405
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)  # noqa: F405

SEED_DEMO_ACCOUNTS = env_bool("SEED_DEMO_ACCOUNTS", False)  # noqa: F405
