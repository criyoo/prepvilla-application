"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { UserRole } from "@prepvilla/types";
import { AppHeader } from "../../../ui/shared/AppHeader";
import { Button } from "../../../ui/shared/Button";
import { useAuthStore } from "../../../ui/shared/authStore";

function GoogleAuthCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const callbackError = searchParams.get("error");
    if (callbackError) {
      setError("Google authentication could not be completed. Please try again.");
      return;
    }

    const accessToken = searchParams.get("accessToken");
    const refreshToken = searchParams.get("refreshToken");
    const userId = searchParams.get("userId");
    const roleParam = searchParams.get("role");
    const displayName = searchParams.get("displayName");
    const redirectTo = searchParams.get("redirectTo");

    if (!accessToken || !refreshToken || !userId || !roleParam) {
      setError("Missing authentication details from Google authentication.");
      return;
    }
    if (roleParam !== "student" && roleParam !== "tutor" && roleParam !== "admin") {
      setError("Invalid role returned from Google authentication.");
      return;
    }

    setSession({
      accessToken,
      refreshToken,
      userId,
      role: roleParam as UserRole,
      displayName: displayName || "User",
    });
    const safeRedirect =
      redirectTo && redirectTo.startsWith("/") && !redirectTo.startsWith("//")
        ? redirectTo
        : roleParam === "student"
          ? "/dashboard/profile"
          : roleParam === "tutor"
            ? "/dashboard/verification"
            : "/dashboard";
    router.replace(safeRedirect);
  }, [searchParams, router, setSession]);

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="mx-auto w-full max-w-[560px] px-4 pb-10 pt-12">
        <div className="rounded-2xl border border-border bg-surface-2 p-6">
          <h1 className="text-xl font-semibold">Completing Google authentication</h1>
          {error ? (
            <>
              <p className="mt-2 text-sm text-danger">{error}</p>
              <div className="mt-5">
                <Link href="/login">
                  <Button>Back to Login</Button>
                </Link>
              </div>
            </>
          ) : (
            <p className="mt-2 text-sm text-muted">Please wait while we sign you in...</p>
          )}
        </div>
      </main>
    </div>
  );
}

export default function GoogleAuthCallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <GoogleAuthCallbackContent />
    </Suspense>
  );
}
