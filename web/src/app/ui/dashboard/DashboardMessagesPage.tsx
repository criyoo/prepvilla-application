"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChatMessage, Conversation } from "@prepvilla/types";
import { Button } from "../shared/Button";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";

type ConversationsResponse = { results: Conversation[] };
type MessagesResponse = { results: ChatMessage[] };

function wsBaseUrl() {
  return process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8500";
}

function formatTimeHHMMSS(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-GB", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function mergeMessages(existing: ChatMessage[], incoming: ChatMessage[]) {
  const byId = new Map<string, ChatMessage>();
  for (const message of existing) {
    byId.set(message.id, message);
  }
  for (const message of incoming) {
    byId.set(message.id, message);
  }
  return Array.from(byId.values()).sort(
    (left, right) => new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime(),
  );
}

export function DashboardMessagesPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const userId = useAuthStore((s) => s.userId);
  const searchParams = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [realtimeConnected, setRealtimeConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectDelayRef = useRef(1000);

  // Check for conversationId in URL query params
  useEffect(() => {
    const conversationId = searchParams.get("conversationId");
    if (conversationId) {
      setSelectedId(conversationId);
    }
  }, [searchParams]);

  const selected = useMemo(() => conversations.find((c) => c.id === selectedId) ?? null, [conversations, selectedId]);
  const isBlocked = useMemo(() => selected?.isBlocked ?? false, [selected]);

  const loadConversations = useCallback(async (silent = false) => {
    if (!silent) {
      setError(null);
    }
    const res = await api.get<ConversationsResponse>("/api/conversations");
    if (!res.ok) {
      if (!silent) {
        setError(res.error);
        setConversations([]);
      }
      return;
    }
    setConversations(res.data.results || []);
    if (!selectedId && res.data.results?.[0]) setSelectedId(res.data.results[0].id);
  }, [selectedId]);

  const loadMessages = useCallback(async (conversationId: string, mode: "replace" | "merge" = "replace") => {
    if (mode === "replace") {
      setError(null);
    }
    const res = await api.get<MessagesResponse>(`/api/conversations/${conversationId}/messages`);
    if (!res.ok) {
      if (mode === "replace") {
        setError(res.error);
        setMessages([]);
      }
      return;
    }
    const nextMessages = res.data.results || [];
    setMessages((prev) => (mode === "merge" ? mergeMessages(prev, nextMessages) : nextMessages));
  }, []);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (!selectedId) return;
    setMessages([]);
    void loadMessages(selectedId);
  }, [selectedId, loadMessages]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void loadConversations(true);
    }, 20000);
    return () => window.clearInterval(intervalId);
  }, [loadConversations]);

  useEffect(() => {
    if (!selectedId || realtimeConnected) return;
    const intervalId = window.setInterval(() => {
      void loadMessages(selectedId, "merge");
    }, 10000);
    return () => window.clearInterval(intervalId);
  }, [selectedId, realtimeConnected, loadMessages]);

  useEffect(() => {
    if (!selectedId || !accessToken || isBlocked) return;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      const url = `${wsBaseUrl()}/ws/conversations/${selectedId}?token=${encodeURIComponent(accessToken)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        reconnectDelayRef.current = 1000;
        setRealtimeConnected(true);
      };
      ws.onmessage = (ev) => {
        try {
          const parsed = JSON.parse(ev.data) as { type: string; payload?: unknown };
          if (parsed.type === "message.created" && parsed.payload) {
            const msg = parsed.payload as ChatMessage;
            setMessages((prev) => mergeMessages(prev, [msg]));
            void loadConversations(true);
          }
        } catch {
          return;
        }
      };
      ws.onerror = () => {
        setError("WebSocket error");
      };
      ws.onclose = () => {
        wsRef.current = null;
        setRealtimeConnected(false);
        if (cancelled) return;
        const reconnectDelay = reconnectDelayRef.current;
        reconnectTimerRef.current = window.setTimeout(() => {
          void loadMessages(selectedId, "merge");
          connect();
        }, reconnectDelay);
        reconnectDelayRef.current = Math.min(reconnectDelay * 2, 10000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      setRealtimeConnected(false);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [selectedId, accessToken, isBlocked, loadConversations, loadMessages]);

  async function send() {
    if (!selectedId || !body.trim() || isBlocked) return;
    setError(null);
    const res = await api.post<{ message: ChatMessage }>(`/api/conversations/${selectedId}/messages`, { body });
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setMessages((prev) => mergeMessages(prev, [res.data.message]));
    void loadConversations(true);
    setBody("");
  }

  return (
    <div className="grid gap-4">
      <div className="form-panel rounded-2xl p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="brand-heading text-[24px] font-semibold leading-[32px]">Messages</h1>
            <p className="mt-1 text-[14px] leading-[22px] text-black/65">Real-time chat tied to bookings.</p>
            {!realtimeConnected ? (
              <p className="mt-1 text-[12px] leading-[18px] text-black/55">Realtime channel reconnecting, using low-frequency polling fallback.</p>
            ) : null}
          </div>
          <Button variant="secondary" onClick={() => void loadConversations()}>
            Refresh
          </Button>
        </div>
      </div>

      {error ? <div className="text-[14px] leading-[22px] text-danger">{error}</div> : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        <div className="overflow-hidden rounded-2xl border border-border bg-surface-2">
          <div className="border-b border-border p-3 text-[14px] font-semibold leading-[22px]">Conversations</div>
          <div className="max-h-[520px] overflow-auto">
            {conversations.length === 0 ? (
              <div className="p-3 text-[14px] leading-[22px] text-muted">No conversations</div>
            ) : (
              conversations.map((c) => {
                const name = userId === c.studentId ? c.tutorName : c.studentName;
                const isConversationBlocked = c.isBlocked ?? false;
                return (
                  <button
                    key={c.id}
                    onClick={() => setSelectedId(c.id)}
                    className={
                      selectedId === c.id
                        ? "w-full border-b border-border bg-surface px-3 py-3 text-left text-[14px] leading-[22px]"
                        : "w-full border-b border-border px-3 py-3 text-left text-[14px] leading-[22px] text-muted hover:bg-surface"
                    }
                    style={{ opacity: isConversationBlocked ? 0.5 : 1 }}
                  >
                    <div className="font-medium text-foreground">{name}</div>
                    <div className="mt-0.5 text-[12px] leading-[18px] text-muted">{new Date(c.createdAt).toLocaleString()}</div>
                    {isConversationBlocked ? (
                      <div className="mt-1 text-[12px] leading-[18px] text-red-500">Blocked</div>
                    ) : null}
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-border bg-surface-2">
          <div className="border-b border-border p-3 text-[14px] font-semibold leading-[22px]">
            {selected ? "Chat" : "Select a conversation"}
          </div>
          {isBlocked ? (
            <div className="flex h-[520px] items-center justify-center text-[14px] leading-[22px] text-muted">
              This conversation has been blocked. You cannot send messages.
            </div>
          ) : (
            <div className="flex h-[520px] flex-col">
              <div className="flex-1 overflow-auto p-3">
                {messages.length === 0 ? (
                  <div className="text-[14px] leading-[22px] text-muted">No messages yet</div>
                ) : (
                  <div className="grid gap-2">
                    {messages.map((m) => (
                      <div
                        key={m.id}
                        className={
                          m.senderUserId === userId
                            ? "ml-auto max-w-[80%] rounded-2xl bg-accent px-3 py-2 text-[14px] leading-[22px] text-white"
                            : "mr-auto max-w-[80%] rounded-2xl border border-border bg-surface px-3 py-2 text-[14px] leading-[22px]"
                        }
                      >
                        <div>{m.body}</div>
                        <div className="mt-1 text-[12px] leading-[18px] opacity-80">{formatTimeHHMMSS(m.createdAt)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="border-t border-border p-3">
                <div className="flex gap-2">
                  <input
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && void send()}
                    placeholder="Write a message"
                    className="h-10 w-full rounded-xl border border-black/12 bg-white px-3 text-[14px] leading-[22px] text-black shadow-sm focus:outline-none focus:ring-4 focus:ring-black/8 focus:border-black"
                  />
                  <Button onClick={() => void send()} disabled={!selectedId || !body.trim()}>
                    Send
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
