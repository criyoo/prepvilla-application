"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, Chrome, Lock, Mail } from "lucide-react";
import type { UserRole } from "@prepvilla/types";
import { AppHeader } from "../shared/AppHeader";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { OtpResendButton } from "../shared/OtpResendButton";
import { api } from "../shared/api";
import { requestGoogleAuthorizationCode } from "../shared/googleMeet";
import { useAuthStore } from "../shared/authStore";
import { AuthCard } from "./AuthCard";
import { GoogleAuthTransition } from "./GoogleAuthTransition";
import BrandLogo from "../shared/BrandLogo";

type SignupResponse = {
  message: string;
  pendingEmail: string;
};

type VerifiedSignupResponse = {
  accessToken: string;
  refreshToken: string;
  defaultDashboardPath?: string;
  user: {
    id: string;
    role: UserRole;
    displayName: string;
    fullName?: string;
    firstName?: string;
    middleName?: string;
    lastName?: string;
    email?: string;
  };
};

type SignupVariant = "student" | "tutor";

type GoogleStartResponse = {
  clientId: string;
};

function mapGoogleAuthError(errorCode: string | null): string | null {
  if (!errorCode) return null;
  const map: Record<string, string> = {
    google_auth_failed: "Google sign up could not be completed. Please try again.",
    google_not_configured: "Google sign up is currently unavailable.",
    invalid_state: "The Google sign up session expired. Please try again.",
    email_not_verified: "Your Google email address is not verified.",
    google_token_missing: "Google sign up failed. Please try again.",
    google_email_missing: "Could not read your Google email address.",
    google_audience_mismatch: "Google sign up failed validation.",
    account_role_mismatch: "An account already exists for this email with a different role.",
  };
  return map[errorCode] || "Sign up failed. Please try again.";
}

function composeFullName(firstName: string, middleName: string, lastName: string) {
  return [firstName, middleName, lastName]
    .map((value) => value.trim())
    .filter(Boolean)
    .join(" ");
}

type AuthSignupPageProps = {
  signupRole: SignupVariant;
  hideHeaderMenu?: boolean;
  hideHeaderActions?: boolean;
};

export function AuthSignupPage({
  signupRole,
  hideHeaderMenu = false,
  hideHeaderActions = false,
}: AuthSignupPageProps) {
  const router = useRouter();
  const clearSession = useAuthStore((s) => s.clear);
  const setSession = useAuthStore((s) => s.setSession);
  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [pendingEmail, setPendingEmail] = useState("");
  const [isPendingOtp, setIsPendingOtp] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [googleAuthPhase, setGoogleAuthPhase] = useState<"idle" | "authorizing" | "completing">("idle");
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const role: UserRole = signupRole;
  const isTutorFlow = signupRole === "tutor";

  useEffect(() => {
    const callbackError = new URLSearchParams(window.location.search).get("error");
    const mappedError = mapGoogleAuthError(callbackError);
    if (mappedError) setError(mappedError);
  }, []);

  async function onSubmit() {
    setIsSubmitting(true);
    setError(null);
    try {
      if (!email.trim()) {
        setError("Email is required");
        return;
      }
      if (!password || password.length < 6) {
        setError("Password must be at least 6 characters");
        return;
      }
      const submittedFullName = composeFullName(firstName, middleName, lastName);
      if (!firstName.trim() || !lastName.trim()) {
        setError("First name and last name are required");
        return;
      }

      if (!isTutorFlow) {
        if (password !== confirmPassword) {
          setError("Passwords do not match");
          return;
        }
      }

      const payload: Record<string, unknown> = {
        email: email.trim(),
        password,
        role,
        fullName: submittedFullName,
        firstName: firstName.trim(),
        middleName: middleName.trim(),
        lastName: lastName.trim(),
      };

      const res = await api.post<SignupResponse>("/api/auth/signup", payload);

      if (!res.ok) {
        setError(res.error);
        return;
      }

      setPendingEmail(res.data.pendingEmail);
      setIsPendingOtp(true);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function verifyOtp() {
    setIsVerifying(true);
    setError(null);
    try {
      const res = await api.post<VerifiedSignupResponse>("/api/auth/verify-otp", {
        email: pendingEmail,
        otp,
      });

      if (!res.ok) {
        setError(res.error || "Invalid OTP");
        return;
      }
      if (isTutorFlow) {
        setSession({
          accessToken: res.data.accessToken,
          refreshToken: res.data.refreshToken,
          userId: res.data.user.id,
          role: res.data.user.role,
          displayName: res.data.user.displayName,
        });
        router.push(res.data.defaultDashboardPath || "/dashboard/verification");
        return;
      }
      clearSession();
      router.push(`/login?verified=1&email=${encodeURIComponent(pendingEmail)}`);
    } finally {
      setIsVerifying(false);
    }
  }

  async function resendSignupOtp(): Promise<boolean> {
    const submittedFullName = composeFullName(firstName, middleName, lastName);
    const res = await api.post<SignupResponse>("/api/auth/signup", {
      email: pendingEmail || email.trim(),
      password,
      role,
      fullName: submittedFullName,
      firstName: firstName.trim(),
      middleName: middleName.trim(),
      lastName: lastName.trim(),
    });
    if (!res.ok) {
      setError(res.error || "Could not resend the verification code");
      return false;
    }
    setOtp("");
    setError(null);
    return true;
  }

  async function startGoogleSignup() {
    setGoogleAuthPhase("authorizing");
    setError(null);
    try {
      const res = await api.get<GoogleStartResponse>(`/api/auth/google/start?mode=signup&role=${signupRole}`);
      if (!res.ok) {
        setError(res.error || "Google sign up is unavailable right now.");
        setGoogleAuthPhase("idle");
        return;
      }
      const code = await requestGoogleAuthorizationCode(res.data.clientId);
      setGoogleAuthPhase("completing");
      const exchange = await api.postWithHeaders<VerifiedSignupResponse>(
        "/api/auth/google/exchange",
        { code, mode: "signup", role: signupRole },
        { "X-Requested-With": "XmlHttpRequest" },
      );
      if (!exchange.ok) {
        setError(mapGoogleAuthError(exchange.error) || exchange.error);
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
      router.replace(exchange.data.defaultDashboardPath || "/dashboard");
    } catch {
      setError("Google sign up could not be completed. Please try again.");
      setGoogleAuthPhase("idle");
    }
  }

  if (googleAuthPhase !== "idle") {
    return <GoogleAuthTransition action="signup" phase={googleAuthPhase} />;
  }

  if (isPendingOtp) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader hideMenu={hideHeaderMenu} hideActions={hideHeaderActions} />
        <main className="mx-auto w-full max-w-[500px] px-4 pb-10 pt-10">
          <AuthCard title="Verify Email" subtitle={`Enter the OTP sent to ${pendingEmail}`}>
            <Input
              label="OTP Code"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              placeholder="Enter 6-digit OTP"
              maxLength={6}
            />
            {error && <div className="mt-2 text-[14px] leading-[22px] text-danger">{error}</div>}
            <Button disabled={otp.length !== 6 || isVerifying} onClick={verifyOtp}>
              {isVerifying ? "Verifying..." : "Verify & Complete Signup"}
            </Button>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-center text-[14px] leading-[22px] text-black/65">
              <span>Didn&apos;t receive OTP?</span>
              <OtpResendButton onResend={resendSignupOtp} />
              <button className="font-semibold text-black hover:text-[color:var(--palette-coral-deep)] hover:underline" onClick={() => setIsPendingOtp(false)}>
                Go back
              </button>
            </div>
          </AuthCard>
        </main>
      </div>
    );
  }

  if (isTutorFlow) {
    return (
      <div className="brand-page min-h-screen">
        <AppHeader hideMenu={hideHeaderMenu} hideActions={hideHeaderActions} />
        <main className="mx-auto w-full max-w-[1400px] px-4 pb-12 pt-6 md:px-8">
          {/* <div className="flex justify-center mb-4">
            <BrandLogo className="mt-6 h-48 w-48 w-auto" />
          </div> */}
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <section className="mt-12 brand-hero relative overflow-hidden rounded-[36px] p-6 text-white md:p-10">
              <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-surface/22 blur-3xl" />
              <div className="absolute -bottom-20 left-1/3 h-56 w-56 rounded-full bg-accent/20 blur-3xl" />
              <div className="relative">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/80">Become A Tutor</p>
                <h1 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight md:text-5xl">
                  Share your passion and start earning by teaching students.
                </h1>
                <p className="mt-4 max-w-2xl text-sm text-white/85 md:text-base">
                  Create your tutor account in minutes, get verified, and connect with students who need your expertise.
                </p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {[
                    "Create your tutor profile and set your hourly rate.",
                    "Choose your subjects and availability.",
                    "Receive lesson requests from verified students.",
                    "Grow your reputation with reviews.",
                  ].map((item) => (
                    <div
                      key={item}
                      className="inline-flex items-start gap-2 rounded-2xl border border-surface/35 bg-surface/14 px-3 py-3 text-sm leading-5 backdrop-blur"
                    >
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-white" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-8 inline-flex items-center gap-2 rounded-full border border-surface/35 bg-surface/14 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white/85">
                  Start today
                  <ArrowRight className="h-3.5 w-3.5" />
                </div>
              </div>
            </section>

            <section className="mt-10 form-panel w-full rounded-[30px] p-6 sm:p-8">
              <h2 className="brand-heading text-[28px] font-semibold leading-[36px]">Create Tutor Account</h2>
              <p className="mt-1 text-sm text-muted">
                Sign up with your email and password, or continue with Google SSO.
              </p>

              <div className="mt-6 grid gap-3">
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  <Input
                    label="First name"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="First name"
                    inputSize="lg"
                  />
                  <Input
                    label="Middle name"
                    value={middleName}
                    onChange={(e) => setMiddleName(e.target.value)}
                    placeholder="Middle name (optional)"
                    inputSize="lg"
                  />
                  <Input
                    label="Last name"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="Last name"
                    inputSize="lg"
                  />
                </div>
                <Input
                  label="Email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  leftIcon={<Mail className="h-5 w-5" />}
                  inputSize="lg"
                />
                <Input
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  leftIcon={<Lock className="h-5 w-5" />}
                  inputSize="lg"
                />
                <Button
                  fullWidth
                  size="lg"
                  disabled={isSubmitting || !firstName.trim() || !lastName.trim() || !email.trim() || !password}
                  onClick={() => void onSubmit()}
                >
                  {isSubmitting ? "Sending..." : "Send verification code"}
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
                disabled={googleAuthPhase !== "idle" || isSubmitting}
                onClick={() => void startGoogleSignup()}
              >
                Sign up with Google
              </Button>

              {error ? (
                <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div>
              ) : null}

              <div className="mt-6 text-center text-[14px] leading-[22px] text-black/65">
                Already have an account?{" "}
                <Link className="font-semibold text-black hover:text-[color:var(--palette-coral-deep)] hover:underline" href="/login">
                  Sign in
                </Link>
              </div>
            </section>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="brand-page min-h-screen">
      <AppHeader hideMenu={hideHeaderMenu} hideActions={hideHeaderActions} />
      <main className="mx-auto w-full max-w-[1200px] px-4 pb-10 pt-10">
        <AuthCard
          title="Create student account"
          subtitle="Enter your details, verify the OTP, then sign in to start booking lessons."
          className="max-w-[540px] rounded-[30px] p-6 shadow-[0_24px_54px_rgba(15,23,42,0.08)] sm:p-8"
        >
          <div className="flex justify-center mb-4">
            <BrandLogo className="h-20 w-auto" />
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <Input
              label="First name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="First name"
            />
            <Input
              label="Middle name"
              value={middleName}
              onChange={(e) => setMiddleName(e.target.value)}
              placeholder="Middle name (optional)"
            />
            <Input
              label="Last name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Last name"
            />
          </div>
          <Input
            label="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min 6 characters"
          />
          <Input
            label="Confirm Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
          />
          <Button
            disabled={isSubmitting || !firstName.trim() || !lastName.trim() || !email.trim() || !password || !confirmPassword}
            onClick={() => void onSubmit()}
          >
            {isSubmitting ? "Sending..." : "Send verification code"}
          </Button>

          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-black/10" />
            <span className="text-sm text-black/45">or</span>
            <div className="h-px flex-1 bg-black/10" />
          </div>

          <Button
            fullWidth
            variant="google"
            leftIcon={<Chrome className="h-4 w-4" />}
            disabled={googleAuthPhase !== "idle" || isSubmitting}
            onClick={() => void startGoogleSignup()}
          >
            Sign up with Google
          </Button>
          {error ? <div className="mt-2 text-[14px] leading-[22px] text-danger">{error}</div> : null}
          <div className="mt-4 text-[14px] leading-[22px] text-black/65">
            Already have an account?{" "}
            <Link className="font-semibold text-black hover:text-[color:var(--palette-coral-deep)] hover:underline" href="/login">
              Sign in
            </Link>
          </div>
        </AuthCard>
      </main>
    </div>
  );
}
