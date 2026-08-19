"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { AppHeader } from "../shared/AppHeader";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { OtpResendButton } from "../shared/OtpResendButton";
import { api } from "../shared/api";
import { AuthCard } from "./AuthCard";

type Step = "request" | "confirm" | "done";

export function AuthForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("request");

  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password1, setPassword1] = useState("");
  const [password2, setPassword2] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedEmail = useMemo(() => email.trim().toLowerCase(), [email]);

  async function requestCode(): Promise<boolean> {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await api.post<{ ok: boolean }>("/api/auth/password-reset/request", { email: normalizedEmail });
      if (!res.ok) {
        setError(res.error ?? "Request failed");
        return false;
      }
      setStep("confirm");
      return true;
    } finally {
      setIsSubmitting(false);
    }
  }

  async function confirmReset() {
    setIsSubmitting(true);
    setError(null);
    try {
      if (password1 !== password2) {
        setError("Passwords do not match");
        return;
      }
      if (password1.length < 6) {
        setError("Password must be at least 6 characters");
        return;
      }

      const res = await api.post<{ ok: boolean }>("/api/auth/password-reset/confirm", {
        email: normalizedEmail,
        code: code.trim().toUpperCase(),
        newPassword: password1,
      });

      if (!res.ok) {
        setError(res.error ?? "Reset failed");
        return;
      }
      setStep("done");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="brand-page min-h-screen">
      <AppHeader />
      <main className="mx-auto w-full max-w-[1200px] px-4 pb-10 pt-10">
        <AuthCard title="Reset password" subtitle="We’ll send a 6-character code to your email.">
          {step === "request" ? (
            <>
              <Input
                label="Registered email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
              {error ? <div className="text-[14px] leading-[22px] text-danger">{error}</div> : null}
              <Button disabled={!normalizedEmail || isSubmitting} onClick={requestCode}>
                {isSubmitting ? "Sending…" : "Send code"}
              </Button>
              <div className="text-[14px] leading-[22px] text-black/65">
                Remembered your password?{" "}
                <Link className="font-semibold text-black hover:text-[color:var(--palette-coral-deep)] hover:underline" href="/login">
                  Sign in
                </Link>
              </div>
            </>
          ) : step === "confirm" ? (
            <>
              <Input label="Email" value={normalizedEmail} disabled />
              <Input
                label="OTP code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="ABC123"
              />
              <Input
                label="New password"
                type="password"
                value={password1}
                onChange={(e) => setPassword1(e.target.value)}
                placeholder="••••••••"
              />
              <Input
                label="Confirm new password"
                type="password"
                value={password2}
                onChange={(e) => setPassword2(e.target.value)}
                placeholder="••••••••"
              />
              {error ? <div className="text-[14px] leading-[22px] text-danger">{error}</div> : null}
              <Button disabled={!code.trim() || !password1 || !password2 || isSubmitting} onClick={confirmReset}>
                {isSubmitting ? "Updating…" : "Update password"}
              </Button>
              <div className="flex items-center justify-between text-[14px] leading-[22px]">
                <OtpResendButton onResend={requestCode} label="Resend code" disabled={isSubmitting} />
                <Link className="font-semibold text-black hover:text-[color:var(--palette-coral-deep)] hover:underline" href="/login">
                  Back to sign in
                </Link>
              </div>
            </>
          ) : (
            <>
              <div className="form-inset rounded-xl p-3 text-[14px] leading-[22px] text-black/65">
                Your password has been updated. You can now sign in with your new password.
              </div>
              <Button onClick={() => router.push("/login")}>Go to sign in</Button>
            </>
          )}
        </AuthCard>
      </main>
    </div>
  );
}
