import { Suspense } from "react";
import { TutorProfileRoutePage } from "../ui/tutors/TutorProfileRoutePage";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <TutorProfileRoutePage />
    </Suspense>
  );
}
