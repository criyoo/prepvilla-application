from channels.routing import URLRouter
from django.urls import path

from core.auth import JwtAuthMiddleware
from core.consumers import ConversationConsumer

websocket_urlpatterns = [
    path(
        "ws/conversations/<uuid:conversation_id>",
        ConversationConsumer.as_asgi(),
    ),
]

websocket_application = JwtAuthMiddleware(
    URLRouter(websocket_urlpatterns)
)
