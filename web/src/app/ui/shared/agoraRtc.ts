"use client";

const AGORA_SDK_URL =
  process.env.NEXT_PUBLIC_AGORA_SDK_URL ?? "https://download.agora.io/sdk/release/AgoraRTC_N-4.21.0.js";

export type AgoraUid = string | number;
export type AgoraMediaType = "audio" | "video";

export type AgoraTrack = {
  stop: () => void;
  close?: () => void;
  play: (element?: string | HTMLElement) => void;
};

export type AgoraLocalTrack = AgoraTrack & {
  setEnabled: (enabled: boolean) => Promise<void>;
};

export type AgoraLocalAudioTrack = AgoraLocalTrack;
export type AgoraLocalVideoTrack = AgoraLocalTrack;

export type AgoraRemoteAudioTrack = AgoraTrack;
export type AgoraRemoteVideoTrack = AgoraTrack;

export type AgoraRemoteUser = {
  uid: AgoraUid;
  hasAudio: boolean;
  hasVideo: boolean;
  audioTrack?: AgoraRemoteAudioTrack | null;
  videoTrack?: AgoraRemoteVideoTrack | null;
};

export type AgoraConnectionState =
  | "DISCONNECTED"
  | "CONNECTING"
  | "CONNECTED"
  | "RECONNECTING"
  | "DISCONNECTING";

export type AgoraRTCClient = {
  remoteUsers: AgoraRemoteUser[];
  join: (appId: string, channel: string, token: string | null, uid?: AgoraUid | null) => Promise<AgoraUid>;
  leave: () => Promise<void>;
  publish: (tracks: AgoraLocalTrack[]) => Promise<void>;
  unpublish: (tracks: AgoraLocalTrack[]) => Promise<void>;
  subscribe: (user: AgoraRemoteUser, mediaType: AgoraMediaType) => Promise<void>;
  on: (
    event:
      | "user-published"
      | "user-unpublished"
      | "user-left"
      | "connection-state-change",
    listener: (...args: unknown[]) => void,
  ) => void;
  removeAllListeners: () => void;
};

export type AgoraRTCStatic = {
  createClient: (config: { mode: "rtc"; codec: "vp8" | "h264" }) => AgoraRTCClient;
  createMicrophoneAudioTrack: () => Promise<AgoraLocalAudioTrack>;
  createCameraVideoTrack: () => Promise<AgoraLocalVideoTrack>;
};

declare global {
  interface Window {
    AgoraRTC?: AgoraRTCStatic;
  }
}

let agoraLoaderPromise: Promise<AgoraRTCStatic> | null = null;

export function loadAgoraRtcSdk() {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Agora RTC can only load in the browser."));
  }
  if (window.AgoraRTC) {
    return Promise.resolve(window.AgoraRTC);
  }
  if (agoraLoaderPromise) {
    return agoraLoaderPromise;
  }

  agoraLoaderPromise = new Promise<AgoraRTCStatic>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-agora-sdk="true"]');
    if (existing) {
      existing.addEventListener("load", () => {
        if (window.AgoraRTC) {
          resolve(window.AgoraRTC);
          return;
        }
        reject(new Error("Agora RTC SDK loaded without exposing the global client."));
      });
      existing.addEventListener("error", () => reject(new Error("Failed to load Agora RTC SDK.")));
      return;
    }

    const script = document.createElement("script");
    script.src = AGORA_SDK_URL;
    script.async = true;
    script.dataset.agoraSdk = "true";
    script.onload = () => {
      if (window.AgoraRTC) {
        resolve(window.AgoraRTC);
        return;
      }
      reject(new Error("Agora RTC SDK loaded without exposing the global client."));
    };
    script.onerror = () => reject(new Error("Failed to load Agora RTC SDK."));
    document.head.appendChild(script);
  }).catch((error) => {
    agoraLoaderPromise = null;
    throw error;
  });

  return agoraLoaderPromise;
}
