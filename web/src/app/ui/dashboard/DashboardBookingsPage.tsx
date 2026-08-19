"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Booking, BookingStatus } from "@prepvilla/types";
import { Button } from "../shared/Button";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";

type BookingRow = Booking & {
  tutorName: string;
  studentName: string;
  tutorPhotoUrl?: string;
};

type BookingsResponse = { results: BookingRow[] };

function formatDateTime(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

function getStatusBadgeClass(status: BookingStatus) {
  switch (status) {
    case "confirmed":
      return "bg-green-100 text-green-700 border-green-200";
    case "requested":
      return "bg-yellow-100 text-yellow-700 border-yellow-200";
    case "rejected":
      return "bg-red-100 text-red-700 border-red-200";
    case "cancelled":
      return "bg-gray-100 text-gray-700 border-gray-200";
    case "completed":
      return "border-info-border bg-info-soft text-info-foreground";
    default:
      return "bg-gray-100 text-gray-700 border-gray-200";
  }
}

const statusTabs: { label: string; value: BookingStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Requested", value: "requested" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Completed", value: "completed" },
  { label: "Rejected", value: "rejected" },
  { label: "Cancelled", value: "cancelled" },
];

export function DashboardBookingsPage() {
  const role = useAuthStore((s) => s.role);
  const router = useRouter();
  const [status, setStatus] = useState<BookingStatus | "all">("all");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<BookingRow[]>([]);

  const filtered = useMemo(() => {
    if (status === "all") return rows;
    return rows.filter((b) => b.status === status);
  }, [rows, status]);

  async function load() {
    setIsLoading(true);
    setError(null);
    const res = await api.get<BookingsResponse>("/api/bookings");
    if (!res.ok) {
      setError(res.error);
      setRows([]);
      setIsLoading(false);
      return;
    }
    setRows(res.data.results || []);
    setIsLoading(false);
  }

  useEffect(() => {
    void load();
  }, []);

  async function cancel(bookingId: string) {
    const res = await api.post<{ ok: true }>(`/api/bookings/${bookingId}/cancel`, {});
    if (!res.ok) {
      setError(res.error);
      return;
    }
    await load();
  }

  async function confirm(bookingId: string) {
    const res = await api.post<{ ok: true }>(`/api/bookings/${bookingId}/confirm`, {});
    if (!res.ok) {
      setError(res.error);
      return;
    }
    await load();
  }

  async function reject(bookingId: string) {
    const res = await api.post<{ ok: true }>(`/api/bookings/${bookingId}/reject`, {});
    if (!res.ok) {
      setError(res.error);
      return;
    }
    await load();
  }

  async function confirmCompletion(bookingId: string) {
    const res = await api.post<{
      ok: true;
      status: BookingStatus;
      awaitingOtherConfirmation?: boolean;
    }>(`/api/bookings/${bookingId}/complete`, {});
    if (!res.ok) {
      setError(res.error);
      return;
    }
    await load();
  }

  function getPhotoUrl(url?: string) {
    if (!url) return null;
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    return `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8500"}${url.startsWith("/") ? "" : "/"}${url}`;
  }

  return (
    <div className="grid gap-4">
      <div className="rounded-2xl border border-border bg-surface-2 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-[18px] font-semibold leading-[28px]">Bookings</h1>
            <p className="mt-1 text-[14px] leading-[22px] text-muted">
              View and manage your bookings.
            </p>
          </div>
          <Button variant="secondary" onClick={load} disabled={isLoading}>
            Refresh
          </Button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {statusTabs.map((t) => (
            <button
              key={t.value}
              onClick={() => setStatus(t.value)}
              className={
                status === t.value
                  ? "rounded-full bg-surface px-3 py-1 text-[14px] leading-[22px]"
                  : "rounded-full border border-border bg-transparent px-3 py-1 text-[14px] leading-[22px] text-muted hover:bg-surface"
              }
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {error ? <div className="text-[14px] leading-[22px] text-danger">{error}</div> : null}

      <div className="overflow-hidden rounded-2xl border border-border bg-surface-2">
        <div className="grid grid-cols-1 divide-y divide-border">
          {isLoading ? (
            <div className="p-4 text-[14px] leading-[22px] text-muted">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="p-4 text-[14px] leading-[22px] text-muted">No bookings</div>
          ) : (
            filtered.map((b) => (
              <div key={b.id} className="grid gap-3 p-4 sm:grid-cols-[1fr_auto] sm:items-center">
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    {/* Tutor Photo - Only show for students */}
                    {role === "student" && (
                      <div className="shrink-0">
                        {b.tutorPhotoUrl ? (
                          <img
                            src={getPhotoUrl(b.tutorPhotoUrl) || ""}
                            alt={b.tutorName}
                            className="h-12 w-12 rounded-full object-cover"
                          />
                        ) : (
                          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-200 text-lg font-medium text-gray-500">
                            {(role === "student" ? b.tutorName : b.studentName)?.charAt(0).toUpperCase() || "?"}
                          </div>
                        )}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="truncate text-[16px] font-semibold leading-[24px]">
                          {role === "student" ? b.tutorName : b.studentName}
                        </div>
                        <div className={`rounded-full border px-2 py-0.5 text-[12px] leading-[18px] ${getStatusBadgeClass(b.status)}`}>
                          {b.status}
                        </div>
                      </div>
                      <div className="mt-1 text-[14px] leading-[22px] text-muted">
                        {b.startsAt ? `Starts: ${formatDateTime(b.startsAt)}` : "Not scheduled"}
                      </div>
                      <div className="mt-1 text-[13px] leading-[20px] text-muted">
                        Lesson method: {b.lessonType || "Lesson"}
                      </div>
                      {b.notes ? <div className="mt-1 text-[14px] leading-[22px]">{b.notes}</div> : null}
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {b.videoCallUrl ? (
                    <Button
                      variant="secondary"
                      onClick={() =>
                        router.push(
                          b.videoCallUrl || `/dashboard/video-room?bookingId=${encodeURIComponent(b.id)}`,
                        )
                      }
                    >
                      Open Video Room
                    </Button>
                  ) : null}
                  {role === "tutor" && b.status === "requested" ? (
                    <>
                      <Button variant="primary" onClick={() => void confirm(b.id)}>
                        Accept
                      </Button>
                      <Button variant="destructive" onClick={() => void reject(b.id)}>
                        Reject
                      </Button>
                    </>
                  ) : null}
                  {b.status === "confirmed" && b.endsAt && new Date(b.endsAt).getTime() <= Date.now()
                    ? (role === "student" ? b.studentCompletedAt : b.tutorCompletedAt) ? (
                        <Button variant="secondary" disabled>
                          Completion confirmed
                        </Button>
                      ) : (
                        <Button variant="primary" onClick={() => void confirmCompletion(b.id)}>
                          Confirm lesson completed
                        </Button>
                      )
                    : null}
                  {b.status !== "cancelled" && b.status !== "completed" && b.status !== "rejected" ? (
                    <Button variant="secondary" onClick={() => void cancel(b.id)}>
                      Cancel
                    </Button>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
