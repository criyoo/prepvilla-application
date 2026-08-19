"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { TutorCard } from "@prepvilla/types";
import { Heart } from "lucide-react";
import { Button } from "../shared/Button";
import { RequireAuth } from "../shared/RequireAuth";
import { api } from "../shared/api";
import { TutorCardView } from "../tutors/TutorCardView";

type FavoriteTutorsResponse = { results: TutorCard[] };
type FavoriteResponse = { ok: boolean; isFavorited: boolean };

export function DashboardFavoritesPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tutors, setTutors] = useState<TutorCard[]>([]);

  async function loadFavorites() {
    setIsLoading(true);
    setError(null);
    const res = await api.get<FavoriteTutorsResponse>("/api/me/favorite-tutors");
    if (!res.ok) {
      setError(res.error ?? "Failed to load favorites");
      setTutors([]);
      setIsLoading(false);
      return;
    }
    setTutors(res.data.results ?? []);
    setIsLoading(false);
  }

  useEffect(() => {
    void loadFavorites();
  }, []);

  async function handleFavoriteChange(tutorId: string, nextFavorited: boolean) {
    const res = nextFavorited
      ? await api.post<FavoriteResponse>(`/api/me/favorite-tutors/${tutorId}`)
      : await api.delete<FavoriteResponse>(`/api/me/favorite-tutors/${tutorId}`);

    if (!res.ok) {
      throw new Error(res.error ?? "Failed to update favorites");
    }

    if (nextFavorited) {
      await loadFavorites();
      return;
    }
    setTutors((prev) => prev.filter((item) => item.id !== tutorId));
  }

  return (
    <RequireAuth allow={["student"]}>
      <div className="grid gap-4">
        <div className="rounded-3xl border border-border bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-lg font-semibold">
                <Heart className="h-5 w-5 text-red-500" />
                Favorite Tutors
              </div>
              <p className="mt-1 text-sm text-muted">
                Tutors you saved from cards appear here for quick access.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={() => void loadFavorites()} disabled={isLoading}>
                Refresh
              </Button>
              <Link href="/search">
                <Button>Find tutors</Button>
              </Link>
            </div>
          </div>
        </div>

        {error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        {isLoading ? (
          <div className="tutor-card-grid">
            {Array.from({ length: 6 }).map((_, idx) => (
              <div key={idx} className="h-[420px] animate-pulse rounded-3xl border border-border bg-white" />
            ))}
          </div>
        ) : tutors.length === 0 ? (
          <div className="rounded-3xl border border-border bg-white p-8 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-500">
              <Heart className="h-5 w-5" />
            </div>
            <h2 className="mt-4 text-lg font-semibold">No favorites yet</h2>
            <p className="mt-1 text-sm text-muted">
              Tap the heart icon on tutor cards to save them here.
            </p>
            <div className="mt-5">
              <Link href="/search">
                <Button>Start searching</Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="tutor-card-grid">
            {tutors.map((tutor) => (
              <TutorCardView
                key={tutor.id}
                tutor={tutor}
                isFavorited
                onFavoriteChange={handleFavoriteChange}
                size="wide"
              />
            ))}
          </div>
        )}
      </div>
    </RequireAuth>
  );
}
