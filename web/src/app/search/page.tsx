import { Suspense } from "react";
import { SearchPage } from "../ui/search/SearchPage";

export default function Page() {
  return (
    <Suspense fallback={<div className="h-[720px] animate-pulse rounded-2xl border border-border bg-surface-2" />}>
      <SearchPage />
    </Suspense>
  );
}
