import { create } from "zustand";
import type { UserRole } from "@prepvilla/types";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  role: UserRole | null;
  displayName: string | null;
  isLoaded: boolean;
  setSession: (s: {
    accessToken: string;
    refreshToken: string;
    userId: string;
    role: UserRole;
    displayName: string;
  }) => void;
  updateTokens: (tokens: {
    accessToken: string;
    refreshToken?: string | null;
  }) => void;
  clear: () => void;
  loadFromStorage: () => void;
  updateProfile: (p: { displayName?: string }) => void;
};

const storageKey = "prepvilla.session";

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  userId: null,
  role: null,
  displayName: null,
  isLoaded: false,
  setSession: (s) => {
    set({
      accessToken: s.accessToken,
      refreshToken: s.refreshToken,
      userId: s.userId,
      role: s.role,
      displayName: s.displayName,
      isLoaded: true,
    });
    if (typeof window !== "undefined") {
      window.localStorage.setItem(storageKey, JSON.stringify(s));
    }
  },
  updateTokens: ({ accessToken, refreshToken }) => {
    const prev = get();
    const nextRefreshToken = refreshToken ?? prev.refreshToken;
    set({
      accessToken,
      refreshToken: nextRefreshToken,
    });
    if (typeof window !== "undefined") {
      if (nextRefreshToken && prev.userId && prev.role && prev.displayName) {
        window.localStorage.setItem(
          storageKey,
          JSON.stringify({
            accessToken,
            refreshToken: nextRefreshToken,
            userId: prev.userId,
            role: prev.role,
            displayName: prev.displayName,
          }),
        );
      } else {
        window.localStorage.removeItem(storageKey);
      }
    }
  },
  clear: () => {
    set({ accessToken: null, refreshToken: null, userId: null, role: null, displayName: null, isLoaded: true });
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(storageKey);
    }
  },
  loadFromStorage: () => {
    if (typeof window === "undefined") return;
    if (get().isLoaded) return;
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      set({ isLoaded: true });
      return;
    }
    try {
      const parsed = JSON.parse(raw) as {
        accessToken: string;
        refreshToken: string;
        userId: string;
        role: UserRole;
        displayName: string;
      };
      get().setSession(parsed);
      set({ isLoaded: true });
    } catch {
      window.localStorage.removeItem(storageKey);
      set({ isLoaded: true });
    }
  },
  updateProfile: (p) => {
    const prev = get();
    const next = {
      accessToken: prev.accessToken,
      refreshToken: prev.refreshToken,
      userId: prev.userId,
      role: prev.role,
      displayName: p.displayName ?? prev.displayName,
    };
    set({ displayName: next.displayName });
    if (typeof window !== "undefined" && next.accessToken && next.refreshToken && next.userId && next.role && next.displayName) {
      window.localStorage.setItem(storageKey, JSON.stringify(next));
    }
  },
}));
