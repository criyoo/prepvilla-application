import { Suspense } from "react";
import { DashboardMessagesPage } from "../../ui/dashboard/DashboardMessagesPage";

export default function Page() {
  return (
    <Suspense fallback={<div className="h-[520px] animate-pulse rounded-2xl border border-border bg-surface-2" />}>
      <DashboardMessagesPage />
    </Suspense>
  );
}
