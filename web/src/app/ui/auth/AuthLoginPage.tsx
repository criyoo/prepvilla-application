"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Chrome, Lock, Mail, X } from "lucide-react";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { api } from "../shared/api";
import { requestGoogleAuthorizationCode } from "../shared/googleMeet";
import { useAuthStore } from "../shared/authStore";
import type { UserRole } from "@prepvilla/types";
import { GoogleAuthTransition } from "./GoogleAuthTransition";

type LoginResponse = {
  accessToken: string;
  refreshToken: string;
  user: { id: string; role: UserRole; displayName: string };
  defaultDashboardPath: string;
};

type GoogleStartResponse = {
  clientId: string;
};

function mapAuthError(errorCode: string | null): string | null {
  if (!errorCode) return null;
  const map: Record<string, string> = {
    google_auth_failed: "Google sign in could not be completed. Please try again.",
    account_not_found: "No account was found for this Google email.",
    google_not_configured: "Google sign in is currently unavailable.",
    invalid_state: "The Google sign in session expired. Please try again.",
    email_not_verified: "Your Google email address is not verified.",
    google_token_missing: "Google sign in failed. Please try again.",
    google_email_missing: "Could not read your Google email address.",
    google_audience_mismatch: "Google sign in failed validation.",
  };
  return map[errorCode] || "Sign in failed. Please try again.";
}

export function AuthLoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useAuthStore((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [googleAuthPhase, setGoogleAuthPhase] = useState<"idle" | "authorizing" | "completing">("idle");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const nextPath = useMemo(() => {
    const value = searchParams.get("next");
    if (!value) return null;
    if (!value.startsWith("/") || value.startsWith("//")) return null;
    return value;
  }, [searchParams]);

  useEffect(() => {
    const nextError = mapAuthError(searchParams.get("error"));
    if (nextError) {
      setError(nextError);
    }
    const nextEmail = searchParams.get("email");
    if (nextEmail) {
      setEmail(nextEmail);
    }
    if (searchParams.get("verified") === "1") {
      setNotice("Email verified. Sign in to continue.");
    }
  }, [searchParams]);

  async function onSubmit() {
    setIsSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api.post<LoginResponse>("/api/auth/login", { email, password });
      if (!res.ok) {
        setError(res.error);
        return;
      }
      setSession({
        accessToken: res.data.accessToken,
        refreshToken: res.data.refreshToken,
        userId: res.data.user.id,
        role: res.data.user.role,
        displayName: res.data.user.displayName,
      });
      if (nextPath) {
        router.push(nextPath);
        return;
      }
      router.push(res.data.defaultDashboardPath || "/dashboard");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function startGoogleLogin() {
    setGoogleAuthPhase("authorizing");
    setError(null);
    try {
      const res = await api.get<GoogleStartResponse>("/api/auth/google/start?mode=login");
      if (!res.ok) {
        setError(res.error || "Google sign in is unavailable right now.");
        setGoogleAuthPhase("idle");
        return;
      }
      const code = await requestGoogleAuthorizationCode(res.data.clientId);
      setGoogleAuthPhase("completing");
      const exchange = await api.postWithHeaders<LoginResponse>(
        "/api/auth/google/exchange",
        { code, mode: "login" },
        { "X-Requested-With": "XmlHttpRequest" },
      );
      if (!exchange.ok) {
        setError(mapAuthError(exchange.error) || exchange.error);
        setGoogleAuthPhase("idle");
        return;
      }
      setSession({
        accessToken: exchange.data.accessToken,
        refreshToken: exchange.data.refreshToken,
        userId: exchange.data.user.id,
        role: exchange.data.user.role,
        displayName: exchange.data.user.displayName,
      });
      router.replace(nextPath || exchange.data.defaultDashboardPath || "/dashboard");
    } catch {
      setError("Google sign in could not be completed. Please try again.");
      setGoogleAuthPhase("idle");
    }
  }

  if (googleAuthPhase !== "idle") {
    return <GoogleAuthTransition action="login" phase={googleAuthPhase} />;
  }

  return (
    <div className="brand-page min-h-screen px-4 py-6 sm:py-10">
      <main className="mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-[560px] items-center justify-center sm:min-h-[calc(100vh-5rem)]">
        <section className="form-panel relative w-full rounded-[28px] p-6 backdrop-blur-sm sm:p-8">
          <Link
            href="/"
            className="absolute left-4 top-4 inline-flex h-9 w-9 items-center justify-center rounded-full border border-black/10 bg-white text-black/65 transition hover:-translate-y-0.5 hover:border-[rgba(139,97,120,0.36)] hover:bg-[var(--secondary-color-soft)] hover:text-black"
            aria-label="Close login"
          >
            <X className="h-5 w-5" />
          </Link>

          <h1 className="brand-heading mt-2 text-center text-3xl font-semibold tracking-tight">Log in</h1>
          <p className="mt-1 text-center text-sm text-black/65">Use the same sign-in method you used during registration.</p>

          <div className="mt-6 grid gap-3">
            <Input
              label="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              leftIcon={<Mail className="h-4 w-4" />}
              inputSize="lg"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              leftIcon={<Lock className="h-4 w-4" />}
              inputSize="lg"
            />
            <div className="text-right text-[13px] leading-[20px]">
              <Link className="font-medium text-black hover:text-[color:var(--palette-coral-deep)] hover:underline" href="/forgot-password">
                Forgot password?
              </Link>
            </div>
            <Button
              fullWidth
              size="lg"
              disabled={!email || !password || isSubmitting}
              onClick={() => void onSubmit()}
            >
              {isSubmitting ? "Logging in..." : "Log in"}
            </Button>
          </div>

          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-black/10" />
            <span className="text-sm text-black/45">or</span>
            <div className="h-px flex-1 bg-black/10" />
          </div>

          <Button
            fullWidth
            size="lg"
            variant="google"
            leftIcon={<Chrome className="h-4 w-4" />}
            disabled={googleAuthPhase !== "idle"}
            onClick={() => void startGoogleLogin()}
          >
            Log in with Google
          </Button>

          {notice ? <div className="mt-4 rounded-xl border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">{notice}</div> : null}
          {error ? <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}

          <div className="mt-6 text-center text-[14px] leading-[22px] text-black/65">
            Don&apos;t have an account?
            <div className="mt-1 flex items-center justify-center gap-2">
              <Link className="font-semibold text-black hover:text-[color:var(--palette-coral-deep)] hover:underline" href="/signup">
                Student sign up
              </Link>
              <span>•</span>
              <Link className="font-semibold text-black hover:text-[color:var(--palette-coral-deep)] hover:underline" href="/signup/tutor">
                Become a tutor
              </Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
