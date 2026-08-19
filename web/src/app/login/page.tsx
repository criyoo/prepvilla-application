import { Suspense } from "react";
import { AuthLoginPage } from "../ui/auth/AuthLoginPage";

export default function Page() {
  return (
    <Suspense fallback={<div className="h-[520px] animate-pulse rounded-2xl border border-border bg-surface-2" />}>
      <AuthLoginPage />
    </Suspense>
  );
}
