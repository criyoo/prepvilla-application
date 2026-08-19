"use client";

import { useSearchParams } from "next/navigation";
import { AppHeader } from "../shared/AppHeader";
import { TutorProfilePage } from "./TutorProfilePage";

export function TutorProfileRoutePage() {
  const searchParams = useSearchParams();
  const tutorId = searchParams.get("id")?.trim() ?? "";

  if (!tutorId) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <main className="mx-auto flex min-h-[calc(100vh-6rem)] w-full max-w-[720px] items-center px-4 pb-10 pt-6">
          <div className="w-full rounded-2xl border border-border bg-surface-2 p-6 text-center">
            <h1 className="text-[24px] font-semibold leading-[32px] text-gray-900">
              Tutor not specified
            </h1>
            <p className="mt-2 text-[14px] leading-[22px] text-muted">
              Open a tutor profile from search results or favorites to view the full details.
            </p>
          </div>
        </main>
      </div>
    );
  }

  return <TutorProfilePage tutorId={tutorId} />;
}
