export type UserRole = "student" | "tutor" | "admin";
export type VerificationStatus = "not_submitted" | "pending" | "approved" | "rejected";
export type BookingStatus = "requested" | "confirmed" | "completed" | "cancelled" | "rejected";
export type TeachingMode = "face_to_face" | "webcam";

export interface TutorCard {
  id: string;
  displayName: string;
  headline: string;
  subjects: string[];
  hourlyRate: number;
  timezone: string;
  location?: string;
  profilePhotoUrl?: string;
  verificationStatus: VerificationStatus;
  nextAvailableAt?: string;
  averageRating: number;
  totalReviews: number;
  isFavorited?: boolean;
  firstLessonFree?: boolean;
  teachingModes?: TeachingMode[];
  videoCallUrl?: string | null;
}

export interface TutorDetails extends TutorCard {
  bio: string;
  languages: string[];
  responseTime?: string;
  isListed: boolean;
}

export interface AvailabilitySlot {
  id: string;
  startsAt: string;
  endsAt: string;
}

export interface Booking {
  id: string;
  tutorId: string;
  studentId: string;
  status: BookingStatus;
  lessonType?: string;
  startsAt?: string;
  endsAt?: string;
  studentCompletedAt?: string | null;
  tutorCompletedAt?: string | null;
  requestedStartRange?: { from: string; to: string };
  notes?: string;
  createdAt: string;
  tutorName?: string;
  studentName?: string;
  tutorPhotoUrl?: string;
  teachingModes?: TeachingMode[];
  videoCallUrl?: string | null;
}

export interface Conversation {
  id: string;
  tutorId: string;
  tutorName: string;
  studentId: string;
  studentName: string;
  createdAt: string;
  isBlocked?: boolean;
}

export interface ChatMessage {
  id: string;
  conversationId: string;
  senderUserId: string;
  body: string;
  createdAt: string;
  readAt?: string;
}
