import os
import sys

# Add the backend app directory to Python path so modules can be imported.
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# Initialize Django BEFORE importing any Django modules
import django
django.setup()

from django.conf import settings
from django.core.asgi import get_asgi_application
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from channels.routing import ProtocolTypeRouter
from config.routing import websocket_application

http_application = get_asgi_application()

if settings.DEBUG:
    # ASGI servers do not serve Django static files automatically in development.
    http_application = ASGIStaticFilesHandler(http_application)

application = ProtocolTypeRouter({
    "http": http_application,
    "websocket": websocket_application,
})
