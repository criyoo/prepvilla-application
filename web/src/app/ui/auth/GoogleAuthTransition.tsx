"use client";

import { Chrome, LoaderCircle } from "lucide-react";

type GoogleAuthTransitionProps = {
  action: "login" | "signup";
  phase: "authorizing" | "completing";
};

export function GoogleAuthTransition({ action, phase }: GoogleAuthTransitionProps) {
  const isCompleting = phase === "completing";
  const title = action === "login" ? "Signing you in" : "Creating your account";
  const message = isCompleting
    ? "Google verified your identity. We are opening your account now."
    : "Complete the secure Google authentication window to continue.";

  return (
    <div className="brand-page min-h-screen px-4 py-6 sm:py-10">
      <main className="mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-[520px] items-center justify-center sm:min-h-[calc(100vh-5rem)]">
        <section
          className="form-panel w-full rounded-[28px] p-8 text-center backdrop-blur-sm sm:p-10"
          aria-live="polite"
          aria-busy="true"
        >
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-white shadow-sm">
            {isCompleting ? (
              <LoaderCircle className="h-7 w-7 animate-spin text-[color:var(--palette-coral-deep)]" />
            ) : (
              <Chrome className="h-7 w-7 text-[color:var(--palette-coral-deep)]" />
            )}
          </div>
          <h1 className="brand-heading mt-5 text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-black/65">{message}</p>
        </section>
      </main>
    </div>
  );
}
