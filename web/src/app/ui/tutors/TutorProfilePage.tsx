"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { AvailabilitySlot, TutorDetails, Conversation } from "@prepvilla/types";
import {
  ArrowLeft,
  BadgeCheck,
  BookOpen,
  CalendarDays,
  Check,
  Clock3,
  GraduationCap,
  Languages,
  MapPin,
  MessageCircle,
  Monitor,
  Sparkles,
  Star,
} from "lucide-react";
import { AppHeader } from "../shared/AppHeader";
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

function formatSlotDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function formatSlotTime(value: string) {
  return new Date(value).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
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

  const photoUrl = resolveMediaUrl(data?.tutor.profilePhotoUrl);

  return (
    <div className="brand-page min-h-screen">
      <AppHeader />
      <main className="mx-auto w-full max-w-[1280px] px-4 pb-16 pt-5 sm:px-6 lg:px-8">
        {isLoading ? (
          <div className="space-y-6">
            <div className="h-[430px] animate-pulse rounded-[2rem] bg-primary-deep/10 sm:h-[360px]" />
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
              <div className="h-72 animate-pulse rounded-[1.75rem] bg-white/70" />
              <div className="h-[520px] animate-pulse rounded-[1.75rem] bg-white/70" />
            </div>
          </div>
        ) : data ? (
          <>
            <section className="relative overflow-hidden rounded-[2rem] border border-white/15 bg-[linear-gradient(135deg,var(--palette-navy-deep)_0%,var(--palette-navy)_58%,var(--palette-coral)_100%)] px-5 py-6 text-white shadow-[0_28px_70px_rgba(15,23,40,0.22)] sm:px-7 sm:py-8 lg:px-10">
              <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
              <div className="absolute -bottom-28 left-1/3 h-72 w-72 rounded-full bg-secondary-color/30 blur-3xl" />
              <div className="absolute inset-0 opacity-20 [background-image:radial-gradient(rgba(255,255,255,0.26)_1px,transparent_1px)] [background-size:26px_26px]" />

              <div className="relative grid gap-7 md:grid-cols-[220px_minmax(0,1fr)] md:items-center lg:grid-cols-[250px_minmax(0,1fr)]">
                <div className="relative mx-auto aspect-[4/5] w-full max-w-[250px] overflow-hidden rounded-[1.75rem] border border-white/25 bg-white/10 shadow-2xl">
                  {photoUrl && !photoFailed ? (
                    <Image
                      src={photoUrl}
                      alt={data.tutor.displayName}
                      className="h-full w-full object-cover"
                      fill
                      priority
                      sizes="(min-width: 1024px) 250px, (min-width: 768px) 220px, 80vw"
                      unoptimized
                      onError={() => setPhotoFailed(true)}
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-white/25 to-white/5 text-7xl font-bold text-white/80">
                      {data.tutor.displayName.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-primary-deep/70 to-transparent" />
                </div>

                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {data.tutor.verificationStatus === "approved" ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300/35 bg-emerald-400/15 px-3 py-1.5 text-xs font-semibold text-emerald-50 backdrop-blur">
                        <BadgeCheck className="h-4 w-4" />
                        Verified tutor
                      </span>
                    ) : null}
                    {data.tutor.firstLessonFree ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-light/35 bg-accent/20 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur">
                        <Sparkles className="h-3.5 w-3.5" />
                        First lesson free
                      </span>
                    ) : null}
                  </div>

                  <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
                    {data.tutor.displayName}
                  </h1>
                  <p className="mt-3 max-w-3xl text-base leading-7 text-white/75 sm:text-lg">
                    {data.tutor.headline || "A dedicated tutor ready to help you make meaningful progress."}
                  </p>

                  <div className="mt-5 flex flex-wrap gap-2 text-sm text-white/85">
                    <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 backdrop-blur">
                      <MapPin className="h-4 w-4 text-accent-light" />
                      {data.tutor.location ?? data.tutor.timezone}
                    </span>
                    {data.tutor.languages.map((language) => (
                      <span
                        key={language}
                        className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 capitalize backdrop-blur"
                      >
                        <Languages className="h-4 w-4 text-accent-light" />
                        {language}
                      </span>
                    ))}
                  </div>

                  <div className="mt-7 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl border border-white/12 bg-white/10 p-4 backdrop-blur">
                      <p className="text-xs font-medium uppercase tracking-[0.16em] text-white/55">Lesson rate</p>
                      <p className="mt-1 text-2xl font-bold">₦{data.tutor.hourlyRate.toLocaleString()}</p>
                      <p className="text-xs text-white/55">per hour</p>
                    </div>
                    <div className="rounded-2xl border border-white/12 bg-white/10 p-4 backdrop-blur">
                      <p className="text-xs font-medium uppercase tracking-[0.16em] text-white/55">Rating</p>
                      <p className="mt-1 flex items-center gap-1.5 text-2xl font-bold">
                        <Star className="h-5 w-5 fill-accent-light text-accent-light" />
                        {data.tutor.averageRating.toFixed(1)}
                      </p>
                      <p className="text-xs text-white/55">
                        {data.tutor.totalReviews} {data.tutor.totalReviews === 1 ? "review" : "reviews"}
                      </p>
                    </div>
                    <div className="col-span-2 rounded-2xl border border-white/12 bg-white/10 p-4 backdrop-blur sm:col-span-1">
                      <p className="text-xs font-medium uppercase tracking-[0.16em] text-white/55">Lessons</p>
                      <p className="mt-1 text-lg font-bold">
                        {availableTeachingModes.length === 2
                          ? "Online & in person"
                          : formatTeachingMode(availableTeachingModes[0])}
                      </p>
                      <p className="text-xs text-white/55">Flexible learning</p>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <div className="mt-6 grid items-start gap-2 lg:grid-cols-[minmax(0,1fr)_400px]">
              <aside id="booking-panel" className="order-first lg:order-last lg:sticky lg:top-24">
                <div className="overflow-hidden rounded-[1.75rem] border border-border bg-white shadow-[0_24px_58px_rgba(15,23,40,0.1)]">
                  <div className="border-b border-border bg-[linear-gradient(135deg,var(--palette-coral-mist)_0%,rgba(239,226,232,0.75)_100%)] px-10 py-5">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Start learning</p>
                        <h2 className="brand-heading mt-1 text-2xl font-bold">Book a lesson</h2>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-bold text-primary-deep">₦{data.tutor.hourlyRate.toLocaleString()}</p>
                        <p className="text-xs text-muted">per hour</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 p-6">
                    <div className="grid gap-2">
                      <div className="text-sm font-semibold text-primary-deep">How would you like to learn?</div>
                      <div className="grid grid-cols-2 gap-2">
                        {availableTeachingModes.map((mode) => {
                          const label = formatTeachingMode(mode);
                          const isSelected = lessonType === label;
                          const ModeIcon = mode === "webcam" ? Monitor : GraduationCap;
                          return (
                            <button
                              key={mode}
                              type="button"
                              onClick={() => setLessonType(label)}
                              className={`flex min-h-20 flex-col items-center justify-center gap-2 rounded-2xl border px-3 py-3 text-sm font-semibold transition ${isSelected
                                ? "border-primary-deep bg-primary-deep text-white shadow-lg shadow-primary-deep/15"
                                : "border-border bg-surface text-primary-deep hover:-translate-y-0.5 hover:border-accent/35 hover:bg-accent-soft/50"
                                }`}
                            >
                              <ModeIcon className={`h-5 w-5 ${isSelected ? "text-accent-light" : "text-accent"}`} />
                              {label}
                            </button>
                          );
                        })}
                      </div>
                      {data.tutor.videoCallUrl && lessonType === "Webcam" ? (
                        <div className="rounded-xl bg-info-soft px-3 py-2 text-xs leading-5 text-info-foreground">
                          Webcam bookings include a video room link on the bookings page.
                        </div>
                      ) : null}
                    </div>

                    <Input
                      label="What would you like help with?"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Share your learning goals"
                    />

                    <div className="rounded-2xl border border-border bg-surface p-4">
                      <div className="flex items-center gap-2 text-sm font-semibold text-primary-deep">
                        <Clock3 className="h-4 w-4 text-accent" />
                        Request a preferred time
                      </div>
                      <div className="mt-3 grid gap-2">
                        <Input label="From" type="datetime-local" value={rangeFrom} onChange={(e) => setRangeFrom(e.target.value)} />
                        <Input label="To" type="datetime-local" value={rangeTo} onChange={(e) => setRangeTo(e.target.value)} />
                      </div>
                    </div>

                    {submitState ? (
                      <div className="rounded-xl border border-success/20 bg-success/10 px-3 py-2 text-sm leading-6 text-success">
                        {submitState}
                      </div>
                    ) : null}
                    {error ? (
                      <div className="rounded-xl border border-danger/20 bg-red-50 px-3 py-2 text-sm leading-6 text-danger">
                        {error}
                      </div>
                    ) : null}

                    <Button
                      size="lg"
                      fullWidth
                      onClick={() => void submitBookingRequest()}
                      disabled={(isLoggedIn && !isStudent) || (isStudent && !selectedSlot && !(rangeFrom && rangeTo))}
                    >
                      Send booking request
                    </Button>
                    <Button
                      variant="secondary"
                      size="lg"
                      fullWidth
                      leftIcon={<MessageCircle className="h-4 w-4" />}
                      onClick={() => void startMessage()}
                      disabled={isLoggedIn && !isStudent}
                    >
                      Message tutor
                    </Button>

                    {!isLoggedIn ? (
                      <div className="text-center text-xs leading-5 text-muted">
                        You will be asked to create a student account before sending your request.
                      </div>
                    ) : !isStudent ? (
                      <div className="text-center text-xs leading-5 text-muted">
                        Log in as a student to request lessons and message tutors.
                      </div>
                    ) : null}
                  </div>
                </div>
              </aside>

              <section className="order-last space-y-6 lg:order-first">
                <article className="mb-3 rounded-[1.75rem] border border-border bg-white/90 p-6 shadow-[0_18px_45px_rgba(15,23,40,0.06)] sm:p-15">
                  <div className="flex items-center gap-2">
                    <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent-soft text-accent">
                      <BookOpen className="h-5 w-5" />
                    </span>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Meet your tutor</p>
                      <h2 className="text-2xl font-bold text-primary-deep">About {data.tutor.displayName}</h2>
                    </div>
                  </div>
                  <p className="mt-6 whitespace-pre-line text-base leading-8 text-foreground/80">
                    {data.tutor.bio || "This tutor has not added a biography yet."}
                  </p>

                  {data.tutor.responseTime ? (
                    <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-info-soft px-3 py-2 text-sm font-medium text-primary-deep">
                      <Clock3 className="h-4 w-4 text-accent" />
                      Usually responds {data.tutor.responseTime}
                    </div>
                  ) : null}
                </article>

                <article className="mb-3 rounded-[1.75rem] border border-border bg-white/90 p-6 shadow-[0_18px_45px_rgba(15,23,40,0.06)] sm:p-8">
                  <div className="flex items-center gap-2">
                    <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-soft text-primary-deep">
                      <GraduationCap className="h-5 w-5" />
                    </span>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-secondary-color">Expertise</p>
                      <h2 className="text-2xl font-bold text-primary-deep">Subjects taught</h2>
                    </div>
                  </div>

                  <div className="mt-6 flex flex-wrap gap-3">
                    {data.tutor.subjects.length ? (
                      data.tutor.subjects.map((subject) => (
                        <span
                          key={subject}
                          className="inline-flex items-center gap-2 rounded-full border border-info-border bg-info-soft px-4 py-2.5 text-sm font-semibold capitalize text-primary-deep"
                        >
                          <Check className="h-4 w-4 text-accent" />
                          {subject}
                        </span>
                      ))
                    ) : (
                      <p className="text-sm text-muted">No subjects have been added yet.</p>
                    )}
                  </div>
                </article>

                <article className="rounded-[1.75rem] border border-border bg-white/90 p-6 shadow-[0_18px_45px_rgba(15,23,40,0.06)] sm:p-8">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[rgba(245,184,65,0.18)] text-[#8b5e00]">
                        <CalendarDays className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8b5e00]">Plan ahead</p>
                        <h2 className="text-2xl font-bold text-primary-deep">Upcoming availability</h2>
                      </div>
                    </div>
                    {selectedSlot ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-3 py-1.5 text-xs font-semibold text-success">
                        <Check className="h-3.5 w-3.5" /> Slot selected
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-6 grid gap-3 sm:grid-cols-2">
                    {data.availability.length === 0 ? (
                      <div className="col-span-full rounded-2xl border border-dashed border-border-strong bg-surface px-5 py-8 text-center">
                        <Clock3 className="mx-auto h-7 w-7 text-accent" />
                        <p className="mt-3 font-semibold text-primary-deep">No public slots yet</p>
                        <p className="mt-1 text-sm leading-6 text-muted">
                          Use the booking form to request a time that works for you.
                        </p>
                      </div>
                    ) : (
                      data.availability.slice(0, 6).map((slot) => {
                        const isSelected = selectedSlotId === slot.id;
                        return (
                          <button
                            key={slot.id}
                            type="button"
                            onClick={() => setSelectedSlotId(slot.id)}
                            className={`flex items-center justify-between gap-3 rounded-2xl border p-4 text-left transition ${isSelected
                              ? "border-primary-deep bg-primary-deep text-white shadow-lg shadow-primary-deep/15"
                              : "border-border bg-surface text-primary-deep hover:-translate-y-0.5 hover:border-accent/35 hover:bg-accent-soft/40"
                              }`}
                          >
                            <div>
                              <p className="text-sm font-bold">{formatSlotDate(slot.startsAt)}</p>
                              <p className={`mt-1 text-xs ${isSelected ? "text-white/65" : "text-muted"}`}>
                                {formatSlotTime(slot.startsAt)} – {formatSlotTime(slot.endsAt)}
                              </p>
                            </div>
                            <span className={`flex h-8 w-8 items-center justify-center rounded-full ${isSelected ? "bg-white/15" : "bg-white"}`}>
                              {isSelected ? <Check className="h-4 w-4" /> : <CalendarDays className="h-4 w-4 text-accent" />}
                            </span>
                          </button>
                        );
                      })
                    )}
                  </div>
                </article>
              </section>
            </div>

            <article className="mt-3 rounded-[1.75rem] border border-border bg-white/90 p-6 shadow-[0_18px_45px_rgba(15,23,40,0.06)] sm:p-8">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent-soft text-accent">
                    <Star className="h-5 w-5 fill-accent text-accent" />
                  </span>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Student feedback</p>
                    <h2 className="text-2xl font-bold text-primary-deep">
                      Reviews <span className="text-muted">({reviews.length})</span>
                    </h2>
                  </div>
                </div>
                {isLoggedIn && isStudent && reviewableBookingId ? (
                  <Button variant="secondary" onClick={() => setShowReviewForm(!showReviewForm)}>
                    {showReviewForm ? "Cancel" : "Write a review"}
                  </Button>
                ) : null}
              </div>

              {!isLoggedIn ? (
                <div className="mt-5 rounded-2xl bg-info-soft px-4 py-3 text-sm leading-6 text-muted">
                  <Link href={`/login?next=${encodeURIComponent(nextPath)}`} className="font-semibold text-accent hover:underline">
                    Log in as a student
                  </Link>{" "}
                  to leave a review after a completed lesson.
                </div>
              ) : reviewNotice ? (
                <div className="mt-5 rounded-2xl bg-info-soft px-4 py-3 text-sm leading-6 text-muted">{reviewNotice}</div>
              ) : null}

              {showReviewForm ? (
                <div className="mt-5 rounded-2xl border border-info-border bg-info-soft/50 p-5">
                  <h3 className="text-lg font-bold text-primary-deep">Share your experience</h3>
                  <div className="mt-4 grid gap-4">
                    <div>
                      <label className="text-sm font-semibold text-primary-deep">Rating</label>
                      <div className="mt-2 flex gap-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            type="button"
                            onClick={() => setReviewRating(star)}
                            className="rounded-lg p-1 transition hover:scale-110 focus:outline-none focus:ring-2 focus:ring-accent/50"
                            aria-label={`Rate ${star} out of 5`}
                          >
                            <Star
                              className={`h-7 w-7 ${star <= reviewRating ? "fill-accent text-accent" : "text-border-strong"
                                }`}
                            />
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-semibold text-primary-deep">Comment</label>
                      <textarea
                        className="mt-2 w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm text-foreground shadow-sm placeholder:text-muted transition focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/10"
                        value={reviewComment}
                        onChange={(e) => setReviewComment(e.target.value)}
                        placeholder="Share your experience with this tutor..."
                        rows={4}
                      />
                    </div>
                    <Button onClick={() => void submitReview()} disabled={isSubmittingReview}>
                      {isSubmittingReview ? "Submitting..." : "Submit review"}
                    </Button>
                  </div>
                </div>
              ) : null}

              <div className="mt-6 space-y-3">
                {isLoadingReviews ? (
                  <div className="h-28 animate-pulse rounded-2xl bg-surface" />
                ) : reviews.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border-strong bg-surface px-5 py-8 text-center">
                    <MessageCircle className="mx-auto h-7 w-7 text-secondary-color" />
                    <p className="mt-3 font-semibold text-primary-deep">No reviews yet</p>
                    <p className="mt-1 text-sm text-muted">Be the first student to learn with this tutor.</p>
                  </div>
                ) : (
                  reviews.map((review) => (
                    <div key={review.id} className="rounded-2xl border border-border bg-surface p-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-primary-deep">{review.studentName}</p>
                          <div className="mt-1 flex gap-0.5" aria-label={`${review.rating} out of 5 stars`}>
                            {[1, 2, 3, 4, 5].map((star) => (
                              <Star
                                key={star}
                                className={`h-4 w-4 ${star <= review.rating ? "fill-accent text-accent" : "text-border-strong"
                                  }`}
                              />
                            ))}
                          </div>
                        </div>
                        <p className="text-xs text-muted">{new Date(review.createdAt).toLocaleDateString()}</p>
                      </div>
                      {review.comment ? (
                        <p className="mt-4 text-sm leading-7 text-foreground/75">{review.comment}</p>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </article>
          </>
        ) : (
          <div className="mx-auto max-w-xl rounded-[1.75rem] border border-border bg-white/90 p-8 text-center shadow-[0_24px_58px_rgba(15,23,40,0.08)]">
            <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-soft text-accent">
              <BookOpen className="h-6 w-6" />
            </span>
            <h1 className="mt-5 text-2xl font-bold text-primary-deep">Unable to load tutor profile</h1>
            <p className="mt-2 text-sm leading-6 text-muted">
              {error ?? "This tutor profile is no longer available."}
            </p>
            <Button className="mt-5" onClick={() => void load()}>
              Try again
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
