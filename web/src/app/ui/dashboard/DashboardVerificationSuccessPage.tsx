"use client";

import { CheckCircle2, FileText, LayoutDashboard } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "../shared/Button";

export function DashboardVerificationSuccessPage() {
  const router = useRouter();

  return (
    <div className="grid gap-4">
      <div className="rounded-2xl border border-border bg-surface-2 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-[22px] font-semibold leading-[30px]">Documents Verified Successfully</h1>
            <p className="mt-1 text-[14px] leading-[22px] text-muted">
              Your documents have been received and verified for testing purposes.
            </p>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-border bg-surface">
            <CheckCircle2 className="h-5 w-5 text-accent" />
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-border bg-surface-2">
        <div className="grid gap-3 p-5">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-surface">
              <FileText className="h-4 w-4 text-muted" />
            </div>
            <div className="min-w-0">
              <div className="text-[14px] font-semibold leading-[22px]">What happens next</div>
              <div className="mt-1 text-[14px] leading-[22px] text-muted">
                You can return to your dashboard to see your verification status as Approved.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-surface">
              <LayoutDashboard className="h-4 w-4 text-muted" />
            </div>
            <div className="min-w-0">
              <div className="text-[14px] font-semibold leading-[22px]">Return to dashboard</div>
              <div className="mt-1 text-[14px] leading-[22px] text-muted">
                Continue setting availability, responding to messages, and managing bookings.
              </div>
            </div>
          </div>

          <div className="mt-2 flex flex-wrap gap-2">
            <Button onClick={() => router.push("/dashboard")}>Return to Dashboard</Button>
            <Button variant="secondary" onClick={() => router.push("/dashboard/verification")}>
              Back to Verification
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

