"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, LoaderCircle, XCircle } from "lucide-react";
import { api } from "../shared/api";
import { AppHeader } from "../shared/AppHeader";
import { RequireAuth } from "../shared/RequireAuth";

type VerificationResponse = {
  id: string;
  transactionId: string;
  status: "pending" | "completed" | "failed" | "cancelled";
};

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("Confirming your payment...");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const providerStatus = (searchParams.get("status") || "").toLowerCase();
    const transactionId = searchParams.get("transaction_id") || "";
    const transactionReference = searchParams.get("tx_ref") || "";

    if (providerStatus === "cancelled") {
      router.replace("/dashboard/billing?checkout=cancelled");
      return;
    }
    if (!transactionId) {
      setFailed(true);
      setMessage("The payment provider did not return a transaction to verify.");
      return;
    }

    const query = new URLSearchParams({ transaction_id: transactionId });
    if (transactionReference) query.set("tx_ref", transactionReference);

    void api.get<VerificationResponse>(`/api/payments/flutterwave/verify?${query.toString()}`).then((result) => {
      if (!result.ok || result.data.status !== "completed") {
        setFailed(true);
        setMessage(result.ok ? "Payment was not completed." : result.error);
        return;
      }
      router.replace("/dashboard/billing?checkout=success");
    });
  }, [router, searchParams]);

  return (
    <div className="mx-auto flex min-h-[520px] max-w-2xl items-center px-4 py-12">
      <div className="w-full rounded-[28px] border border-border bg-white p-8 text-center shadow-[0_24px_48px_rgba(15,23,40,0.1)]">
        <div className={`mx-auto flex h-16 w-16 items-center justify-center rounded-full ${failed ? "bg-red-50 text-red-600" : "bg-primary-soft text-primary-deep"}`}>
          {failed ? <XCircle className="h-8 w-8" /> : message.startsWith("Confirming") ? <LoaderCircle className="h-8 w-8 animate-spin" /> : <CheckCircle2 className="h-8 w-8" />}
        </div>
        <h1 className="mt-5 text-[24px] font-bold text-primary-deep">Subscription payment</h1>
        <p className="mt-2 text-[14px] leading-6 text-muted">{message}</p>
        {failed ? (
          <button type="button" onClick={() => router.replace("/dashboard/billing?checkout=failed")} className="mt-6 rounded-xl bg-primary-deep px-5 py-3 text-[14px] font-semibold text-white">
            Return to billing
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default function FlutterwaveCallbackPage() {
  return (
    <RequireAuth>
      <AppHeader />
      <CallbackContent />
    </RequireAuth>
  );
}
