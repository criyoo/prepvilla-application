"use client";

import Link from "next/link";
import { Bug, CircleAlert, Lightbulb, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { Select } from "../shared/Select";
import { Textarea } from "../shared/Textarea";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";

export type SupportRequestKind = "feedback" | "complaint" | "issue";

type Notification = { type: "success" | "error"; message: string };
type SubmissionResponse = { ok: true; id: string; ticketNumber: string; status: string };
type MeResponse = { fullName: string; displayName: string; email: string };

const requestConfig = {
  feedback: {
    eyebrow: "Feedback",
    title: "Help us improve PrepVilla",
    description: "Share a suggestion, an idea, or feedback about your experience.",
    subjectLabel: "Feedback title",
    subjectPlaceholder: "Summarise your suggestion",
    messageLabel: "Feedback or suggestion",
    messagePlaceholder: "Tell us what could be improved, why it matters, and what a better experience would look like.",
    submitLabel: "Send Feedback",
    icon: Lightbulb,
    iconClass: "bg-amber-100 text-amber-700",
    categories: [
      "General experience",
      "Tutor discovery and search",
      "Tutor profile",
      "Bookings and lessons",
      "Messaging",
      "Video lessons",
      "Payments and payouts",
      "Billing and subscriptions",
      "Verification",
      "Accessibility and usability",
      "New feature idea",
      "Other",
    ],
  },
  complaint: {
    eyebrow: "Complaint",
    title: "Send a complaint to support",
    description: "Tell the support team what happened and the outcome you are requesting.",
    subjectLabel: "Complaint title",
    subjectPlaceholder: "Summarise your complaint",
    messageLabel: "Complaint details",
    messagePlaceholder: "Explain what happened, when it happened, who was involved, and how you would like it resolved.",
    submitLabel: "Submit Complaint",
    icon: CircleAlert,
    iconClass: "bg-rose-100 text-rose-700",
    categories: [
      "Tutor or student conduct",
      "Booking or cancellation",
      "Lesson quality",
      "Payment or refund",
      "Tutor payout",
      "Subscription",
      "Verification decision",
      "Account restriction",
      "Privacy or safety",
      "Support experience",
      "Other",
    ],
  },
  issue: {
    eyebrow: "Issues",
    title: "Raise an issue for the admin team",
    description: "Report an account, booking, payment, or technical issue that needs investigation.",
    subjectLabel: "Issue summary",
    subjectPlaceholder: "Briefly describe the issue",
    messageLabel: "Issue details",
    messagePlaceholder: "Include the steps you took, what you expected, what happened instead, and any error message shown.",
    submitLabel: "Raise Issue",
    icon: Bug,
    iconClass: "bg-sky-100 text-sky-700",
    categories: [
      "Login or account access",
      "Profile update",
      "Tutor search",
      "Booking workflow",
      "Availability",
      "Messaging",
      "Video room",
      "Student payment",
      "Tutor payout",
      "Subscription activation",
      "Identity verification",
      "Upload or document",
      "Email or notification",
      "Page or display problem",
      "Other technical issue",
    ],
  },
} as const;

export function DashboardSupportRequestPage({ kind }: { kind: SupportRequestKind }) {
  const role = useAuthStore((state) => state.role);
  const config = requestConfig[kind];
  const Icon = config.icon;
  const [category, setCategory] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [relatedReference, setRelatedReference] = useState("");
  const [severity, setSeverity] = useState("normal");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState<Notification | null>(null);

  const normalizedRole = role ? ((role as string).toLowerCase() === "teacher" ? "tutor" : role) : null;
  const isSupportedRole = normalizedRole === "student" || normalizedRole === "tutor";

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

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!category || !subject.trim() || message.trim().length < 10) {
      setNotification({
        type: "error",
        message: "Choose a category, add a title, and provide at least 10 characters of detail.",
      });
      return;
    }

    setIsSubmitting(true);
    setNotification(null);
    const response = await api.post<SubmissionResponse>("/api/support/requests", {
      kind,
      topic: `${category}: ${subject.trim()}`,
      message: message.trim(),
      relatedReference: relatedReference.trim(),
      metadata: {
        category,
        severity: kind === "issue" ? severity : undefined,
        page: window.location.pathname,
        browser: navigator.userAgent,
      },
    });
    setIsSubmitting(false);

    if (!response.ok) {
      setNotification({ type: "error", message: response.error || `Unable to submit ${kind}.` });
      return;
    }

    setCategory("");
    setSubject("");
    setMessage("");
    setRelatedReference("");
    setSeverity("normal");
    setNotification({
      type: "success",
      message: `Thank you. Your ${kind} was submitted with ticket ${response.data.ticketNumber}.`,
    });
  }

  if (!isSupportedRole) {
    return (
      <div className="form-panel rounded-2xl p-6">
        <h1 className="brand-heading text-[24px] font-semibold leading-[32px]">{config.eyebrow}</h1>
        <p className="mt-2 text-[14px] leading-[22px] text-black/65">
          This page is available to student and tutor accounts.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-black/10 bg-[linear-gradient(135deg,#ffffff_0%,#f7f1e8_55%,#efe2e8_100%)] p-6 shadow-[0_22px_44px_rgba(15,23,40,0.08)] sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="flex max-w-3xl items-start gap-4">
            <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${config.iconClass}`}>
              <Icon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-[12px] font-semibold uppercase tracking-[0.16em] text-black/50">{config.eyebrow}</p>
              <h1 className="brand-heading mt-1 text-[28px] font-bold leading-tight text-primary-deep">{config.title}</h1>
              <p className="mt-2 text-[14px] leading-6 text-black/65">{config.description}</p>
            </div>
          </div>
          <Link
            href="/dashboard/faq"
            className="rounded-xl border border-black/10 bg-white px-4 py-2 text-[14px] font-semibold text-primary-deep transition hover:border-black/25"
          >
            Read FAQs
          </Link>
        </div>
      </section>

      {notification ? (
        <div className={`rounded-2xl border px-4 py-3 text-[14px] ${notification.type === "success"
          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
          : "border-red-200 bg-red-50 text-red-700"
          }`}>
          {notification.message}
        </div>
      ) : null}

      <form onSubmit={(event) => void submit(event)} className="form-panel rounded-2xl p-6">
        <div className="grid gap-5 md:grid-cols-2">
          <Input label="Full Name" value={fullName} disabled />
          <Input label="Email Address" type="email" value={email} disabled />
          <Input label="Account Type" value={normalizedRole || ""} disabled className="capitalize" />
          <Select
            label="Category"
            labelClassName="text-sm"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            options={[
              { value: "", label: "Select a category" },
              ...config.categories.map((item) => ({ value: item, label: item })),
            ]}
            disabled={isSubmitting}
          />
          <Input
            label={config.subjectLabel}
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            placeholder={config.subjectPlaceholder}
            maxLength={120}
            disabled={isSubmitting}
          />
          {kind !== "feedback" ? (
            <Input
              label="Related booking, payment, or transaction reference (optional)"
              value={relatedReference}
              onChange={(event) => setRelatedReference(event.target.value)}
              placeholder="Paste a reference if you have one"
              maxLength={160}
              disabled={isSubmitting}
            />
          ) : null}
          {kind === "issue" ? (
            <Select
              label="Severity"
              labelClassName="text-sm"
              value={severity}
              onChange={(event) => setSeverity(event.target.value)}
              options={[
                { value: "normal", label: "Normal - I can continue using PrepVilla" },
                { value: "high", label: "High - An important feature is blocked" },
                { value: "urgent", label: "Urgent - Payment, security, or account access" },
              ]}
              disabled={isSubmitting}
            />
          ) : null}
          <div className="md:col-span-2">
            <Textarea
              label={config.messageLabel}
              labelClassName="text-sm"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder={config.messagePlaceholder}
              maxLength={10000}
              className="min-h-48"
              disabled={isSubmitting}
            />
            <div className="mt-1 text-right text-[12px] text-black/45">{message.length}/10,000</div>
          </div>
        </div>
        <div className="mt-6 flex justify-end">
          <Button
            type="submit"
            leftIcon={<Send className="h-4 w-4" />}
            disabled={isSubmitting || !category || !subject.trim() || message.trim().length < 10}
          >
            {isSubmitting ? "Submitting..." : config.submitLabel}
          </Button>
        </div>
      </form>
    </div>
  );
}
