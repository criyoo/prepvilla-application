"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  CalendarClock,
  Clock3,
  Copy,
  ExternalLink,
  Hand,
  LayoutGrid,
  Link2,
  MessageSquare,
  Mic,
  MonitorUp,
  Paintbrush,
  PhoneOff,
  PlayCircle,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users,
  Video,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Booking, UserRole } from "@prepvilla/types";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { Textarea } from "../shared/Textarea";
import { RequireAuth } from "../shared/RequireAuth";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";

type BookingRow = Booking & {
  tutorName: string;
  studentName: string;
  endsAt?: string;
  videoMeetingUrl?: string | null;
};

type BookingsResponse = {
  results: BookingRow[];
};

type TutorVideoProfile = {
  offersWebcam?: boolean;
  videoCallUrl?: string | null;
  videoMeetingUrl?: string | null;
  verificationStatus?: string;
};

type SavedRoomSource = "instant" | "scheduled";

type RoomDescriptor = {
  id: string;
  title: string;
  scheduledAt: string;
  durationMinutes: number;
  notes: string;
  createdAt: string;
  source: SavedRoomSource | "default" | "booking";
  meetingUrl: string;
  roomName: string;
  bookingId?: string;
  counterpartName?: string;
  legacyMeetingUrl?: string | null;
};

type SavedRoom = RoomDescriptor & {
  source: SavedRoomSource;
};

type JitsiEventPayload = Record<string, unknown>;

type JitsiApi = {
  addListener: (event: string, listener: (payload: JitsiEventPayload) => void) => void;
  executeCommand: (command: string, ...args: unknown[]) => void;
  dispose: () => void;
  getNumberOfParticipants: () => Promise<number>;
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

declare global {
  interface Window {
    JitsiMeetExternalAPI?: JitsiApiConstructor;
  }
}

const DEFAULT_DURATION_MINUTES = 60;
const STORAGE_KEY_PREFIX = "prepvilla.jitsi.rooms";
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
  TILE_VIEW_MAX_COLUMNS: 3,
  MOBILE_APP_PROMO: false,
  SHOW_CHROME_EXTENSION_BANNER: false,
};

function formatDateTime(iso?: string) {
  if (!iso) return "Not scheduled";
  const value = new Date(iso);
  if (Number.isNaN(value.getTime())) return "Not scheduled";
  return value.toLocaleString();
}

function toDatetimeLocalValue(value: Date) {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function createRoomId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function isWebcamBooking(booking: BookingRow) {
  return (booking.lessonType ?? "").toLowerCase().includes("webcam");
}

function getBookingDurationMinutes(booking: BookingRow) {
  if (!booking.startsAt || !booking.endsAt) {
    return DEFAULT_DURATION_MINUTES;
  }
  const start = new Date(booking.startsAt).getTime();
  const end = new Date(booking.endsAt).getTime();
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    return DEFAULT_DURATION_MINUTES;
  }
  return Math.max(15, Math.round((end - start) / 60000));
}

function getStoredRoomsKey(userId: string) {
  return `${STORAGE_KEY_PREFIX}.${userId}`;
}

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

function sanitizeRoomSegment(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function buildManagedRoomName(seed: string) {
  const normalized = sanitizeRoomSegment(seed);
  return normalized ? `prepvilla-${normalized}` : `prepvilla-room-${createRoomId().slice(0, 8)}`;
}

function buildJitsiMeetingUrl(domain: string, roomName: string) {
  return `https://${domain}/${encodeURIComponent(roomName)}`;
}

function parseJitsiRoomName(meetingUrl: string | null | undefined, domain: string) {
  if (!meetingUrl) return null;
  try {
    const parsed = new URL(meetingUrl);
    if (parsed.protocol !== "https:" || parsed.host !== domain) {
      return null;
    }
    const roomName = decodeURIComponent(parsed.pathname.replace(/^\/+/, "").trim());
    return roomName || null;
  } catch {
    return null;
  }
}

function parseStoredRooms(raw: string | null, domain: string) {
  if (!raw) return [] as SavedRoom[];

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];

    const rooms: SavedRoom[] = [];
    for (const item of parsed) {
      if (!item || typeof item !== "object") continue;
      const record = item as Record<string, unknown>;
      const source = record.source === "instant" ? "instant" : record.source === "scheduled" ? "scheduled" : null;
      const title = typeof record.title === "string" ? record.title : "";
      const scheduledAt = typeof record.scheduledAt === "string" ? record.scheduledAt : "";
      if (!source || !title || !scheduledAt || typeof record.id !== "string") {
        continue;
      }

      const durationMinutes =
        typeof record.durationMinutes === "number" && Number.isFinite(record.durationMinutes)
          ? Math.max(15, Math.round(record.durationMinutes))
          : DEFAULT_DURATION_MINUTES;

      const roomNameCandidate =
        typeof record.roomName === "string" && record.roomName.trim()
          ? record.roomName.trim()
          : parseJitsiRoomName(typeof record.meetingUrl === "string" ? record.meetingUrl : null, domain) ??
            buildManagedRoomName(`saved-${record.id}`);

      const rawMeetingUrl = typeof record.meetingUrl === "string" ? record.meetingUrl.trim() : "";
      rooms.push({
        id: record.id,
        title,
        scheduledAt,
        durationMinutes,
        notes: typeof record.notes === "string" ? record.notes : "",
        createdAt:
          typeof record.createdAt === "string" && record.createdAt
            ? record.createdAt
            : new Date().toISOString(),
        source,
        roomName: roomNameCandidate,
        meetingUrl: buildJitsiMeetingUrl(domain, roomNameCandidate),
        legacyMeetingUrl: rawMeetingUrl && !parseJitsiRoomName(rawMeetingUrl, domain) ? rawMeetingUrl : null,
      });
    }

    return rooms.sort((left, right) => new Date(left.scheduledAt).getTime() - new Date(right.scheduledAt).getTime());
  } catch {
    return [];
  }
}

function buildDashboardPath(bookingId?: string) {
  if (!bookingId) return "/dashboard/video-room";
  return `/dashboard/video-room?bookingId=${encodeURIComponent(bookingId)}`;
}

function buildMeetWrapperPath(roomName: string) {
  return `/meet?roomName=${encodeURIComponent(roomName)}`;
}

function toAbsoluteBrowserUrl(url: string) {
  if (typeof window === "undefined") return url;
  return new URL(url, window.location.origin).toString();
}

function openExternalUrl(url: string) {
  if (typeof window === "undefined") return;
  window.open(url, "_blank", "noopener,noreferrer");
}

async function copyTextToClipboard(value: string) {
  if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) {
    throw new Error("Clipboard access is not available in this browser.");
  }
  await navigator.clipboard.writeText(value);
}

function getRoomSourceLabel(source: RoomDescriptor["source"]) {
  if (source === "default") return "Tutor lobby";
  if (source === "booking") return "Booking room";
  if (source === "instant") return "Instant room";
  return "Scheduled room";
}

export function DashboardVideoRoomPage() {
  const searchParams = useSearchParams();
  const displayName = useAuthStore((s) => s.displayName) ?? "Tutor";
  const userId = useAuthStore((s) => s.userId);
  const role = useAuthStore((s) => s.role) as UserRole | null;

  const jitsiDomain = useMemo(() => normalizeJitsiDomain(process.env.NEXT_PUBLIC_JITSI_DOMAIN), []);
  const jitsiScriptUrl = useMemo(() => `https://${jitsiDomain}/external_api.js`, [jitsiDomain]);

  const [profile, setProfile] = useState<TutorVideoProfile | null>(null);
  const [bookings, setBookings] = useState<BookingRow[]>([]);
  const [savedRooms, setSavedRooms] = useState<SavedRoom[]>([]);
  const [hasLoadedSavedRooms, setHasLoadedSavedRooms] = useState(false);
  const [hasResolvedInitialRoom, setHasResolvedInitialRoom] = useState(false);

  const [meetingTitle, setMeetingTitle] = useState("");
  const [scheduledAt, setScheduledAt] = useState(() =>
    toDatetimeLocalValue(new Date(Date.now() + 60 * 60 * 1000)),
  );
  const [durationMinutes, setDurationMinutes] = useState(String(DEFAULT_DURATION_MINUTES));
  const [meetingNotes, setMeetingNotes] = useState("");

  const [selectedRoom, setSelectedRoom] = useState<RoomDescriptor | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStageOpen, setIsStageOpen] = useState(false);
  const [isJitsiReady, setIsJitsiReady] = useState(false);
  const [isConferenceJoined, setIsConferenceJoined] = useState(false);
  const [participantCount, setParticipantCount] = useState(0);
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  const [isVideoMuted, setIsVideoMuted] = useState(false);
  const [isTileView, setIsTileView] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isParticipantsPaneOpen, setIsParticipantsPaneOpen] = useState(false);
  const [isAudioOnly, setIsAudioOnly] = useState(false);
  const [isWhiteboardOpen, setIsWhiteboardOpen] = useState(false);
  const [roomSubject, setRoomSubject] = useState("");
  const [connectionMode, setConnectionMode] = useState<"p2p" | "server" | "unknown">("unknown");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const jitsiContainerRef = useRef<HTMLDivElement | null>(null);
  const jitsiApiRef = useRef<JitsiApi | null>(null);

  useEffect(() => {
    setMeetingTitle((current) => current || `${displayName} lesson room`);
  }, [displayName]);

  useEffect(() => {
    if (!userId || role !== "tutor" || typeof window === "undefined") return;
    setSavedRooms(parseStoredRooms(window.localStorage.getItem(getStoredRoomsKey(userId)), jitsiDomain));
    setHasLoadedSavedRooms(true);
  }, [jitsiDomain, role, userId]);

  useEffect(() => {
    if (!userId || !hasLoadedSavedRooms || role !== "tutor" || typeof window === "undefined") return;
    window.localStorage.setItem(getStoredRoomsKey(userId), JSON.stringify(savedRooms));
  }, [hasLoadedSavedRooms, role, savedRooms, userId]);

  const loadData = useCallback(async () => {
    if (!role) return;
    setIsLoading(true);
    setError(null);

    const bookingsRes = await api.get<BookingsResponse>("/api/bookings");
    if (bookingsRes.ok) {
      setBookings(bookingsRes.data.results ?? []);
    } else {
      setError(bookingsRes.error);
    }

    if (role === "tutor") {
      const profileRes = await api.get<TutorVideoProfile>("/api/tutors/me/profile");
      if (profileRes.ok) {
        setProfile(profileRes.data);
      } else {
        setError(profileRes.error);
      }
    } else {
      setProfile(null);
    }

    setIsLoading(false);
  }, [role]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.JitsiMeetExternalAPI) {
      setIsJitsiReady(true);
      return;
    }

    const existingScript = document.querySelector<HTMLScriptElement>(`script[src="${jitsiScriptUrl}"]`);
    const script = existingScript ?? document.createElement("script");

    const handleLoad = () => {
      if (window.JitsiMeetExternalAPI) {
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
    } else if (window.JitsiMeetExternalAPI) {
      handleLoad();
    }

    return () => {
      script.onload = null;
      script.onerror = null;
    };
  }, [jitsiScriptUrl]);

  const webcamBookings = useMemo(
    () =>
      bookings
        .filter(isWebcamBooking)
        .slice()
        .sort((left, right) => {
          const leftTime = left.startsAt ? new Date(left.startsAt).getTime() : Number.MAX_SAFE_INTEGER;
          const rightTime = right.startsAt ? new Date(right.startsAt).getTime() : Number.MAX_SAFE_INTEGER;
          return leftTime - rightTime;
        }),
    [bookings],
  );

  const bookingRooms = useMemo<RoomDescriptor[]>(
    () =>
      webcamBookings.map((booking) => {
        const scheduledAtIso =
          booking.startsAt ??
          booking.requestedStartRange?.from ??
          new Date(Date.now() + 30 * 60 * 1000).toISOString();
        const counterpartName = role === "student" ? booking.tutorName : booking.studentName;
        const jitsiRoomName =
          parseJitsiRoomName(booking.videoMeetingUrl ?? null, jitsiDomain) ?? buildManagedRoomName(`booking-${booking.id}`);

        return {
          id: booking.id,
          title: counterpartName ? `${counterpartName} lesson` : "Lesson room",
          scheduledAt: scheduledAtIso,
          durationMinutes: getBookingDurationMinutes(booking),
          notes: booking.notes ?? "",
          createdAt: booking.createdAt,
          source: "booking",
          bookingId: booking.id,
          counterpartName,
          roomName: jitsiRoomName,
          meetingUrl: buildJitsiMeetingUrl(jitsiDomain, jitsiRoomName),
          legacyMeetingUrl:
            booking.videoMeetingUrl && !parseJitsiRoomName(booking.videoMeetingUrl, jitsiDomain)
              ? booking.videoMeetingUrl
              : null,
        };
      }),
    [jitsiDomain, role, webcamBookings],
  );

  const defaultRoom = useMemo<RoomDescriptor | null>(() => {
    if (role !== "tutor" || !userId) return null;
    const jitsiRoomName =
      parseJitsiRoomName(profile?.videoMeetingUrl ?? null, jitsiDomain) ?? buildManagedRoomName(`tutor-${userId}-lobby`);

    return {
      id: "default-room",
      title: `${displayName} Lobby`,
      scheduledAt: new Date().toISOString(),
      durationMinutes: DEFAULT_DURATION_MINUTES,
      notes: "Quick drop-in room for prep calls and live lessons.",
      createdAt: new Date().toISOString(),
      source: "default",
      roomName: jitsiRoomName,
      meetingUrl: buildJitsiMeetingUrl(jitsiDomain, jitsiRoomName),
      legacyMeetingUrl:
        profile?.videoMeetingUrl && !parseJitsiRoomName(profile.videoMeetingUrl, jitsiDomain)
          ? profile.videoMeetingUrl
          : null,
    };
  }, [displayName, jitsiDomain, profile?.videoMeetingUrl, role, userId]);

  const roomCatalog = useMemo(
    () => [...(defaultRoom ? [defaultRoom] : []), ...bookingRooms, ...savedRooms],
    [bookingRooms, defaultRoom, savedRooms],
  );

  const resetLiveState = useCallback(() => {
    setIsStageOpen(false);
    setIsConferenceJoined(false);
    setParticipantCount(0);
    setIsAudioMuted(false);
    setIsVideoMuted(false);
    setIsTileView(false);
    setIsChatOpen(false);
    setIsParticipantsPaneOpen(false);
    setIsAudioOnly(false);
    setIsWhiteboardOpen(false);
    setRoomSubject("");
    setConnectionMode("unknown");
  }, []);

  const syncRoomPath = useCallback((room: RoomDescriptor | null) => {
    if (typeof window === "undefined" || !room) return;
    window.history.replaceState(null, "", buildDashboardPath(room.bookingId));
  }, []);

  const selectRoom = useCallback(
    (room: RoomDescriptor) => {
      setSelectedRoom(room);
      setStatusMessage(null);
      setError(null);
      resetLiveState();
      syncRoomPath(room);
    },
    [resetLiveState, syncRoomPath],
  );

  useEffect(() => {
    if (hasResolvedInitialRoom) return;

    const bookingId = searchParams.get("bookingId");
    if (bookingId) {
      const matchedBooking = bookingRooms.find((room) => room.bookingId === bookingId);
      if (matchedBooking) {
        selectRoom(matchedBooking);
        setHasResolvedInitialRoom(true);
        return;
      }
    }

    if (role === "student" && bookingRooms.length > 0) {
      selectRoom(bookingRooms[0]);
      setHasResolvedInitialRoom(true);
      return;
    }

    if (role === "tutor" && defaultRoom) {
      selectRoom(defaultRoom);
      setHasResolvedInitialRoom(true);
      return;
    }

    if (savedRooms.length > 0) {
      selectRoom(savedRooms[0]);
      setHasResolvedInitialRoom(true);
    }
  }, [bookingRooms, defaultRoom, hasResolvedInitialRoom, role, savedRooms, searchParams, selectRoom]);

  useEffect(() => {
    if (!selectedRoom) return;
    const nextRoom = roomCatalog.find((room) => room.id === selectedRoom.id);
    if (!nextRoom) return;
    if (
      nextRoom.title === selectedRoom.title &&
      nextRoom.scheduledAt === selectedRoom.scheduledAt &&
      nextRoom.durationMinutes === selectedRoom.durationMinutes &&
      nextRoom.notes === selectedRoom.notes &&
      nextRoom.meetingUrl === selectedRoom.meetingUrl &&
      (nextRoom.legacyMeetingUrl ?? "") === (selectedRoom.legacyMeetingUrl ?? "")
    ) {
      return;
    }
    setSelectedRoom(nextRoom);
  }, [roomCatalog, selectedRoom]);

  async function copyMeetingLink(url?: string | null) {
    if (!url) {
      setError("Select a room before copying its link.");
      return;
    }
    try {
      await copyTextToClipboard(toAbsoluteBrowserUrl(url));
      setStatusMessage("PrepVilla room link copied.");
      setError(null);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not copy the room link.");
    }
  }

  const upsertSavedRoom = useCallback((room: SavedRoom) => {
    setSavedRooms((current) =>
      [...current.filter((item) => item.id !== room.id), room].sort(
        (left, right) => new Date(left.scheduledAt).getTime() - new Date(right.scheduledAt).getTime(),
      ),
    );
  }, []);

  const removeSavedRoom = useCallback(
    (roomId: string) => {
      setSavedRooms((current) => current.filter((room) => room.id !== roomId));
      setSelectedRoom((current) => {
        if (!current || current.id !== roomId) return current;
        return defaultRoom ?? bookingRooms[0] ?? null;
      });
      resetLiveState();
    },
    [bookingRooms, defaultRoom, resetLiveState],
  );

  const createStandaloneRoom = useCallback(
    (source: SavedRoomSource, openImmediately: boolean) => {
      setError(null);
      setStatusMessage(null);

      const title = meetingTitle.trim() || `${displayName} lesson room`;
      const parsedDuration = Number(durationMinutes);
      const startsAt = source === "instant" ? new Date() : new Date(scheduledAt);

      if (Number.isNaN(startsAt.getTime())) {
        setError("Choose a valid date and time.");
        return;
      }
      if (source === "scheduled" && startsAt.getTime() <= Date.now()) {
        setError("Scheduled rooms must start in the future.");
        return;
      }
      if (!Number.isFinite(parsedDuration) || parsedDuration < 15) {
        setError("Duration must be at least 15 minutes.");
        return;
      }

      const roomId = createRoomId();
      const roomName = buildManagedRoomName(`${title}-${roomId.slice(0, 8)}`);
      const room: SavedRoom = {
        id: roomId,
        title,
        scheduledAt: startsAt.toISOString(),
        durationMinutes: Math.round(parsedDuration),
        notes: meetingNotes.trim(),
        createdAt: new Date().toISOString(),
        source,
        roomName,
        meetingUrl: buildJitsiMeetingUrl(jitsiDomain, roomName),
        legacyMeetingUrl: null,
      };

      upsertSavedRoom(room);
      selectRoom(room);
      setStatusMessage(source === "instant" ? "Instant room created." : "Scheduled room created.");
      if (openImmediately) {
        setIsStageOpen(true);
      }
    },
    [
      displayName,
      durationMinutes,
      jitsiDomain,
      meetingNotes,
      meetingTitle,
      scheduledAt,
      selectRoom,
      upsertSavedRoom,
    ],
  );

  const selectedMeetingUrl = selectedRoom?.meetingUrl ?? "";
  const selectedWrapperUrl = selectedRoom ? buildMeetWrapperPath(selectedRoom.roomName) : "";
  const selectedLegacyUrl = selectedRoom?.legacyMeetingUrl ?? "";
  const canCreateStandaloneRooms = role === "tutor";

  const selectedRoomStatus = selectedRoom
    ? isConferenceJoined && isStageOpen
      ? "In call"
      : selectedRoom.source === "scheduled"
        ? "Scheduled"
        : "Ready"
    : "Pick a room";

  const joinSelectedRoom = useCallback(() => {
    if (!selectedRoom) {
      setError("Select a room before joining.");
      return;
    }
    if (!isJitsiReady) {
      setError("The video room is still loading. Try again in a moment.");
      return;
    }
    setError(null);
    setStatusMessage(`Opening ${selectedRoom.title}.`);
    setIsStageOpen(true);
  }, [isJitsiReady, selectedRoom]);

  const syncParticipantCount = useCallback(async (apiInstance: JitsiApi) => {
    try {
      const count = await apiInstance.getNumberOfParticipants();
      setParticipantCount(count);
    } catch {
      setParticipantCount((current) => current || 1);
    }
  }, []);

  useEffect(() => {
    if (!isStageOpen || !selectedRoom || !isJitsiReady || !jitsiContainerRef.current || !window.JitsiMeetExternalAPI) {
      return;
    }

    const apiInstance = new window.JitsiMeetExternalAPI(jitsiDomain, {
      roomName: selectedRoom.roomName,
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
        enableNoAudioDetection: true,
        enableNoisyMicDetection: true,
        useHostPageLocalStorage: true,
        disableInviteFunctions: true,
        disableDeepLinking: true,
        disableModeratorIndicator: false,
        hideConferenceSubject: true,
        inviteAppName: "PrepVilla",
        defaultLogoUrl: `${window.location.origin}/prepvilla-meet.svg`,
        hiddenPremeetingButtons: ["invite"],
        toolbarButtons: JITSI_TOOLBAR_BUTTONS,
        lobby: {
          autoKnock: true,
          enableChat: true,
        },
        securityUi: {
          hideLobbyButton: false,
          disableLobbyPassword: false,
        },
        breakoutRooms: {
          hideAddRoomButton: false,
          hideAutoAssignButton: false,
          hideJoinRoomButton: false,
          hideMoreActionsButton: false,
          hideMuteAllButton: false,
        },
        speakerStats: {
          disabled: false,
          disableSearch: false,
          order: ["role", "name"],
        },
        filmstrip: {
          disableResizable: false,
          disableStageFilmstrip: false,
        },
      },
      interfaceConfigOverwrite: {
        ...JITSI_INTERFACE_CONFIG,
      },
    });

    jitsiApiRef.current = apiInstance;

    const handleVideoConferenceJoined = () => {
      setIsConferenceJoined(true);
      setStatusMessage(`You joined ${selectedRoom.title}.`);
      void syncParticipantCount(apiInstance);
      apiInstance.executeCommand("displayName", displayName);
      apiInstance.executeCommand("localSubject", selectedRoom.title);
    };

    const handleVideoConferenceLeft = () => {
      setIsConferenceJoined(false);
      setParticipantCount(0);
    };

    const handleParticipantJoined = () => {
      void syncParticipantCount(apiInstance);
    };

    const handleParticipantLeft = () => {
      void syncParticipantCount(apiInstance);
    };

    apiInstance.addListener("videoConferenceJoined", handleVideoConferenceJoined);
    apiInstance.addListener("videoConferenceLeft", handleVideoConferenceLeft);
    apiInstance.addListener("participantJoined", handleParticipantJoined);
    apiInstance.addListener("participantLeft", handleParticipantLeft);
    apiInstance.addListener("audioMuteStatusChanged", (payload) => {
      setIsAudioMuted(payload.muted === true);
    });
    apiInstance.addListener("videoMuteStatusChanged", (payload) => {
      setIsVideoMuted(payload.muted === true);
    });
    apiInstance.addListener("tileViewChanged", (payload) => {
      setIsTileView(payload.enabled === true);
    });
    apiInstance.addListener("chatUpdated", (payload) => {
      setIsChatOpen(payload.isOpen === true);
    });
    apiInstance.addListener("participantsPaneToggled", (payload) => {
      setIsParticipantsPaneOpen(payload.open === true);
    });
    apiInstance.addListener("audioOnlyChanged", (payload) => {
      setIsAudioOnly(payload.audioOnlyChanged === true);
    });
    apiInstance.addListener("whiteboardStatusChanged", (payload) => {
      setIsWhiteboardOpen(typeof payload.status === "string" && payload.status !== "closed");
    });
    apiInstance.addListener("subjectChange", (payload) => {
      setRoomSubject(typeof payload.subject === "string" ? payload.subject : "");
    });
    apiInstance.addListener("p2pStatusChanged", (payload) => {
      setConnectionMode(payload.isP2p === true ? "p2p" : payload.isP2p === false ? "server" : "unknown");
    });
    apiInstance.addListener("readyToClose", () => {
      resetLiveState();
      setStatusMessage("Call ended.");
    });

    return () => {
      apiInstance.dispose();
      if (jitsiApiRef.current === apiInstance) {
        jitsiApiRef.current = null;
      }
    };
  }, [displayName, isJitsiReady, isStageOpen, jitsiDomain, resetLiveState, selectedRoom, syncParticipantCount]);

  const runJitsiCommand = useCallback((command: string, ...args: unknown[]) => {
    if (!jitsiApiRef.current) {
      setError("Join the room before using live controls.");
      return;
    }
    setError(null);
    jitsiApiRef.current.executeCommand(command, ...args);
  }, []);

  return (
    <RequireAuth allow={["tutor", "student"]}>
      <div className="grid gap-6">
        <div className="overflow-hidden rounded-[32px] border border-border bg-[radial-gradient(circle_at_top_left,rgba(240,100,73,0.14),transparent_34%),radial-gradient(circle_at_top_right,rgba(139,97,120,0.16),transparent_28%),linear-gradient(135deg,rgba(255,255,255,0.98)_0%,rgba(247,241,232,0.94)_100%)] p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-accent">
                <Sparkles className="h-3.5 w-3.5" />
                Video room
              </div>
              <h1 className="brand-heading mt-4 text-[28px] font-semibold leading-[34px]">
                Video rooms for live lessons
              </h1>
              <p className="mt-2 text-[14px] leading-[22px] text-muted">
                Webcam, mic, chat, screen share, whiteboard, captions, reactions, lobby, breakout rooms are included.
              </p>
            </div>
            <div className="grid min-w-[240px] gap-2 rounded-[28px] border border-primary-soft bg-white/80 p-4 backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Room status</div>
              <div className="text-lg font-semibold text-foreground">{selectedRoomStatus}</div>
              <div className="text-sm text-muted">
                {selectedRoom ? `${selectedRoom.title} • ${selectedRoom.durationMinutes} min` : "Pick a room to start."}
              </div>
              <div className="inline-flex w-fit items-center gap-2 rounded-full border border-border bg-surface-2 px-3 py-1 text-xs font-medium text-muted">
                <ShieldCheck className="h-3.5 w-3.5 text-accent" />
                {isJitsiReady ? "Video Room ready" : "Loading Video Room"}
              </div>
            </div>
          </div>
        </div>

        {role === "tutor" && !profile?.offersWebcam ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-[14px] leading-[22px] text-amber-900">
            Webcam lessons are off on{" "}
            <Link href="/dashboard/profile" className="font-semibold underline">
              your profile
            </Link>
            .
          </div>
        ) : null}

        {error ? (
          <div className="rounded-2xl border border-danger/20 bg-danger/5 px-4 py-3 text-[14px] leading-[22px] text-danger">
            {error}
          </div>
        ) : null}
        {statusMessage ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-[14px] leading-[22px] text-emerald-700">
            {statusMessage}
          </div>
        ) : null}

        <div className="grid gap-6">
          <div className="grid gap-6">
            {canCreateStandaloneRooms ? (
              <div className="rounded-[30px] border border-border bg-surface-2 p-5 shadow-sm">
                <div className="flex items-center gap-2 text-[18px] font-semibold leading-[26px]">
                  <Plus className="h-5 w-5 text-accent" />
                  Create room
                </div>
                <div className="mt-4 grid gap-4">
                  <Input
                    label="Room title"
                    value={meetingTitle}
                    onChange={(event) => setMeetingTitle(event.target.value)}
                    placeholder="Private mathematics session"
                  />
                  <Input
                    label="Scheduled date and time"
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(event) => setScheduledAt(event.target.value)}
                  />
                  <Input
                    label="Duration (minutes)"
                    type="number"
                    min="15"
                    step="15"
                    value={durationMinutes}
                    onChange={(event) => setDurationMinutes(event.target.value)}
                  />
                  <Textarea
                    label="Notes"
                    value={meetingNotes}
                    onChange={(event) => setMeetingNotes(event.target.value)}
                    placeholder="Optional lesson notes."
                  />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button onClick={() => createStandaloneRoom("scheduled", false)}>
                    <CalendarClock className="h-4 w-4" />
                    Save room
                  </Button>
                  <Button variant="secondary" onClick={() => createStandaloneRoom("instant", true)}>
                    <PlayCircle className="h-4 w-4" />
                    Start now
                  </Button>
                </div>
              </div>
            ) : null}

            <div className="overflow-hidden rounded-[34px] border border-primary-soft bg-[linear-gradient(160deg,var(--primary-deep)_0%,var(--primary)_58%,var(--secondary-color)_82%,var(--accent)_100%)] p-5 text-white shadow-2xl">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/8 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-white/70">
                    <Video className="h-3.5 w-3.5" />
                    Live stage
                  </div>
                  <div className="mt-3 text-2xl font-semibold">{selectedRoom?.title ?? "No room selected"}</div>
                  <div className="mt-1 text-sm text-white/70">
                    {selectedRoom
                      ? `${formatDateTime(selectedRoom.scheduledAt)} • ${selectedRoom.durationMinutes} min`
                      : "Select a room from the left panel."}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => selectedWrapperUrl && openExternalUrl(selectedWrapperUrl)} disabled={!selectedWrapperUrl}>
                    <ExternalLink className="h-4 w-4" />
                    Pop out
                  </Button>
                  <Button variant="secondary" onClick={() => void copyMeetingLink(selectedWrapperUrl)} disabled={!selectedWrapperUrl}>
                    <Copy className="h-4 w-4" />
                    Copy link
                  </Button>
                  <Button onClick={joinSelectedRoom} disabled={!selectedRoom || !isJitsiReady}>
                    <Video className="h-4 w-4" />
                    {isStageOpen ? "Rejoin" : "Join room"}
                  </Button>
                </div>
              </div>

              <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
                <div className="rounded-[28px] border border-white/10 bg-black/25 p-3">
                  <div className="mb-3 flex flex-wrap gap-2">
                    <Button variant="secondary" size="sm" onClick={() => runJitsiCommand("toggleAudio")} disabled={!isConferenceJoined}>
                      <Mic className="h-2.0 w-2.5" />
                      {isAudioMuted ? "Unmute" : "Mute"}
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => runJitsiCommand("toggleVideo")} disabled={!isConferenceJoined}>
                      <Video className="h-2.0 w-2.5" />
                      {isVideoMuted ? "Start camera" : "Stop camera"}
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => runJitsiCommand("toggleShareScreen")} disabled={!isConferenceJoined}>
                      <MonitorUp className="h-2.0 w-2.5" />
                      Share screen
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => runJitsiCommand("toggleChat")} disabled={!isConferenceJoined}>
                      <MessageSquare className="h-2.0 w-2.5" />
                      {isChatOpen ? "Hide chat" : "Open chat"}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => runJitsiCommand("toggleParticipantsPane", !isParticipantsPaneOpen)}
                      disabled={!isConferenceJoined}
                    >
                      <Users className="h-2.0 w-2.5" />
                      {isParticipantsPaneOpen ? "Hide people" : "Show people"}
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => runJitsiCommand("toggleTileView")} disabled={!isConferenceJoined}>
                      <LayoutGrid className="h-2.0 w-2.5" />
                      {isTileView ? "Stage view" : "Tile view"}
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => runJitsiCommand("toggleRaiseHand")} disabled={!isConferenceJoined}>
                      <Hand className="h-2.0 w-2.5" />
                      Raise hand
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => runJitsiCommand("toggleSubtitles")} disabled={!isConferenceJoined}>
                      <MessageSquare className="h-2.0 w-2.5" />
                      Captions
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => runJitsiCommand("toggleWhiteboard")}
                      disabled={!isConferenceJoined}
                    >
                      <Link2 className="h-2.0 w-2.5" />
                      {isWhiteboardOpen ? "Hide board" : "Whiteboard"}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => runJitsiCommand("toggleVirtualBackgroundDialog")}
                      disabled={!isConferenceJoined}
                    >
                      <Paintbrush className="h-2.0 w-2.5" />
                      Background
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => runJitsiCommand("setAudioOnly", !isAudioOnly)} disabled={!isConferenceJoined}>
                      <Mic className="h-2.0 w-2.5" />
                      {isAudioOnly ? "Exit audio only" : "Audio only"}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => runJitsiCommand("hangup")} disabled={!isConferenceJoined}>
                      <PhoneOff className="h-2.0 w-2.5" />
                      Leave
                    </Button>
                  </div>

                  {isStageOpen ? (
                    <div className="overflow-hidden rounded-[24px] border border-white/10 bg-black/35">
                      <div ref={jitsiContainerRef} className="h-[680px] w-full min-w-0" />
                    </div>
                  ) : (
                    <div className="grid min-h-[680px] place-items-center rounded-[24px] border border-dashed border-white/14 bg-[radial-gradient(circle_at_top,rgba(240,100,73,0.16),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(139,97,120,0.18),transparent_34%),rgba(255,255,255,0.03)] p-8 text-center">
                      <div className="max-w-xl">
                        <div className="mx-auto inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-white/8">
                          <Video className="h-8 w-8 text-white" />
                        </div>
                        <div className="mt-6 text-3xl font-semibold">
                          {selectedRoom ? `Join ${selectedRoom.title}` : "Select a room"}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="grid gap-4">
                  <div className="rounded-[28px] border border-white/10 bg-white/6 p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-white/60">Live status</div>
                    <div className="mt-2 text-base font-semibold text-white">{selectedRoomStatus}</div>
                    <div className="mt-4 grid gap-3 text-sm text-white/75">
                      <div className="flex items-center justify-between gap-3">
                        <span className="inline-flex items-center gap-2">
                          <Users className="h-4 w-4" />
                          Participants
                        </span>
                        <span>{participantCount || 0}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="inline-flex items-center gap-2">
                          <Clock3 className="h-4 w-4" />
                          Connection
                        </span>
                        <span>{connectionMode === "p2p" ? "Peer to peer" : connectionMode === "server" ? "Server relay" : "Standby"}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="inline-flex items-center gap-2">
                          <LayoutGrid className="h-4 w-4" />
                          Layout
                        </span>
                        <span>{isTileView ? "Tile" : "Stage"}</span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-[28px] border border-white/10 bg-white/6 p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-white/60">Room details</div>
                    <div className="mt-3 text-lg font-semibold text-white">{selectedRoom?.title ?? "No room selected"}</div>
                    <div className="mt-1 text-sm text-white/70">
                      {selectedRoom ? formatDateTime(selectedRoom.scheduledAt) : "Pick a room from the list."}
                    </div>
                    <div className="mt-3 inline-flex rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs font-medium text-white/70">
                      {selectedRoom ? getRoomSourceLabel(selectedRoom.source) : "Room"}
                    </div>
                    {selectedRoom?.counterpartName ? (
                      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-3">
                        <div className="text-xs font-semibold uppercase tracking-[0.16em] text-white/55">Counterpart</div>
                        <div className="mt-2 text-base font-semibold text-white">{selectedRoom.counterpartName}</div>
                      </div>
                    ) : null}
                    {roomSubject ? (
                      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-3">
                        <div className="text-xs font-semibold uppercase tracking-[0.16em] text-white/55">Live subject</div>
                        <div className="mt-2 text-sm text-white">{roomSubject}</div>
                      </div>
                    ) : null}
                    {selectedRoom?.notes ? (
                      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-3 text-sm leading-[22px] text-white/78">
                        {selectedRoom.notes}
                      </div>
                    ) : null}
                  </div>

                  {selectedLegacyUrl ? (
                    <div className="rounded-[28px] border border-amber-300/25 bg-amber-500/10 p-4">
                      <div className="text-sm font-semibold text-white">Legacy room link detected</div>
                      <div className="mt-2 text-sm leading-[22px] text-white/70">
                        This booking also has an older external meeting link saved. The PrepVilla room opens by default now.
                      </div>
                      <div className="mt-3">
                        <Button variant="secondary" size="sm" onClick={() => openExternalUrl(selectedLegacyUrl)}>
                          <ExternalLink className="h-3.5 w-3.5" />
                          Open legacy link
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            {/* <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
              <div className="rounded-[30px] border border-border bg-surface-2 p-5 shadow-sm">
                <div className="flex items-center gap-2 text-[18px] font-semibold leading-[26px]">
                  <Link2 className="h-5 w-5 text-accent" />
                  Share link
                </div>
                <div className="mt-4">
                  <Input value={selectedWrapperUrl} readOnly placeholder="Select a room to get its PrepVilla link" />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => void copyMeetingLink(selectedWrapperUrl)} disabled={!selectedWrapperUrl}>
                    <Copy className="h-4 w-4" />
                    Copy link
                  </Button>
                  <Button variant="secondary" onClick={() => selectedWrapperUrl && openExternalUrl(selectedWrapperUrl)} disabled={!selectedWrapperUrl}>
                    <ExternalLink className="h-4 w-4" />
                    Open link
                  </Button>
                </div>
              </div>

              <div className="rounded-[30px] border border-border bg-surface-2 p-5 shadow-sm">
                <div className="flex items-center gap-2 text-[18px] font-semibold leading-[26px]">
                  <ShieldCheck className="h-5 w-5 text-accent" />
                  Included features
                </div>
                <div className="mt-4 flex flex-wrap gap-2 text-sm text-foreground">
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Mic & camera</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Screen share</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Chat</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Tile view</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Virtual backgrounds</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Whiteboard</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Captions</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Lobby & security</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Breakout rooms</span>
                  <span className="rounded-full border border-border bg-surface px-3 py-1">Stats & shortcuts</span>
                </div>
              </div>
            </div> */}
          </div>
        </div>
      </div>
    </RequireAuth>
  );
}
