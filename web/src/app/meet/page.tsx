import { Suspense } from "react";
import { PublicMeetRoomPage } from "../ui/meet/PublicMeetRoomPage";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <PublicMeetRoomPage />
    </Suspense>
  );
}
