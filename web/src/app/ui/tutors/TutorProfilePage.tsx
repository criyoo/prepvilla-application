"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { AvailabilitySlot, TutorDetails, Conversation } from "@prepvilla/types";
import { AppHeader } from "../shared/AppHeader";
import { Badge } from "../shared/Badge";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";
import { resolveMediaUrl } from "../shared/media";
import { buildTutorProfileHref } from "../shared/routes";

type TutorResponse = {
  tutor: TutorDetails;
  availability: AvailabilitySlot[];
};

type BookingRequestPayload = {
  lessonType: string;
  notes: string;
  slotId?: string;
  requestedStartRange?: { from: string; to: string };
};

type Review = {
  id: string;
  studentName: string;
  rating: number;
  comment: string;
  createdAt: string;
  bookingId: string;
};

type ReviewsResponse = {
  reviews: Review[];
  summary?: {
    averageRating: number;
    totalReviews: number;
    ratingCounts: Record<string, number>;
  };
};

type BookingRow = {
  id: string;
  status: string;
  tutorProfileId: string;
  reviewId?: string | null;
};

type BookingsResponse = {
  results: BookingRow[];
};

function formatTeachingMode(mode: string) {
  return mode === "webcam" ? "Webcam" : "Face-to-face";
}

export function TutorProfilePage({ tutorId }: { tutorId: string }) {
  const role = useAuthStore((s) => s.role);
  const accessToken = useAuthStore((s) => s.accessToken);
  const loadFromStorage = useAuthStore((s) => s.loadFromStorage);
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState<TutorResponse | null>(null);

  const [lessonType, setLessonType] = useState("Face-to-face");
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [rangeFrom, setRangeFrom] = useState("");
  const [rangeTo, setRangeTo] = useState("");
  const [submitState, setSubmitState] = useState<string | null>(null);
  const [photoFailed, setPhotoFailed] = useState(false);

  const [reviews, setReviews] = useState<Review[]>([]);
  const [isLoadingReviews, setIsLoadingReviews] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [reviewableBookingId, setReviewableBookingId] = useState<string | null>(null);
  const [reviewNotice, setReviewNotice] = useState<string | null>(null);

  const selectedSlot = useMemo(
    () => (data ? data.availability.find((s) => s.id === selectedSlotId) ?? null : null),
    [data, selectedSlotId],
  );
  const availableTeachingModes = useMemo(
    () => (data?.tutor.teachingModes?.length ? data.tutor.teachingModes : ["face_to_face"]),
    [data?.tutor.teachingModes],
  );
  const isLoggedIn = Boolean(accessToken);
  const isStudent = role === "student";
  const nextPath = buildTutorProfileHref(tutorId);

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setData(null);
    const res = await api.get<TutorResponse>(`/api/tutors/${tutorId}`);
    if (!res.ok) {
      setError(res.error);
      setIsLoading(false);
      return;
    }
    setData(res.data);
    setIsLoading(false);
  }, [tutorId]);

  const loadReviews = useCallback(async () => {
    setIsLoadingReviews(true);
    const res = await api.get<ReviewsResponse>(`/api/tutors/${tutorId}/reviews`);
    if (res.ok) {
      setReviews(res.data.reviews);
    }
    setIsLoadingReviews(false);
  }, [tutorId]);

  const loadReviewEligibility = useCallback(async () => {
    if (!isLoggedIn) {
      setReviewableBookingId(null);
      setReviewNotice("Log in as a student to write a review.");
      setShowReviewForm(false);
      return;
    }
    if (!isStudent) {
      setReviewableBookingId(null);
      setReviewNotice("Only students can write reviews.");
      setShowReviewForm(false);
      return;
    }

    const res = await api.get<BookingsResponse>("/api/bookings");
    if (!res.ok) {
      setReviewableBookingId(null);
      setReviewNotice(res.error || "Unable to load review eligibility.");
      setShowReviewForm(false);
      return;
    }

    const eligibleBooking =
      res.data.results.find(
        (booking) =>
          booking.tutorProfileId === tutorId &&
          (booking.status === "completed" || booking.status === "paid") &&
          !booking.reviewId,
      ) ?? null;

    setReviewableBookingId(eligibleBooking?.id ?? null);
    setReviewNotice(
      eligibleBooking ? null : "Complete a lesson with this tutor before leaving a review.",
    );
    if (!eligibleBooking) {
      setShowReviewForm(false);
    }
  }, [isLoggedIn, isStudent, tutorId]);

  useEffect(() => {
    void load();
    void loadReviews();
    void loadReviewEligibility();
  }, [load, loadReviews, loadReviewEligibility]);

  useEffect(() => {
    setPhotoFailed(false);
  }, [data?.tutor.profilePhotoUrl, tutorId]);

  useEffect(() => {
    if (availableTeachingModes.length === 0) return;
    const validLabels = availableTeachingModes.map((mode) => formatTeachingMode(mode).toLowerCase());
    if (!validLabels.includes(lessonType.toLowerCase())) {
      setLessonType(formatTeachingMode(availableTeachingModes[0]));
    }
  }, [availableTeachingModes, lessonType]);

  async function submitBookingRequest() {
    setError(null);
    setSubmitState(null);

    if (!isLoggedIn) {
      router.push(`/signup?next=${encodeURIComponent(nextPath)}`);
      return;
    }
    if (!isStudent) {
      setError("Only students can send booking requests.");
      return;
    }

    const payload: BookingRequestPayload = { lessonType, notes };

    if (selectedSlot) {
      payload.slotId = selectedSlot.id;
    } else if (rangeFrom && rangeTo) {
      payload.requestedStartRange = { from: new Date(rangeFrom).toISOString(), to: new Date(rangeTo).toISOString() };
    } else {
      setError("Select a slot or provide a time range");
      return;
    }

    const res = await api.post<{ bookingId: string; conversation: Conversation | null }>(
      `/api/tutors/${tutorId}/booking-requests`,
      payload,
    );
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setSubmitState("Request sent. Track updates in Dashboard → Bookings.");
  }

  async function startMessage() {
    setError(null);
    if (!isLoggedIn) {
      router.push(`/signup?next=${encodeURIComponent(nextPath)}`);
      return;
    }
    if (!isStudent) {
      setError("Only students can message tutors.");
      return;
    }
    const res = await api.post<{ conversation: Conversation }>("/api/conversations", { tutorId });
    if (!res.ok) {
      setError(res.error);
      return;
    }
    // Redirect to the messages dashboard with the new conversation selected
    router.push(`/dashboard/messages?conversationId=${res.data.conversation.id}`);
  }

  async function submitReview() {
    setError(null);
    if (!isLoggedIn) {
      router.push(`/login?next=${encodeURIComponent(nextPath)}`);
      return;
    }
    if (!isStudent) {
      setError("Only students can write reviews.");
      return;
    }
    if (!reviewableBookingId) {
      setError("You can only review a tutor after a completed lesson.");
      return;
    }
    setIsSubmittingReview(true);

    const res = await api.post(`/api/bookings/${reviewableBookingId}/review`, {
      rating: reviewRating,
      comment: reviewComment,
    });

    setIsSubmittingReview(false);

    if (!res.ok) {
      setError(res.error || "Failed to submit review");
      return;
    }

    setReviewRating(5);
    setReviewComment("");
    setShowReviewForm(false);
    await loadReviews();
    await loadReviewEligibility();
  }

  const statusTone =
    data?.tutor.verificationStatus === "approved"
      ? "success"
      : data?.tutor.verificationStatus === "rejected"
        ? "danger"
        : "neutral";

  const photoUrl = resolveMediaUrl(data?.tutor.profilePhotoUrl);

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="mx-auto w-full max-w-[1200px] px-4 pb-10 pt-6">
        {isLoading ? (
          <div className="h-[240px] animate-pulse rounded-2xl border border-border bg-surface-2" />
        ) : data ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[340px_1fr]">
            {/* Left Sidebar - Profile Image & Key Stats */}
            <aside className="h-fit space-y-4 lg:sticky lg:top-24">
              {/* Profile Card */}
              <div className="rounded-2xl border border-border bg-surface-2 p-6">
                {/* Large Profile Image */}
                <div className="relative mx-auto mb-4 aspect-square w-full max-w-[280px] overflow-hidden rounded-xl">
                  {photoUrl && !photoFailed ? (
                    <Image
                      src={photoUrl}
                      alt={data.tutor.displayName}
                      className="h-full w-full object-cover"
                      fill
                      loading="lazy"
                      sizes="(min-width: 1024px) 280px, 80vw"
                      unoptimized
                      onError={() => setPhotoFailed(true)}
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-gray-200 to-gray-300 text-6xl font-medium text-gray-400">
                      {data.tutor.displayName.charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>

                {/* Hourly Rate - Prominent */}
                <div className="text-center">
                  <div className="text-3xl font-bold text-gray-900">₦{data.tutor.hourlyRate.toLocaleString()}</div>
                  <div className="text-sm text-gray-500">per hour</div>
                </div>

                {/* Stats */}
                <div className="mt-4 grid grid-cols-2 gap-3 border-t border-border pt-4">
                  <div className="text-center">
                    <div className="text-xl font-bold text-gray-900">12</div>
                    <div className="text-xs text-gray-500">Students</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-bold text-gray-900">2h</div>
                    <div className="text-xs text-gray-500">Response</div>
                  </div>
                </div>

                {/* Verification Badge */}
                <div className="mt-4 flex justify-center">
                  <Badge tone={statusTone}>
                    {data.tutor.verificationStatus === "approved" ? "✓ Verified" : data.tutor.verificationStatus}
                  </Badge>
                </div>
              </div>

              {/* Booking Form */}
              <div className="form-panel rounded-2xl p-6">
                <h3 className="brand-heading text-lg font-semibold">Book a Lesson</h3>
                <div className="mt-4 grid gap-3">
                  <div className="grid gap-2">
                    <div className="text-[14px] font-medium leading-[22px] text-black">Lesson method</div>
                    <div className="flex flex-wrap gap-2">
                      {availableTeachingModes.map((mode) => {
                        const label = formatTeachingMode(mode);
                        const isSelected = lessonType === label;
                        return (
                          <button
                            key={mode}
                            type="button"
                            onClick={() => setLessonType(label)}
                            className={
                              isSelected
                                ? "form-chip-active rounded-full px-3 py-1.5 text-[13px] font-semibold"
                                : "form-chip rounded-full px-3 py-1.5 text-[13px] font-medium hover:border-black hover:bg-black hover:text-white"
                            }
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>
                    {data.tutor.videoCallUrl && lessonType === "Webcam" ? (
                      <div className="text-[12px] leading-[18px] text-black/65">
                        Webcam bookings include a video room link on the bookings page.
                      </div>
                    ) : null}
                  </div>
                  <Input
                    label="Notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Learning goals, context, etc."
                  />
                  <div className="form-inset rounded-xl p-3">
                    <div className="text-[12px] font-medium leading-[18px] text-black/55">Or request a time range</div>
                    <div className="mt-2 grid gap-2">
                      <Input label="From" type="datetime-local" value={rangeFrom} onChange={(e) => setRangeFrom(e.target.value)} />
                      <Input label="To" type="datetime-local" value={rangeTo} onChange={(e) => setRangeTo(e.target.value)} />
                    </div>
                  </div>
                  {submitState ? <div className="text-[14px] leading-[22px] text-success">{submitState}</div> : null}
                  {error ? <div className="text-[14px] leading-[22px] text-danger">{error}</div> : null}
                  <Button
                    onClick={() => void submitBookingRequest()}
                    disabled={(isLoggedIn && !isStudent) || (isStudent && !selectedSlot && !(rangeFrom && rangeTo))}
                  >
                    Send booking request
                  </Button>
                  <Button variant="secondary" onClick={() => void startMessage()} disabled={isLoggedIn && !isStudent}>
                    Message tutor
                  </Button>
                  {!isLoggedIn ? (
                    <div className="text-[12px] leading-[18px] text-black/55">
                      Create a student account to request lessons and message tutors.
                    </div>
                  ) : !isStudent ? (
                    <div className="text-[12px] leading-[18px] text-black/55">
                      Login as a student to request and message.
                    </div>
                  ) : null}
                </div>
              </div>
            </aside>

            {/* Main Content */}
            <section className="space-y-6">
              {/* Header Info */}
              <div className="rounded-2xl border border-border bg-surface-2 p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h1 className="text-[28px] font-bold leading-[36px] text-gray-900">{data.tutor.displayName}</h1>
                    <div className="mt-2 text-[16px] leading-[24px] text-muted">{data.tutor.headline}</div>
                    <div className="mt-3 flex flex-wrap gap-2 text-[12px] leading-[18px] text-muted">
                      <span className="rounded-full border border-border bg-surface px-2 py-0.5">
                        📍 {data.tutor.location ?? data.tutor.timezone}
                      </span>
                      {availableTeachingModes.map((mode) => (
                        <span key={mode} className="rounded-full border border-info-border bg-info-soft px-2 py-0.5 text-info-foreground">
                          {formatTeachingMode(mode)}
                        </span>
                      ))}
                      {data.tutor.languages.map((l) => (
                        <span key={l} className="rounded-full border border-border bg-surface px-2 py-0.5">
                          🌐 {l}
                        </span>
                      ))}
                    </div>
                  </div>
                  <Link href="/" className="shrink-0 text-[14px] leading-[22px] text-accent hover:underline">
                    Back
                  </Link>
                </div>
              </div>

              {/* About Me - Large and Bold */}
              <div className="rounded-2xl border border-border bg-surface-2 p-6">
                <h2 className="text-[20px] font-bold leading-[28px] text-gray-900">About Me</h2>
                <p className="mt-4 text-[16px] leading-[28px] text-gray-700">{data.tutor.bio}</p>
              </div>

              {/* Subjects */}
              <div className="rounded-2xl border border-border bg-surface-2 p-6">
                <h2 className="text-[20px] font-bold leading-[28px] text-gray-900">Subjects</h2>
                <div className="mt-4 flex flex-wrap gap-2">
                  {data.tutor.subjects.map((s) => (
                    <span key={s} className="rounded-full bg-gray-100 px-4 py-2 text-[14px] font-medium text-gray-700">
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              {/* Reviews */}
              <div className="rounded-2xl border border-border bg-surface-2 p-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-[20px] font-bold leading-[28px] text-gray-900">Reviews ({reviews.length})</h2>
                  {isLoggedIn && isStudent && reviewableBookingId ? (
                    <Button variant="secondary" onClick={() => setShowReviewForm(!showReviewForm)}>
                      {showReviewForm ? "Cancel" : "Write Review"}
                    </Button>
                  ) : null}
                </div>
                {!isLoggedIn ? (
                  <div className="mt-3 text-[14px] leading-[22px] text-muted">
                    <Link href={`/login?next=${encodeURIComponent(nextPath)}`} className="text-accent hover:underline">
                      Log in as a student
                    </Link>{" "}
                    to write a review.
                  </div>
                ) : reviewNotice ? (
                  <div className="mt-3 text-[14px] leading-[22px] text-muted">{reviewNotice}</div>
                ) : null}

                {/* Review Form */}
                {showReviewForm && (
                  <div className="form-panel mt-4 rounded-xl p-4">
                    <h3 className="brand-heading text-[16px] font-semibold">Write a Review</h3>
                    <div className="mt-3 grid gap-3">
                      <div>
                        <label className="text-[14px] font-medium text-black">Rating</label>
                        <div className="mt-1 flex gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              onClick={() => setReviewRating(star)}
                              className="text-2xl"
                            >
                              {star <= reviewRating ? "⭐" : "☆"}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div>
                        <label className="text-[14px] font-medium text-black">Comment</label>
                        <textarea
                          className="mt-1 w-full rounded-xl border border-black/12 bg-white px-4 py-3 text-sm text-black placeholder:text-[color:var(--form-placeholder)] transition-all duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-black/8 focus:border-black"
                          value={reviewComment}
                          onChange={(e) => setReviewComment(e.target.value)}
                          placeholder="Share your experience with this tutor..."
                          rows={3}
                        />
                      </div>
                      <Button
                        onClick={() => void submitReview()}
                        disabled={isSubmittingReview}
                      >
                        {isSubmittingReview ? "Submitting..." : "Submit Review"}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Reviews List */}
                <div className="mt-4 space-y-4">
                  {isLoadingReviews ? (
                    <div className="text-[14px] leading-[22px] text-muted">Loading reviews...</div>
                  ) : reviews.length === 0 ? (
                    <div className="text-[14px] leading-[22px] text-muted">No reviews yet</div>
                  ) : (
                    reviews.map((review) => (
                      <div key={review.id} className="rounded-xl border border-border bg-surface p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className="text-[14px] font-medium text-gray-900">{review.studentName}</div>
                            <div className="flex">
                              {[1, 2, 3, 4, 5].map((star) => (
                                <span key={star} className="text-sm">
                                  {star <= review.rating ? "⭐" : "☆"}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="text-[12px] text-muted">
                            {new Date(review.createdAt).toLocaleDateString()}
                          </div>
                        </div>
                        {review.comment && (
                          <p className="mt-2 text-[14px] leading-[22px] text-gray-700">{review.comment}</p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Availability */}
              <div className="rounded-2xl border border-border bg-surface-2 p-6">
                <h2 className="text-[20px] font-bold leading-[28px] text-gray-900">Availability</h2>
                <div className="mt-4 grid gap-2">
                  {data.availability.length === 0 ? (
                    <div className="text-[14px] leading-[22px] text-muted">No upcoming slots</div>
                  ) : (
                    data.availability
                      .slice(0, 6)
                      .map((s) => (
                        <button
                          key={s.id}
                          onClick={() => setSelectedSlotId(s.id)}
                          className={
                            selectedSlotId === s.id
                              ? "flex items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-left"
                              : "flex items-center justify-between gap-3 rounded-xl border border-border bg-transparent px-4 py-3 text-left text-muted hover:bg-surface"
                          }
                        >
                          <div className="text-[14px] leading-[22px]">
                            {new Date(s.startsAt).toLocaleString()} → {new Date(s.endsAt).toLocaleString()}
                          </div>
                          <div className="text-[12px] leading-[18px]">{selectedSlotId === s.id ? "Selected" : "Select"}</div>
                        </button>
                      ))
                  )}
                </div>
              </div>
            </section>
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-surface-2 p-6 text-center">
            <h1 className="text-[24px] font-semibold leading-[32px] text-gray-900">
              Unable to load tutor profile
            </h1>
            <p className="mt-2 text-[14px] leading-[22px] text-muted">
              {error ?? "This tutor profile is no longer available."}
            </p>
            <Button className="mt-4" onClick={() => void load()}>
              Try again
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
