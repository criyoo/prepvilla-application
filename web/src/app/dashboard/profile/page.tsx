import { Suspense } from "react";
import { DashboardProfilePage } from "../../ui/dashboard/DashboardProfilePage";

export default function Page() {
  return (
    <Suspense fallback={<div className="h-[720px] animate-pulse rounded-2xl border border-border bg-surface-2" />}>
      <DashboardProfilePage />
    </Suspense>
  );
}
