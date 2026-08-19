"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "../shared/RequireAuth";
import { Button } from "../shared/Button";
import { api } from "../shared/api";

type VerificationRequestRow = {
  id: string;
  tutorId: string;
  tutorName: string;
  status: "pending" | "approved" | "rejected";
  submittedAt: string;
  notes: string | null;
  documentUrl: string | null;
  documentUrls?: string[];
};

type QueueResponse = { results: VerificationRequestRow[] };

export function AdminVerificationPage() {
  const [rows, setRows] = useState<VerificationRequestRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [decisionNotes, setDecisionNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const selected = rows.find((r) => r.id === selectedId) ?? null;

  const load = useCallback(async () => {
    setError(null);
    const res = await api.get<QueueResponse>("/api/admin/verification-requests");
    if (!res.ok) {
      setError(res.error);
      setRows([]);
      return;
    }
    setRows(res.data.results);
    if (!selectedId && res.data.results[0]) setSelectedId(res.data.results[0].id);
  }, [selectedId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function approve() {
    if (!selected) return;
    setError(null);
    const res = await api.post<{ ok: true }>(`/api/admin/verification-requests/${selected.id}/approve`, { notes: decisionNotes });
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setDecisionNotes("");
    await load();
  }

  async function reject() {
    if (!selected) return;
    setError(null);
    const res = await api.post<{ ok: true }>(`/api/admin/verification-requests/${selected.id}/reject`, { notes: decisionNotes });
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setDecisionNotes("");
    await load();
  }

  return (
    <RequireAuth allow={["admin"]}>
      <div className="grid gap-4">
        <div className="form-panel rounded-2xl p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="brand-heading text-[24px] font-semibold leading-[32px]">Admin — Verification</h1>
              <p className="mt-1 text-[14px] leading-[22px] text-black/65">Review and decide tutor verification requests.</p>
            </div>
            <Button variant="secondary" onClick={load}>
              Refresh
            </Button>
          </div>
        </div>

        {error ? <div className="text-[14px] leading-[22px] text-danger">{error}</div> : null}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_420px]">
          <div className="overflow-hidden rounded-2xl border border-border bg-surface-2">
            <div className="border-b border-border p-3 text-[14px] font-semibold leading-[22px]">Queue</div>
            <div className="max-h-[560px] overflow-auto">
              {rows.length === 0 ? (
                <div className="p-3 text-[14px] leading-[22px] text-muted">No requests</div>
              ) : (
                rows.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    className={
                      selectedId === r.id
                        ? "w-full border-b border-border bg-surface px-3 py-3 text-left"
                        : "w-full border-b border-border px-3 py-3 text-left text-muted hover:bg-surface"
                    }
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-[14px] font-medium leading-[22px] text-foreground">{r.tutorName}</div>
                      <div className="rounded-full border border-border bg-surface px-2 py-0.5 text-[12px] leading-[18px] text-muted">
                        {r.status}
                      </div>
                    </div>
                    <div className="mt-1 text-[12px] leading-[18px]">{new Date(r.submittedAt).toLocaleString()}</div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-surface-2 p-4">
            {!selected ? (
              <div className="text-[14px] leading-[22px] text-muted">Select a request</div>
            ) : (
              <div className="grid gap-3">
                <div>
                  <div className="text-[14px] leading-[22px] text-muted">Tutor</div>
                  <div className="text-[18px] font-semibold leading-[28px]">{selected.tutorName}</div>
                </div>
                {selected.documentUrls && selected.documentUrls.length > 0 ? (
                  <div className="grid gap-2">
                    {selected.documentUrls.map((url) => (
                      <a
                        key={url}
                        className="text-[14px] leading-[22px] text-accent hover:underline"
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View submitted document
                      </a>
                    ))}
                  </div>
                ) : selected.documentUrl ? (
                  <a className="text-[14px] leading-[22px] text-accent hover:underline" href={selected.documentUrl} target="_blank" rel="noreferrer">
                    View submitted document
                  </a>
                ) : (
                  <div className="text-[14px] leading-[22px] text-muted">No document URL provided</div>
                )}
                {selected.notes ? (
                  <div className="rounded-xl border border-border bg-surface p-3 text-[14px] leading-[22px]">{selected.notes}</div>
                ) : null}
                <div className="grid gap-2">
                  <div className="text-[12px] font-medium leading-[18px] text-black/55">Decision notes</div>
                  <input
                    className="h-10 rounded-xl border border-black/12 bg-white px-3 text-[14px] leading-[22px] text-black shadow-sm focus:outline-none focus:ring-4 focus:ring-black/8 focus:border-black"
                    value={decisionNotes}
                    onChange={(e) => setDecisionNotes(e.target.value)}
                    placeholder="Reason, next steps, etc."
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => void approve()} disabled={selected.status !== "pending"}>
                    Approve
                  </Button>
                  <Button variant="destructive" onClick={() => void reject()} disabled={selected.status !== "pending"}>
                    Reject
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </RequireAuth>
  );
}
