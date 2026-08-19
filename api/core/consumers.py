from __future__ import annotations

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from django.utils import timezone

from core.models import Conversation, Message
from core.serializers import MessageSerializer


class ConversationConsumer(AsyncWebsocketConsumer):
  async def connect(self):
    self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
    user = self.scope.get("user")
    if not user or not getattr(user, "is_authenticated", False):
      await self.close()
      return

    can_access = await self._can_access(user.id, self.conversation_id)
    if not can_access:
      await self.close()
      return

    self.group_name = f"conv_{self.conversation_id}"
    await self.channel_layer.group_add(self.group_name, self.channel_name)
    await self.accept()

  async def disconnect(self, close_code):
    if hasattr(self, "group_name"):
      await self.channel_layer.group_discard(self.group_name, self.channel_name)

  async def receive(self, text_data=None, bytes_data=None):
    user = self.scope.get("user")
    if not user or not getattr(user, "is_authenticated", False):
      return
    if not text_data:
      return
    try:
      payload = json.loads(text_data)
    except Exception:
      return
    body = payload.get("body")
    if not isinstance(body, str) or not body.strip():
      return

    message = await self._create_message(self.conversation_id, user.id, body.strip())
    await self.channel_layer.group_send(
      self.group_name,
      {
        "type": "message_created",
        "payload": message,
      },
    )

  async def message_created(self, event):
    await self.send(text_data=json.dumps({"type": "message.created", "payload": event.get("payload")}))

  @database_sync_to_async
  def _can_access(self, user_id, conversation_id):
    return Conversation.objects.filter(id=conversation_id).filter(
      Q(student_user_id=user_id) | Q(tutor_profile__user_id=user_id)
    ).exists()

  @database_sync_to_async
  def _create_message(self, conversation_id, sender_user_id, body: str):
    msg = Message.objects.create(conversation_id=conversation_id, sender_user_id=sender_user_id, body=body)
    return MessageSerializer(
      {
        "id": msg.id,
        "conversationId": msg.conversation_id,
        "senderUserId": msg.sender_user_id,
        "body": msg.body,
        "createdAt": msg.created_at,
        "readAt": msg.read_at,
      }
    ).data
