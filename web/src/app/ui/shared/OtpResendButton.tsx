"use client";

import { useEffect, useState } from "react";
import { Button } from "./Button";

type OtpResendButtonProps = {
  onResend: () => Promise<boolean>;
  label?: string;
  cooldownSeconds?: number;
  disabled?: boolean;
};

export function OtpResendButton({
  onResend,
  label = "Resend OTP",
  cooldownSeconds = 30,
  disabled = false,
}: OtpResendButtonProps) {
  const [secondsRemaining, setSecondsRemaining] = useState(0);
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    if (secondsRemaining <= 0) return;
    const timer = window.setInterval(() => {
      setSecondsRemaining((seconds) => Math.max(0, seconds - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [secondsRemaining]);

  async function handleResend() {
    if (disabled || isResending || secondsRemaining > 0) return;
    setIsResending(true);
    try {
      const sent = await onResend();
      if (sent) setSecondsRemaining(cooldownSeconds);
    } finally {
      setIsResending(false);
    }
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={() => void handleResend()}
      disabled={disabled || isResending || secondsRemaining > 0}
    >
      {isResending ? "Sending..." : secondsRemaining > 0 ? `Resend in ${secondsRemaining}s` : label}
    </Button>
  );
}
