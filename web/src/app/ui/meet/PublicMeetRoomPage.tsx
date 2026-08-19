"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Copy, ExternalLink, ShieldCheck, Video } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useAuthStore } from "../shared/authStore";

type VideoRoomAccessResponse = {
  roomName: string;
  source: "booking" | "tutor_lobby" | "unmanaged";
  title: string;
  startsAt?: string | null;
  opensAt?: string | null;
  endsAt?: string | null;
  expiresAt?: string | null;
  error?: string;
};

type JitsiEventPayload = Record<string, unknown>;

type JitsiApi = {
  addListener: (event: string, listener: (payload: JitsiEventPayload) => void) => void;
  executeCommand: (command: string, ...args: unknown[]) => void;
  dispose: () => void;
};

type JitsiApiOptions = {
  roomName: string;
  width: string;
  height: string;
  parentNode: HTMLElement;
  lang?: string;
  userInfo?: {
    displayName?: string;
  };
  configOverwrite?: Record<string, unknown>;
  interfaceConfigOverwrite?: Record<string, unknown>;
};

type JitsiApiConstructor = new (domain: string, options: JitsiApiOptions) => JitsiApi;
type JitsiWindow = Window & {
  JitsiMeetExternalAPI?: JitsiApiConstructor;
};

const JITSI_TOOLBAR_BUTTONS = [
  "microphone",
  "camera",
  "desktop",
  "fullscreen",
  "chat",
  "participants-pane",
  "raisehand",
  "tileview",
  "select-background",
  "settings",
  "security",
  "closedcaptions",
  "whiteboard",
  "sharedvideo",
  "shortcuts",
  "stats",
  "videoquality",
  "filmstrip",
  "profile",
  "recording",
  "livestreaming",
  "mute-everyone",
  "mute-video-everyone",
  "toggle-camera",
  "hangup",
];

const JITSI_INTERFACE_CONFIG = {
  TILE_VIEW_MAX_COLUMNS: 4,
  MOBILE_APP_PROMO: false,
  SHOW_CHROME_EXTENSION_BANNER: false,
};

function normalizeJitsiDomain(rawValue: string | undefined) {
  const fallback = "meet.jit.si";
  const raw = (rawValue ?? fallback).trim();
  if (!raw) return fallback;

  try {
    if (raw.startsWith("http://") || raw.startsWith("https://")) {
      return new URL(raw).host;
    }
  } catch {
    return fallback;
  }

  return raw.replace(/^\/+|\/+$/g, "");
}

function decodeRoomName(value: string | null) {
  if (!value) return null;

  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function buildApiUrl(path: string) {
  const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8500").trim().replace(/\/+$/, "");
  const normalizedPath = `/${path.trim().replace(/^\/+/, "")}`;
  if (baseUrl.endsWith("/api") && (normalizedPath === "/api" || normalizedPath.startsWith("/api/"))) {
    return `${baseUrl}${normalizedPath.slice(4)}`;
  }
  return `${baseUrl}${normalizedPath}`;
}

function formatDateTime(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString();
}

function getSourceLabel(source: VideoRoomAccessResponse["source"]) {
  if (source === "booking") return "Booking room";
  if (source === "tutor_lobby") return "Tutor lobby";
  return "PrepVilla room";
}

async function copyTextToClipboard(value: string) {
  if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) {
    throw new Error("Clipboard access is not available in this browser.");
  }
  await navigator.clipboard.writeText(value);
}

async function requestRoomAccess(roomName: string) {
  try {
    const res = await fetch(buildApiUrl(`/api/video-rooms/${encodeURIComponent(roomName)}/access`), {
      cache: "no-store",
    });
    const payload = (await res.json().catch(() => null)) as VideoRoomAccessResponse | null;
    if (!res.ok) {
      return {
        ok: false as const,
        status: res.status,
        error: payload?.error ?? "This room is not available.",
        payload,
      };
    }
    if (!payload) {
      return {
        ok: false as const,
        status: res.status,
        error: "This room is not available.",
        payload: null,
      };
    }
    return { ok: true as const, status: res.status, payload };
  } catch {
    return {
      ok: false as const,
      status: 0,
      error: "The room could not be loaded. Please check your connection and try again.",
      payload: null,
    };
  }
}

export function PublicMeetRoomPage({ roomName }: { roomName?: string | null }) {
  const searchParams = useSearchParams();
  const displayName = useAuthStore((s) => s.displayName) ?? undefined;
  const jitsiDomain = useMemo(() => normalizeJitsiDomain(process.env.NEXT_PUBLIC_JITSI_DOMAIN), []);
  const jitsiScriptUrl = useMemo(() => `https://${jitsiDomain}/external_api.js`, [jitsiDomain]);
  const resolvedRoomName = useMemo(() => {
    if (roomName !== undefined) return roomName;
    return decodeRoomName(searchParams.get("roomName"));
  }, [roomName, searchParams]);

  const [roomAccess, setRoomAccess] = useState<VideoRoomAccessResponse | null>(null);
  const [isLoadingAccess, setIsLoadingAccess] = useState(true);
  const [isJitsiReady, setIsJitsiReady] = useState(false);
  const [isConferenceJoined, setIsConferenceJoined] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasExpired, setHasExpired] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const jitsiContainerRef = useRef<HTMLDivElement | null>(null);
  const jitsiApiRef = useRef<JitsiApi | null>(null);

  const getJitsiConstructor = () => (window as JitsiWindow).JitsiMeetExternalAPI;

  const handleCopyRoomLink = async () => {
    try {
      await copyTextToClipboard(window.location.href);
      setStatusMessage("PrepVilla room link copied.");
    } catch (caughtError) {
      setStatusMessage(caughtError instanceof Error ? caughtError.message : "Could not copy the room link.");
    }
  };

  useEffect(() => {
    if (!resolvedRoomName) {
      setRoomAccess(null);
      setError("This room link is incomplete.");
      setHasExpired(false);
      setIsLoadingAccess(false);
      setStatusMessage(null);
      return;
    }
    const roomNameToLoad = resolvedRoomName;

    let cancelled = false;

    async function loadRoomAccess() {
      setIsLoadingAccess(true);
      setError(null);
      setHasExpired(false);
      setStatusMessage(null);

      const result = await requestRoomAccess(roomNameToLoad);
      if (cancelled) return;

      if (result.ok) {
        setRoomAccess(result.payload);
        setError(null);
      } else {
        setRoomAccess(result.payload);
        setError(result.error);
        setHasExpired(result.status === 410);
      }

      setIsLoadingAccess(false);
    }

    void loadRoomAccess();

    return () => {
      cancelled = true;
    };
  }, [resolvedRoomName]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (getJitsiConstructor()) {
      setIsJitsiReady(true);
      return;
    }

    const existingScript = document.querySelector<HTMLScriptElement>(`script[src="${jitsiScriptUrl}"]`);
    const script = existingScript ?? document.createElement("script");

    const handleLoad = () => {
      if (getJitsiConstructor()) {
        setIsJitsiReady(true);
      } else {
        setError("The video room loaded, but the live call controls are not available.");
      }
    };

    const handleError = () => {
      setError("Could not load the video room. Refresh the page and try again.");
    };

    script.src = jitsiScriptUrl;
    script.async = true;
    script.onload = handleLoad;
    script.onerror = handleError;

    if (!existingScript) {
      document.body.appendChild(script);
    } else if (getJitsiConstructor()) {
      handleLoad();
    }

    return () => {
      script.onload = null;
      script.onerror = null;
    };
  }, [jitsiScriptUrl]);

  useEffect(() => {
    if (!roomAccess?.expiresAt || error) return;

    const expiresAt = new Date(roomAccess.expiresAt).getTime();
    if (!Number.isFinite(expiresAt)) return;

    const remainingMs = expiresAt - Date.now();
    if (remainingMs <= 0) {
      setHasExpired(true);
      setError("This room link has expired.");
      jitsiApiRef.current?.executeCommand("hangup");
      jitsiApiRef.current?.dispose();
      jitsiApiRef.current = null;
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setHasExpired(true);
      setError("This room link has expired.");
      setIsConferenceJoined(false);
      jitsiApiRef.current?.executeCommand("hangup");
      jitsiApiRef.current?.dispose();
      jitsiApiRef.current = null;
    }, remainingMs);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [error, roomAccess?.expiresAt]);

  useEffect(() => {
    const JitsiMeetExternalAPI = typeof window === "undefined" ? undefined : getJitsiConstructor();
    if (!roomAccess || error || hasExpired || !isJitsiReady || !jitsiContainerRef.current || !JitsiMeetExternalAPI) {
      return;
    }

    const apiInstance = new JitsiMeetExternalAPI(jitsiDomain, {
      roomName: roomAccess.roomName,
      width: "100%",
      height: "100%",
      parentNode: jitsiContainerRef.current,
      lang: "en",
      userInfo: {
        displayName,
      },
      configOverwrite: {
        prejoinPageEnabled: true,
        startWithAudioMuted: false,
        startWithVideoMuted: false,
        useHostPageLocalStorage: true,
        disableInviteFunctions: true,
        disableDeepLinking: true,
        hideConferenceSubject: true,
        inviteAppName: "PrepVilla",
        defaultLogoUrl: `${window.location.origin}/prepvilla-meet.svg`,
        hiddenPremeetingButtons: ["invite"],
        toolbarButtons: JITSI_TOOLBAR_BUTTONS,
      },
      interfaceConfigOverwrite: {
        ...JITSI_INTERFACE_CONFIG,
      },
    });

    jitsiApiRef.current = apiInstance;

    const handleJoined = () => {
      setIsConferenceJoined(true);
      if (displayName) {
        apiInstance.executeCommand("displayName", displayName);
      }
      apiInstance.executeCommand("localSubject", roomAccess.title);
    };

    const handleLeft = () => {
      setIsConferenceJoined(false);
    };

    apiInstance.addListener("videoConferenceJoined", handleJoined);
    apiInstance.addListener("videoConferenceLeft", handleLeft);
    apiInstance.addListener("readyToClose", () => {
      setIsConferenceJoined(false);
    });

    return () => {
      apiInstance.dispose();
      if (jitsiApiRef.current === apiInstance) {
        jitsiApiRef.current = null;
      }
    };
  }, [displayName, error, hasExpired, isJitsiReady, jitsiDomain, roomAccess]);

  const startsAtLabel = formatDateTime(roomAccess?.startsAt);
  const opensAtLabel = formatDateTime(roomAccess?.opensAt);
  const endsAtLabel = formatDateTime(roomAccess?.endsAt);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(240,100,73,0.14),transparent_24%),radial-gradient(circle_at_bottom_right,rgba(139,97,120,0.2),transparent_30%),linear-gradient(180deg,var(--primary-deep)_0%,var(--primary)_48%,rgba(139,97,120,0.92)_100%)] text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-[1800px] flex-col px-4 py-4 sm:px-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[28px] border border-white/10 bg-white/6 px-4 py-3 backdrop-blur">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/8 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/70">
              <ShieldCheck className="h-3.5 w-3.5" />
              PrepVilla Meet
            </div>
            <div className="mt-2 text-xl font-semibold text-white">{roomAccess?.title ?? "Loading room"}</div>
            <div className="mt-1 text-sm text-white/65">
              {roomAccess ? getSourceLabel(roomAccess.source) : "Resolving room access"}
              {endsAtLabel ? ` • Ends ${endsAtLabel}` : ""}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-white/70">
            {startsAtLabel ? <div>Starts {startsAtLabel}</div> : null}
            <button
              type="button"
              onClick={() => void handleCopyRoomLink()}
              className="inline-flex items-center gap-2 rounded-full border border-white/14 bg-white/8 px-4 py-2 font-semibold text-white transition hover:bg-white/12"
            >
              <Copy className="h-4 w-4" />
              Copy link
            </button>
            <Link
              href="/dashboard/video-room"
              className="inline-flex items-center gap-2 rounded-full border border-white/14 bg-white/8 px-4 py-2 font-semibold text-white transition hover:bg-white/12"
            >
              <ExternalLink className="h-4 w-4" />
              Dashboard
            </Link>
          </div>
        </div>

        {isLoadingAccess ? (
          <div className="grid flex-1 place-items-center rounded-[32px] border border-white/10 bg-black/20 p-8">
            <div className="max-w-lg text-center">
              <div className="mx-auto inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-white/8">
                <Video className="h-8 w-8 text-white" />
              </div>
              <div className="mt-6 text-3xl font-semibold">Preparing your room</div>
            </div>
          </div>
        ) : error ? (
          <div className="grid flex-1 place-items-center rounded-[32px] border border-white/10 bg-black/20 p-8">
            <div className="max-w-2xl rounded-[28px] border border-amber-300/18 bg-amber-500/10 p-6 text-center">
              <div className="text-2xl font-semibold text-white">{hasExpired ? "Room expired" : "Room unavailable"}</div>
              <div className="mt-3 text-sm leading-[24px] text-white/78">{error}</div>
              {opensAtLabel && !hasExpired ? (
                <div className="mt-3 text-sm text-white/65">This booking room opens at {opensAtLabel}.</div>
              ) : null}
              {endsAtLabel ? <div className="mt-2 text-sm text-white/65">This booking ended at {endsAtLabel}.</div> : null}
            </div>
          </div>
        ) : (
          <div className="overflow-hidden rounded-[32px] border border-white/10 bg-black/25 shadow-2xl">
            <div className="border-b border-white/10 bg-white/6">
              <div className="flex items-center justify-between px-4 py-3 text-sm text-white/70">
                <div>{isConferenceJoined ? "Connected" : isJitsiReady ? "Join the room below" : "Loading video room"}</div>
                <div>{roomAccess?.roomName}</div>
              </div>
              {statusMessage ? <div className="px-4 pb-3 text-sm text-emerald-200">{statusMessage}</div> : null}
            </div>
            <div ref={jitsiContainerRef} className="h-[calc(100vh-126px)] min-h-[640px] w-full" />
          </div>
        )}
      </div>
    </div>
  );
}
