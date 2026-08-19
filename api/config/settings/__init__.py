import os
import sys


if os.environ.get("DJANGO_SETTINGS_MODULE") == __name__:
  environment = os.environ.get("DJANGO_ENV", os.environ.get("ENVIRONMENT", "")).strip().lower()
  debug_enabled = os.environ.get("DJANGO_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}

  if not environment and len(sys.argv) > 1 and sys.argv[1] == "test":
    environment = "test"

  if environment in {"prod", "production"}:
    from .production import *  # noqa: F403,F401
  elif environment in {"dev", "development"}:
    from .development import *  # noqa: F403,F401
  elif environment == "test":
    from .test import *  # noqa: F403,F401
  elif environment == "local" or debug_enabled:
    from .local import *  # noqa: F403,F401
  else:
    from .production import *  # noqa: F403,F401
