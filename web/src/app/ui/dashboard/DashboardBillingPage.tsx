"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Clock3, CreditCard, Crown, History, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "../shared/api";
import { Button } from "../shared/Button";
import { useAuthStore } from "../shared/authStore";

type SubscriptionPlan = {
  code: "free" | "silver" | "gold" | "platinum";
  name: string;
  price: number;
  durationDays: number;
  badge: string;
  summary: string;
  features: string[];
};

type SubscriptionCatalog = {
  currency: string;
  plans: SubscriptionPlan[];
};

type SubscriptionPayment = {
  id: string;
  plan: string;
  planName: string;
  amount: string;
  currency: string;
  status: "pending" | "completed" | "failed" | "cancelled";
  transactionId: string;
  paymentLink: string;
  paidAt: string | null;
  createdAt: string;
  expiresAt: string | null;
};

type SubscriptionHistory = { results: SubscriptionPayment[] };

type CheckoutResponse = {
  id: string;
  transactionId: string;
  status: SubscriptionPayment["status"];
  paymentLink: string;
  amount: string;
  currency: string;
};

const planStyles: Record<SubscriptionPlan["code"], { icon: typeof Sparkles; iconClass: string; cardClass: string }> = {
  free: {
    icon: Sparkles,
    iconClass: "bg-accent-soft text-accent-hover",
    cardClass: "border-[rgba(240,100,73,0.26)] bg-[linear-gradient(180deg,#fff_0%,#fff7f1_100%)]",
  },
  silver: {
    icon: ShieldCheck,
    iconClass: "bg-slate-100 text-slate-700",
    cardClass: "border-slate-200 bg-[linear-gradient(180deg,#fff_0%,#f8fafc_100%)]",
  },
  gold: {
    icon: Crown,
    iconClass: "bg-amber-100 text-amber-700",
    cardClass: "border-amber-300 bg-[linear-gradient(180deg,#fffdf5_0%,#fff7dc_100%)]",
  },
  platinum: {
    icon: CreditCard,
    iconClass: "bg-[rgba(15,23,40,0.12)] text-primary-deep",
    cardClass: "border-[rgba(15,23,40,0.24)] bg-[linear-gradient(180deg,#fff_0%,#efe2e8_100%)]",
  },
};

function formatPrice(amount: number | string, currency: string) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(Number(amount || 0));
}

function formatDate(value: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat("en-NG", { day: "numeric", month: "short", year: "numeric" }).format(date);
}

function statusClass(status: SubscriptionPayment["status"]) {
  if (status === "completed") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "pending") return "border-amber-200 bg-amber-50 text-amber-700";
  if (status === "failed") return "border-red-200 bg-red-50 text-red-700";
  return "border-slate-200 bg-slate-50 text-slate-600";
}

export default function DashboardBillingPage() {
  const role = useAuthStore((state) => state.role);
  const [catalog, setCatalog] = useState<SubscriptionCatalog | null>(null);
  const [payments, setPayments] = useState<SubscriptionPayment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadBilling = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    const [catalogResult, historyResult] = await Promise.all([
      api.get<SubscriptionCatalog>("/api/payments/subscriptions/plans"),
      api.get<SubscriptionHistory>("/api/payments/subscriptions"),
    ]);

    if (!catalogResult.ok) {
      setError(catalogResult.error);
      setIsLoading(false);
      return;
    }
    if (!historyResult.ok) {
      setError(historyResult.error);
      setIsLoading(false);
      return;
    }

    setCatalog(catalogResult.data);
    setPayments(historyResult.data.results || []);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void loadBilling();
  }, [loadBilling]);

  useEffect(() => {
    const checkoutStatus = new URLSearchParams(window.location.search).get("checkout");
    if (checkoutStatus === "success") setNotice("Your subscription payment was confirmed successfully.");
    if (checkoutStatus === "cancelled") setNotice("Checkout was cancelled. You can choose a package whenever you are ready.");
    if (checkoutStatus === "failed") setError("We could not confirm that payment. Please try again.");
  }, []);

  const activeSubscription = useMemo(
    () => payments.find((payment) => payment.status === "completed" && payment.expiresAt && new Date(payment.expiresAt).getTime() >= Date.now()) || null,
    [payments],
  );
  const hasUsedFreePackage = payments.some((payment) => payment.plan === "free" && payment.status === "completed");

  async function choosePlan(plan: SubscriptionPlan) {
    setSelectedPlan(plan.code);
    setError(null);
    setNotice(null);
    const result = await api.post<CheckoutResponse>("/api/payments/subscriptions/checkout", { plan: plan.code });
    if (!result.ok) {
      setError(result.error);
      setSelectedPlan(null);
      return;
    }

    if (result.data.status === "completed") {
      setNotice(`${plan.name} is now active on your account.`);
      setSelectedPlan(null);
      await loadBilling();
      return;
    }

    if (!result.data.paymentLink) {
      setError("Checkout could not be started. Please try again.");
      setSelectedPlan(null);
      return;
    }

    window.location.assign(result.data.paymentLink);
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-black/10 bg-[linear-gradient(135deg,var(--palette-navy-deep)_0%,var(--palette-navy)_64%,var(--palette-coral)_100%)] p-6 text-white shadow-[0_24px_48px_rgba(15,23,40,0.2)] sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-2xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[12px] font-semibold uppercase tracking-[0.14em]">
              <CreditCard className="h-4 w-4" />
              Billing & Subscription
            </div>
            <h1 className="text-[30px] font-bold leading-tight sm:text-[38px]">Choose a package that fits your goals</h1>
            <p className="mt-3 max-w-xl text-[15px] leading-6 text-white/78">
              Flexible access for every {role === "tutor" ? "tutor" : "student"}, with secure checkout and a clear payment history.
            </p>
          </div>
          <div className="rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm">
            <div className="text-[12px] font-semibold uppercase tracking-[0.14em] text-white/65">Current package</div>
            <div className="mt-2 text-[20px] font-bold">{activeSubscription?.planName || "No active package"}</div>
            <div className="mt-1 flex items-center gap-2 text-[13px] text-white/75">
              <Clock3 className="h-4 w-4" />
              {activeSubscription ? `Active until ${formatDate(activeSubscription.expiresAt)}` : "Select a package below"}
            </div>
          </div>
        </div>
      </section>

      {notice ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-[14px] text-emerald-800">{notice}</div> : null}
      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[14px] text-red-700">{error}</div> : null}

      {isLoading || !catalog ? (
        <div className="rounded-2xl border border-border bg-white p-8 text-center text-[14px] text-muted">Loading subscription packages...</div>
      ) : (
        <section>
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-[22px] font-bold text-primary-deep">Subscription packages</h2>
              <p className="mt-1 text-[14px] text-muted">All paid packages provide 30 days of access.</p>
            </div>
            <Button variant="secondary" size="sm" onClick={() => void loadBilling()} disabled={isLoading} leftIcon={<RefreshCw className="h-4 w-4" />}>
              Refresh
            </Button>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {catalog.plans.map((plan) => {
              const style = planStyles[plan.code];
              const Icon = style.icon;
              const isCurrent = activeSubscription?.plan === plan.code;
              const freePackageUnavailable = plan.code === "free" && hasUsedFreePackage && !isCurrent;
              return (
                <article
                  key={plan.code}
                  className={`relative flex min-h-[660px] flex-col rounded-[24px] border p-5 shadow-[0_16px_36px_rgba(15,23,40,0.07)] transition hover:-translate-y-1 hover:shadow-[0_22px_42px_rgba(15,23,40,0.12)] ${style.cardClass} ${isCurrent ? "ring-2 ring-accent ring-offset-2" : ""}`}
                >
                  {plan.code === "gold" ? (
                    <div className="absolute right-4 top-4 rounded-full bg-amber-500 px-3 py-1 text-[12px] font-bold uppercase tracking-wide text-white">Most popular</div>
                  ) : null}
                  <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${style.iconClass}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="mt-5 text-[12px] font-bold uppercase tracking-[0.18em] text-muted">{plan.badge}</div>
                  <h3 className="mt-1 text-[16px] font-semibold text-primary-deep">{plan.name}</h3>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-[24px] font-semibold font-black tracking-tight text-primary-deep">{formatPrice(plan.price, catalog.currency)}</span>
                    {plan.price > 0 ? <span className="text-[13px] text-muted">/ 30 days</span> : null}
                  </div>
                  <p className="mt-3 min-h-12 text-[14px] leading-6 text-muted">{plan.summary}</p>
                  <ul className="mt-5 space-y-3">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex gap-2 text-[13px] leading-5 text-primary-deep">
                        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white shadow-sm">
                          <Check className="h-3.5 w-3.5 text-emerald-600" />
                        </span>
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-auto pt-6">
                    <Button
                      fullWidth
                      variant={plan.code === "gold" ? "gradient" : "primary"}
                      onClick={() => void choosePlan(plan)}
                      isLoading={selectedPlan === plan.code}
                      disabled={Boolean(selectedPlan) || isCurrent || freePackageUnavailable}
                    >
                      {isCurrent ? "Current package" : freePackageUnavailable ? "Free package used" : plan.price === 0 ? "Start free" : "Choose package"}
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      <section className="overflow-hidden rounded-[24px] border border-border bg-white shadow-[0_16px_36px_rgba(15,23,40,0.06)]">
        <div className="flex items-center gap-3 border-b border-border px-5 py-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft text-primary-deep">
            <History className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-[18px] font-bold text-primary-deep">Billing history</h2>
            <p className="text-[13px] text-muted">Your subscription activations and checkout attempts.</p>
          </div>
        </div>
        {payments.length === 0 ? (
          <div className="px-5 py-10 text-center text-[14px] text-muted">No billing history yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-[13px]">
              <thead className="bg-surface-2 text-primary-deep">
                <tr>
                  <th className="px-5 py-3 font-semibold">Package</th>
                  <th className="px-5 py-3 font-semibold">Amount</th>
                  <th className="px-5 py-3 font-semibold">Date</th>
                  <th className="px-5 py-3 font-semibold">Valid until</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {payments.map((payment) => (
                  <tr key={payment.id}>
                    <td className="px-5 py-4 font-semibold text-primary-deep">{payment.planName}</td>
                    <td className="px-5 py-4 text-muted">{formatPrice(payment.amount, payment.currency)}</td>
                    <td className="px-5 py-4 text-muted">{formatDate(payment.paidAt || payment.createdAt)}</td>
                    <td className="px-5 py-4 text-muted">{formatDate(payment.expiresAt)}</td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold capitalize ${statusClass(payment.status)}`}>{payment.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
