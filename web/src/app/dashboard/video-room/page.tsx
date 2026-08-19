import { Suspense } from "react";
import { DashboardVideoRoomPage } from "../../ui/dashboard/DashboardVideoRoomPage";

export default function Page() {
  return (
    <Suspense fallback={<div className="h-[520px] animate-pulse rounded-2xl border border-border bg-surface-2" />}>
      <DashboardVideoRoomPage />
    </Suspense>
  );
}
