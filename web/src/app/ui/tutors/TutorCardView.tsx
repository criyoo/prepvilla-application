"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { TutorCard } from "@prepvilla/types";
import { clsx } from "clsx";
import { Heart, Star } from "lucide-react";
import { useAuthStore } from "../shared/authStore";
import { resolveMediaUrl } from "../shared/media";
import { buildTutorProfileHref } from "../shared/routes";

function formatMoney(rate: number | null | undefined) {
  if (typeof rate !== "number" || Number.isNaN(rate) || rate <= 0) {
    return "Rate on profile";
  }
  return `₦${rate.toLocaleString()}/hr`;
}

function formatTeachingModeSummary(modes: string[]) {
  const normalized = Array.from(new Set(modes));
  const hasFaceToFace = normalized.includes("face_to_face");
  const hasWebcam = normalized.includes("webcam");

  if (hasFaceToFace && hasWebcam) {
    return "Face-to-face & Webcam";
  }
  if (hasWebcam) {
    return "Webcam";
  }
  return "Face-to-face";
}

type Props = {
  tutor: TutorCard;
  showFavorite?: boolean;
  isFavorited?: boolean;
  onFavoriteChange?: (tutorId: string, nextFavorited: boolean) => Promise<void> | void;
  size?: "default" | "wide";
};

export function TutorCardView({
  tutor,
  showFavorite = true,
  isFavorited = false,
  onFavoriteChange,
}: Props) {
  const router = useRouter();
  const role = useAuthStore((s) => s.role);
  const isLoggedIn = useAuthStore((s) => Boolean(s.accessToken));
  const canFavorite = showFavorite && isLoggedIn && role === "student";
  const [favorited, setFavorited] = useState(isFavorited);
  const [isSavingFavorite, setIsSavingFavorite] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setFavorited(isFavorited);
  }, [isFavorited, tutor.id]);

  useEffect(() => {
    setImageFailed(false);
  }, [tutor.id, tutor.profilePhotoUrl]);

  const statusTone =
    tutor.verificationStatus === "approved"
      ? "success"
      : tutor.verificationStatus === "rejected"
        ? "danger"
        : "neutral";
  const statusLabel =
    tutor.verificationStatus === "approved"
      ? "Verified"
      : tutor.verificationStatus === "not_submitted"
        ? "Not verified"
        : tutor.verificationStatus;

  const photoUrl = useMemo(() => {
    const baseUrl = resolveMediaUrl(tutor.profilePhotoUrl);
    if (!baseUrl) return null;
    const separator = baseUrl.includes("?") ? "&" : "?";
    let hash = 0;
    for (let i = 0; i < baseUrl.length; i++) {
      hash = (hash << 5) - hash + baseUrl.charCodeAt(i);
      hash &= hash;
    }
    return `${baseUrl}${separator}_v=${Math.abs(hash)}`;
  }, [tutor.profilePhotoUrl]);

  const locationLabel = tutor.location ?? tutor.timezone;
  const teachingModes = tutor.teachingModes?.length ? tutor.teachingModes : ["face_to_face"];
  const teachingModeSummary = formatTeachingModeSummary(teachingModes);
  const subjectsLine = tutor.subjects.length
    ? tutor.subjects.length > 3
      ? `${tutor.subjects.slice(0, 3).join(", ")} +${tutor.subjects.length - 3}`
      : tutor.subjects.join(", ")
    : "General tutoring";

  async function handleFavoriteClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!canFavorite || isSavingFavorite) return;

    const next = !favorited;
    setFavorited(next);
    setIsSavingFavorite(true);
    try {
      if (onFavoriteChange) {
        await onFavoriteChange(tutor.id, next);
      }
    } catch {
      setFavorited(!next);
    } finally {
      setIsSavingFavorite(false);
    }
  }

  const destinationHref = buildTutorProfileHref(tutor.id);

  function handleTutorPhotoClick(event: React.MouseEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest("button")) return;
    router.push(destinationHref);
  }

  function handleTutorPhotoKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest("button")) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    router.push(destinationHref);
  }

  const card = (
    <article className="group relative w-full">
      <div
        role="link"
        tabIndex={0}
        aria-label={`View ${tutor.displayName}'s profile`}
        onClick={handleTutorPhotoClick}
        onKeyDown={handleTutorPhotoKeyDown}
        className="relative cursor-pointer overflow-hidden rounded-[30px] border border-transparent shadow-sm transition-shadow duration-300 hover:shadow-xl"
      >
        {photoUrl && !imageFailed ? (
          <Image
            className="pointer-events-none absolute inset-0 h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-120"
            src={photoUrl}
            alt={tutor.displayName}
            fill
            loading="lazy"
            sizes="(min-width: 1280px) 320px, (min-width: 768px) 45vw, 100vw"
            unoptimized={process.env.NODE_ENV !== "production"}
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-primary-soft via-surface to-accent/15">
            <span className="text-7xl font-bold text-primary-deep">
              {tutor.displayName.charAt(0).toUpperCase()}
            </span>
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/82 via-black/22 to-black/10" />
        <div className="absolute inset-x-0 top-0 z-40 flex items-start justify-between p-3">
          {canFavorite ? (
            <button
              type="button"
              aria-label={favorited ? "Remove from favorites" : "Save to favorites"}
              onClick={(e) => void handleFavoriteClick(e)}
              disabled={isSavingFavorite}
              className={`inline-flex h-9 w-9 items-center justify-center rounded-full border transition ${favorited
                ? "border-red-500 bg-red-500 text-white"
                : "border-surface/60 bg-surface/92 text-primary-deep hover:bg-surface hover:text-red-500"
                }`}
            >
              <Heart className="h-4 w-4" fill={favorited ? "currentColor" : "none"} />
            </button>
          ) : (
            <div />
          )}
        </div>
        <div className="relative z-10 flex h-[var(--tutor-card-image-height)] items-end p-3 text-white">
          <div className="max-w-[100%]">
            <div className="line-clamp-1 text-lg font-semibold drop-shadow-lg">{tutor.displayName}</div>
            <div className="mt-1 line-clamp-1 text-sm font-medium text-white/90">
              {locationLabel || "Location not set"} <span className="text-white/75">({teachingModeSummary})</span>
            </div>
          </div>
        </div>
      </div>

      <div className="px-1 pt-3">
        <div className="flex items-center justify-between gap-3 text-sm leading-tight text-foreground">
          <span className="inline-flex items-center gap-1.5 font-medium">
            <Star className="h-5 w-5 fill-orange-500 text-orange-500" />
            <span>{tutor.averageRating.toFixed(1)} ({tutor.totalReviews} reviews)</span>
          </span>
          <span
            className={clsx(
              "inline-flex items-center rounded-full border px-2 py-0.5 text-sm font-medium leading-tight",
              statusTone === "neutral" && "border-border bg-surface text-muted",
              statusTone === "success" && "border-success/30 bg-success/10 text-success",
              statusTone === "danger" && "border-danger/30 bg-danger/10 text-danger",
            )}
          >
            {statusLabel}
          </span>
        </div>
        <div className="mt-1 text-sm leading-tight text-foreground">
          <span className="line-clamp-1">{subjectsLine}</span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-sm leading-tight text-foreground">
          <span className="font-medium">{formatMoney(tutor.hourlyRate)}</span>
          {tutor.firstLessonFree ? (
            <>
              <span className="text-muted">.</span>
              <span className="font-medium text-accent">1st lesson free</span>
            </>
          ) : null}
        </div>
      </div>
    </article>
  );

  return card;
}
