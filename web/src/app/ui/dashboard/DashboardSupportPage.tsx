"use client";

import { useEffect, useState } from "react";
import { Headset, Mail, MessageSquareMore, PhoneCall } from "lucide-react";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { Textarea } from "../shared/Textarea";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";

type Notification = {
  type: "success" | "error";
  message: string;
};

type MeResponse = {
  fullName: string;
  displayName: string;
  email: string;
};

const SUPPORT_EMAIL = "support@prepvilla.info";
const SUPPORT_PHONE = "+2348099446062";

export function DashboardSupportPage() {
  const role = useAuthStore((s) => s.role);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState<Notification | null>(null);

  useEffect(() => {
    let active = true;
    void api.get<MeResponse>("/api/me").then((response) => {
      if (!active || !response.ok) return;
      setFullName(response.data.fullName || response.data.displayName || "");
      setEmail(response.data.email || "");
    });
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) {
      setNotification({ type: "error", message: "Subject and message are required." });
      return;
    }

    setIsSubmitting(true);
    setNotification(null);
    const res = await api.post<{ ok: boolean }>("/api/support/contact", {
      subject: subject.trim(),
      message: message.trim(),
    });
    setIsSubmitting(false);

    if (!res.ok) {
      setNotification({ type: "error", message: res.error || "Failed to send support request." });
      return;
    }

    setSubject("");
    setMessage("");
    setNotification({ type: "success", message: "Your support request has been sent." });
  }

  if (role !== "tutor") {
    return (
      <div className="form-panel rounded-2xl p-6">
        <h1 className="brand-heading text-[24px] font-semibold leading-[32px]">Support</h1>
        <p className="mt-2 text-[14px] leading-[22px] text-black/65">
          The tutor support page is only available for tutor accounts.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-black/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.98)_0%,rgba(247,241,232,0.98)_58%,rgba(239,226,232,0.92)_100%)] p-8 shadow-[0_22px_44px_rgba(15,23,40,0.08)]">
        <div className="flex items-center gap-4">
          <div className="rounded-full bg-[linear-gradient(135deg,var(--palette-navy-deep)_0%,var(--palette-coral)_100%)] p-3 text-white shadow-[0_18px_30px_rgba(15,23,40,0.18)]">
            <Headset className="h-8 w-8" />
          </div>
          <div>
            <h1 className="brand-heading text-[32px] font-bold leading-[40px]">Support</h1>
            <p className="text-[16px] leading-[24px] text-black/65">
              Contact PrepVilla support for locked profile fields, account help, and verification questions.
            </p>
          </div>
        </div>
      </div>

      {notification ? (
        <div
          className={`rounded-xl border p-4 text-[14px] leading-[22px] ${
            notification.type === "success"
              ? "border-green-200 bg-green-50 text-green-800"
              : "border-red-200 bg-red-50 text-red-800"
          }`}
        >
          {notification.message}
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <form onSubmit={(e) => void handleSubmit(e)} className="form-panel rounded-2xl p-6">
          <div className="mb-4 flex items-center gap-3">
            <Mail className="h-5 w-5 text-[color:var(--palette-coral-deep)]" />
            <h2 className="text-[20px] font-semibold text-black">Email Support</h2>
          </div>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Input label="Full Name" value={fullName} disabled />
              <Input label="Email Address" type="email" value={email} disabled />
            </div>
            <Input
              label="Support Email"
              value={SUPPORT_EMAIL}
              disabled
            />
            <Input
              label="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="What do you need help with?"
              disabled={isSubmitting}
            />
            <Textarea
              label="Message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Describe the issue and include the field you need changed."
              disabled={isSubmitting}
            />
            <Button type="submit" disabled={isSubmitting || !subject.trim() || !message.trim()}>
              {isSubmitting ? "Sending..." : "Send to Support"}
            </Button>
          </div>
        </form>

        <div className="space-y-6">
          <div className="rounded-2xl border border-black/10 bg-white p-6 shadow-[0_18px_36px_rgba(15,23,42,0.06)]">
            <div className="mb-3 flex items-center gap-3">
              <MessageSquareMore className="h-5 w-5 text-[color:var(--palette-plum)]" />
              <h2 className="text-[20px] font-semibold">Chat with Support</h2>
            </div>
            <p className="text-[14px] leading-[22px] text-black/65">
              Live chat will be integrated here later. For now, please use the support form.
            </p>
            <Button variant="secondary" className="mt-4" disabled>
              Coming Soon
            </Button>
          </div>

          <div className="rounded-2xl border border-black/10 bg-white p-6 shadow-[0_18px_36px_rgba(15,23,42,0.06)]">
            <div className="mb-3 flex items-center gap-3">
              <PhoneCall className="h-5 w-5 text-[color:var(--palette-coral-deep)]" />
              <h2 className="text-[20px] font-semibold">Call Support On</h2>
            </div>
            <a href={`tel:${SUPPORT_PHONE}`} className="mt-3 inline-block text-[18px] font-semibold text-primary-deep underline underline-offset-4">
              {SUPPORT_PHONE}
            </a>
            <p className="mt-2 text-[12px] leading-[18px] text-black/55">
              Or drop you contact number via email and we will get back to you within 48hrs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
