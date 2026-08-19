from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
  def has_permission(self, request, view):
    return bool(request.user and request.user.is_authenticated and getattr(request.user, "role", None) == "admin")


class IsTutor(BasePermission):
  def has_permission(self, request, view):
    return bool(request.user and request.user.is_authenticated and getattr(request.user, "role", None) == "tutor")


class IsStudent(BasePermission):
  def has_permission(self, request, view):
    return bool(request.user and request.user.is_authenticated and getattr(request.user, "role", None) == "student")

