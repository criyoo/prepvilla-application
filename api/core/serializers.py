from django.db.models import Avg, Min
from rest_framework import serializers

from core.models import (
  AppUser,
  AvailabilitySlot,
  Booking,
  Conversation,
  Message,
  Review,
  TutorProfile,
  VerificationRequest,
)


class UserSerializer(serializers.Serializer):
  id = serializers.UUIDField()
  email = serializers.EmailField()
  role = serializers.CharField()
  displayName = serializers.CharField(source="display_name")
  timezone = serializers.CharField()
  createdAt = serializers.DateTimeField(source="created_at")
  fullName = serializers.CharField(source="full_name")
  mobileNumber = serializers.CharField(source="mobile_number")
  dateOfBirth = serializers.DateField(source="date_of_birth", allow_null=True)


class TutorCardSerializer(serializers.Serializer):
  id = serializers.UUIDField()
  displayName = serializers.CharField()
  headline = serializers.CharField()
  subjects = serializers.ListField(child=serializers.CharField())
  hourlyRate = serializers.IntegerField()
  timezone = serializers.CharField()
  location = serializers.CharField(required=False, allow_blank=True)
  profilePhotoUrl = serializers.CharField(required=False, allow_blank=True)
  verificationStatus = serializers.CharField()
  nextAvailableAt = serializers.DateTimeField(allow_null=True, required=False)
  isFavorited = serializers.BooleanField(required=False, default=False)
  firstLessonFree = serializers.BooleanField(required=False, default=False)
  teachingModes = serializers.ListField(child=serializers.CharField(), required=False)
  videoCallUrl = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TutorDetailsSerializer(serializers.Serializer):
  id = serializers.UUIDField()
  displayName = serializers.CharField()
  headline = serializers.CharField()
  subjects = serializers.ListField(child=serializers.CharField())
  hourlyRate = serializers.IntegerField()
  timezone = serializers.CharField()
  location = serializers.CharField(required=False, allow_blank=True)
  profilePhotoUrl = serializers.CharField(required=False, allow_blank=True)
  verificationStatus = serializers.CharField()
  nextAvailableAt = serializers.DateTimeField(allow_null=True, required=False)
  bio = serializers.CharField()
  languages = serializers.ListField(child=serializers.CharField())
  isListed = serializers.BooleanField()
  firstLessonFree = serializers.BooleanField(required=False, default=False)
  teachingModes = serializers.ListField(child=serializers.CharField(), required=False)
  videoCallUrl = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TutorMeProfileSerializer(serializers.Serializer):
  headline = serializers.CharField(allow_blank=True)
  bio = serializers.CharField(allow_blank=True)
  subjects = serializers.ListField(child=serializers.CharField())
  languages = serializers.ListField(child=serializers.CharField())
  hourlyRate = serializers.IntegerField()
  profilePhotoUrl = serializers.CharField(allow_blank=True, required=False)
  homeCity = serializers.CharField(allow_blank=True, required=False)
  homeState = serializers.CharField(allow_blank=True, required=False)
  homeAddress = serializers.CharField(allow_blank=True, required=False)
  verificationStatus = serializers.CharField()
  isListed = serializers.BooleanField()
  responseTime = serializers.CharField(source="response_time", allow_blank=True, required=False)
  firstLessonFree = serializers.BooleanField(required=False, default=False)
  offersFaceToFace = serializers.BooleanField(required=False, default=True)
  offersWebcam = serializers.BooleanField(required=False, default=False)
  teachingModes = serializers.ListField(child=serializers.CharField(), required=False)
  videoCallUrl = serializers.CharField(required=False, allow_blank=True, allow_null=True)
  additionalDocumentUrls = serializers.ListField(child=serializers.CharField(), required=False)


class AvailabilitySlotSerializer(serializers.ModelSerializer):
  id = serializers.UUIDField(required=False)
  startsAt = serializers.DateTimeField(source="starts_at")
  endsAt = serializers.DateTimeField(source="ends_at")

  class Meta:
    model = AvailabilitySlot
    fields = ["id", "startsAt", "endsAt"]


class BookingSerializer(serializers.ModelSerializer):
  tutorId = serializers.UUIDField(source="tutor_profile_id")
  studentId = serializers.UUIDField(source="student_user_id")
  lessonType = serializers.CharField(source="lesson_type")
  startsAt = serializers.DateTimeField(source="starts_at", allow_null=True)
  endsAt = serializers.DateTimeField(source="ends_at", allow_null=True)
  studentCompletedAt = serializers.DateTimeField(source="student_completed_at", allow_null=True)
  tutorCompletedAt = serializers.DateTimeField(source="tutor_completed_at", allow_null=True)
  requestedStartRange = serializers.SerializerMethodField()
  createdAt = serializers.DateTimeField(source="created_at")

  class Meta:
    model = Booking
    fields = ["id", "tutorId", "studentId", "lessonType", "status", "startsAt", "endsAt", "studentCompletedAt", "tutorCompletedAt", "requestedStartRange", "notes", "createdAt"]

  def get_requestedStartRange(self, obj: Booking):
    if obj.requested_from and obj.requested_to:
      return {"from": obj.requested_from.isoformat(), "to": obj.requested_to.isoformat()}
    return None


class BookingRowSerializer(serializers.Serializer):
  id = serializers.UUIDField()
  tutorId = serializers.UUIDField()
  studentId = serializers.UUIDField()
  status = serializers.CharField()
  startsAt = serializers.DateTimeField(allow_null=True)
  requestedStartRange = serializers.DictField(allow_null=True)
  notes = serializers.CharField(allow_null=True)
  createdAt = serializers.DateTimeField()
  tutorName = serializers.CharField()
  studentName = serializers.CharField()
  tutorPhotoUrl = serializers.CharField(required=False, allow_blank=True)
  teachingModes = serializers.ListField(child=serializers.CharField(), required=False)
  videoCallUrl = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ConversationSerializer(serializers.Serializer):
  id = serializers.UUIDField()
  tutorId = serializers.UUIDField()
  tutorName = serializers.CharField()
  studentId = serializers.UUIDField()
  studentName = serializers.CharField()
  createdAt = serializers.DateTimeField()
  isBlocked = serializers.BooleanField(source="is_blocked")


class MessageSerializer(serializers.Serializer):
  id = serializers.UUIDField()
  conversationId = serializers.UUIDField()
  senderUserId = serializers.UUIDField()
  body = serializers.CharField()
  createdAt = serializers.DateTimeField()
  readAt = serializers.DateTimeField(allow_null=True)


class VerificationStateSerializer(serializers.Serializer):
  status = serializers.CharField()
  notes = serializers.CharField(allow_null=True)
  submittedAt = serializers.DateTimeField(allow_null=True)
  decidedAt = serializers.DateTimeField(allow_null=True)
  email = serializers.EmailField(required=False, allow_blank=True)
  firstName = serializers.CharField(required=False, allow_blank=True)
  middleName = serializers.CharField(required=False, allow_blank=True)
  lastName = serializers.CharField(required=False, allow_blank=True)
  fullName = serializers.CharField(required=False, allow_blank=True)
  profilePhotoUrl = serializers.CharField(required=False, allow_blank=True)
  homeState = serializers.CharField(required=False, allow_blank=True)
  homeCity = serializers.CharField(required=False, allow_blank=True)
  homeAddress = serializers.CharField(required=False, allow_blank=True)
  qualification = serializers.CharField(required=False, allow_blank=True)
  ninNumber = serializers.CharField(required=False, allow_blank=True)
  bvnNumber = serializers.CharField(required=False, allow_blank=True)
  languages = serializers.ListField(child=serializers.CharField(), required=False)
  documentUrls = serializers.ListField(child=serializers.CharField(), required=False)


class VerificationQueueRowSerializer(serializers.Serializer):
  id = serializers.UUIDField()
  tutorId = serializers.UUIDField()
  tutorName = serializers.CharField()
  status = serializers.CharField()
  submittedAt = serializers.DateTimeField()
  notes = serializers.CharField(allow_null=True)
  documentUrl = serializers.CharField(allow_null=True)
  documentUrls = serializers.ListField(child=serializers.CharField(), required=False)


class ReviewSerializer(serializers.ModelSerializer):
  tutorId = serializers.UUIDField(source="tutor_profile_id")
  studentId = serializers.UUIDField(source="student_user_id")
  studentName = serializers.CharField(source="student_user.display_name", read_only=True)
  createdAt = serializers.DateTimeField(source="created_at", read_only=True)
  
  class Meta:
    model = Review
    fields = ["id", "tutorId", "studentId", "studentName", "rating", "comment", "createdAt"]


class ReviewSummarySerializer(serializers.Serializer):
  tutorId = serializers.UUIDField()
  averageRating = serializers.FloatField()
  totalReviews = serializers.IntegerField()
