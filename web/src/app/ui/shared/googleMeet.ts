"use client";

export const GOOGLE_MEET_CREATE_SCOPE = "https://www.googleapis.com/auth/meetings.space.created";

type GoogleTokenResponse = {
  access_token?: string;
  expires_in?: number;
  scope?: string;
  error?: string;
  error_description?: string;
};

type GoogleTokenClient = {
  requestAccessToken: (override?: { prompt?: string }) => void;
};

type GoogleCodeResponse = {
  code?: string;
  error?: string;
  error_description?: string;
};

type GoogleCodeClient = {
  requestCode: () => void;
};

type GoogleIdentity = {
  accounts: {
    oauth2: {
      initTokenClient: (config: {
        client_id: string;
        scope: string;
        callback: (response: GoogleTokenResponse) => void;
        error_callback?: (error: { type?: string }) => void;
      }) => GoogleTokenClient;
      initCodeClient: (config: {
        client_id: string;
        scope: string;
        ux_mode: "popup";
        prompt?: string;
        callback: (response: GoogleCodeResponse) => void;
        error_callback?: (error: { type?: string }) => void;
      }) => GoogleCodeClient;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleIdentity;
  }
}

let googleIdentityPromise: Promise<GoogleIdentity> | null = null;

function loadGoogleIdentity() {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Google Meet can only be authorized in the browser."));
  }
  if (window.google?.accounts?.oauth2) {
    return Promise.resolve(window.google);
  }
  if (googleIdentityPromise) {
    return googleIdentityPromise;
  }

  googleIdentityPromise = new Promise<GoogleIdentity>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-google-identity="true"]');
    if (existing) {
      existing.addEventListener("load", () => {
        if (window.google?.accounts?.oauth2) {
          resolve(window.google);
          return;
        }
        reject(new Error("Google Identity Services loaded without the OAuth client."));
      });
      existing.addEventListener("error", () => reject(new Error("Failed to load Google Identity Services.")));
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.dataset.googleIdentity = "true";
    script.onload = () => {
      if (window.google?.accounts?.oauth2) {
        resolve(window.google);
        return;
      }
      reject(new Error("Google Identity Services loaded without the OAuth client."));
    };
    script.onerror = () => reject(new Error("Failed to load Google Identity Services."));
    document.head.appendChild(script);
  }).catch((error) => {
    googleIdentityPromise = null;
    throw error;
  });

  return googleIdentityPromise;
}

export async function requestGoogleAccessToken({
  clientId,
  scope = GOOGLE_MEET_CREATE_SCOPE,
  prompt = "consent",
}: {
  clientId: string;
  scope?: string;
  prompt?: string;
}) {
  const google = await loadGoogleIdentity();

  return new Promise<{ accessToken: string; expiresIn: number; scope: string }>((resolve, reject) => {
    const tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope,
      callback: (response) => {
        if (response.error) {
          reject(
            new Error(
              response.error_description ||
                response.error ||
                "Google Meet authorization could not be completed.",
            ),
          );
          return;
        }
        if (!response.access_token) {
          reject(new Error("Google Meet authorization did not return an access token."));
          return;
        }
        resolve({
          accessToken: response.access_token,
          expiresIn: response.expires_in ?? 0,
          scope: response.scope ?? scope,
        });
      },
      error_callback: () => {
        reject(new Error("Google Meet authorization was cancelled or blocked."));
      },
    });
    tokenClient.requestAccessToken({ prompt });
  });
}

export async function requestGoogleAuthorizationCode(clientId: string) {
  const google = await loadGoogleIdentity();

  return new Promise<string>((resolve, reject) => {
    const codeClient = google.accounts.oauth2.initCodeClient({
      client_id: clientId,
      scope: "openid email profile",
      ux_mode: "popup",
      prompt: "consent select_account",
      callback: (response) => {
        if (response.error) {
          reject(new Error(response.error_description || response.error));
          return;
        }
        if (!response.code) {
          reject(new Error("Google authentication did not return an authorization code."));
          return;
        }
        resolve(response.code);
      },
      error_callback: () => {
        reject(new Error("Google authentication was cancelled or blocked."));
      },
    });
    codeClient.requestCode();
  });
}

export async function createGoogleMeetSpace(accessToken: string) {
  const response = await fetch("https://meet.googleapis.com/v2/spaces", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: "{}",
  });

  const text = await response.text();
  let payload: Record<string, unknown> = {};
  if (text) {
    try {
      payload = JSON.parse(text) as Record<string, unknown>;
    } catch {
      payload = {};
    }
  }
  if (!response.ok) {
    const errorPayload =
      payload && typeof payload.error === "object" && payload.error
        ? (payload.error as Record<string, unknown>)
        : null;
    const message =
      (typeof errorPayload?.message === "string" && errorPayload.message) ||
      (typeof payload.error === "string" && payload.error) ||
      `Google Meet request failed (${response.status}).`;
    throw new Error(message);
  }

  const meetingUri = typeof payload.meetingUri === "string" ? payload.meetingUri : "";
  const spaceName = typeof payload.name === "string" ? payload.name : "";
  if (!meetingUri) {
    throw new Error("Google Meet returned a space without a meeting URL.");
  }
  return {
    meetingUri,
    spaceName,
  };
}
