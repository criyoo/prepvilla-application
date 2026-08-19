from __future__ import annotations

from typing import Callable

from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.utils.functional import LazyObject
from rest_framework_simplejwt.tokens import AccessToken

from core.models import AppUser


class UserLazyObject(LazyObject):
  def _setup(self):
    self._wrapped = AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
  async def __call__(self, scope, receive, send):
    close_old_connections()
    scope["user"] = UserLazyObject()

    token = None
    qs = scope.get("query_string", b"").decode("utf-8")
    if qs:
      for part in qs.split("&"):
        if part.startswith("token="):
          token = part.split("token=", 1)[1]

    if token:
      try:
        access = AccessToken(token)
        user_id = access.get("user_id")
        if user_id:
          user = await AppUser.objects.filter(id=user_id).afirst()
          if user:
            scope["user"] = user
      except Exception:
        scope["user"] = AnonymousUser()

    return await super().__call__(scope, receive, send)

