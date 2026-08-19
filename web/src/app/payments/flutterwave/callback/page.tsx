import { Suspense } from "react";
import FlutterwaveCallbackPage from "../../../ui/payments/FlutterwaveCallbackPage";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-[520px]" aria-busy="true" />}>
      <FlutterwaveCallbackPage />
    </Suspense>
  );
}
