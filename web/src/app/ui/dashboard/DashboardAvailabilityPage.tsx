"use client";

import { useEffect, useState } from "react";
import type { AvailabilitySlot } from "@prepvilla/types";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { RequireAuth } from "../shared/RequireAuth";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";
import { useFormDraft } from "../shared/useFormDraft";

type AvailabilityResponse = { results: AvailabilitySlot[] };

export function DashboardAvailabilityPage() {
  const userId = useAuthStore((state) => state.userId);
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const clearDraft = useFormDraft(
    userId ? `prepvilla.form-draft.${userId}.availability` : null,
    { startsAt, endsAt },
    (draft) => {
      if (typeof draft.startsAt === "string") setStartsAt(draft.startsAt);
      if (typeof draft.endsAt === "string") setEndsAt(draft.endsAt);
    },
  );

  async function load() {
    setError(null);
    const res = await api.get<AvailabilityResponse>("/api/tutors/me/availability");
    if (!res.ok) {
      setError(res.error);
      setSlots([]);
      return;
    }
    setSlots(res.data.results || []);
  }

  useEffect(() => {
    void load();
  }, []);

  async function saveAll(next: AvailabilitySlot[]) {
    setError(null);
    const res = await api.put<{ results: AvailabilitySlot[] }>("/api/tutors/me/availability", { slots: next });
    if (!res.ok) {
      setError(res.error);
      return false;
    }
    setSlots(res.data.results || []);
    return true;
  }

  async function addSlot() {
    if (!startsAt || !endsAt) return;
    const next: AvailabilitySlot[] = [
      ...slots,
      {
        id: `temp-${Date.now()}`,
        startsAt: new Date(startsAt).toISOString(),
        endsAt: new Date(endsAt).toISOString(),
      },
    ];
    if (await saveAll(next)) {
      clearDraft();
      setStartsAt("");
      setEndsAt("");
    }
  }

  return (
    <RequireAuth allow={["tutor"]}>
      <div className="grid gap-4">
        <div className="form-panel rounded-2xl p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="brand-heading text-[24px] font-semibold leading-[32px]">Availability</h1>
              <p className="mt-1 text-[14px] leading-[22px] text-black/65">Create orange edit availability slots, and let students know when you can be booked.</p>
            </div>
            <Button variant="secondary" onClick={load}>
              Refresh
            </Button>
          </div>
        </div>

        {error ? <div className="text-[14px] leading-[22px] text-danger">{error}</div> : null}

        <div className="form-panel rounded-2xl p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <Input
              label="Start"
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
            />
            <Input label="End" type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} />
            <div className="flex items-end">
              <Button className="w-full" onClick={() => void addSlot()} disabled={!startsAt || !endsAt}>
                Add slot
              </Button>
            </div>
          </div>
          <div className="mt-4 grid gap-2">
            {slots.length === 0 ? (
              <div className="text-[14px] leading-[22px] text-muted">No availability slots</div>
            ) : (
              slots
                .slice()
                .sort((a, b) => a.startsAt.localeCompare(b.startsAt))
                .map((s) => (
                  <div key={s.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface p-3">
                    <div className="text-[14px] leading-[22px]">
                      <div className="font-medium">{new Date(s.startsAt).toLocaleString()}</div>
                      <div className="text-muted">to {new Date(s.endsAt).toLocaleString()}</div>
                    </div>
                    <Button
                      variant="destructive"
                      onClick={() => void saveAll(slots.filter((x) => x.id !== s.id))}
                    >
                      Remove
                    </Button>
                  </div>
                ))
            )}
          </div>
        </div>
      </div>
    </RequireAuth>
  );
}
