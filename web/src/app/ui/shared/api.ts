import { useAuthStore } from "./authStore";

type ApiOk<T> = { ok: true; data: T };
type ApiErr = { ok: false; error: string; status: number };

type ApiResult<T> = ApiOk<T> | ApiErr;
type RequestOptions = {
  skipAuth?: boolean;
  hasRetriedAfterRefresh?: boolean;
  hasRetriedAnonymously?: boolean;
};
type RefreshResponse = {
  accessToken: string;
  refreshToken?: string;
};

let refreshPromise: Promise<boolean> | null = null;
const PUBLIC_GET_CACHE_TTL_MS = 30_000;
const publicGetCache = new Map<string, { expiresAt: number; data: unknown }>();
const publicGetInFlight = new Map<string, Promise<ApiResult<unknown>>>();

function getBaseUrl() {
  const configuredBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8500")
    .trim()
    .replace(/\/+$/, "");

  // The AWS frontend distribution proxies /api to the ALB. Using that
  // same-origin route avoids making public pages depend on cross-origin
  // browser requests while preserving the configured API URL everywhere
  // else, including local development.
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname.toLowerCase();
    const isFrontendHost =
      (hostname === "prepvilla.info" || hostname.endsWith(".prepvilla.info")) &&
      !hostname.startsWith("api.") &&
      !hostname.startsWith("media.");

    if (window.location.protocol === "https:" && isFrontendHost) {
      return window.location.origin;
    }
  }

  return configuredBaseUrl;
}

function normalizePath(path: string) {
  return `/${path.trim().replace(/^\/+/, "")}`;
}

function isPublicTutorGet(path: string) {
  const pathname = normalizePath(path).split("?", 1)[0];
  return pathname === "/api/tutors" || /^\/api\/tutors\/[^/]+(?:\/reviews(?:\/summary)?)?$/.test(pathname);
}

function buildUrl(path: string) {
  const baseUrl = getBaseUrl();
  const normalizedPath = normalizePath(path);

  // Accept either `https://host` or `https://host/api` as the configured base URL.
  if (baseUrl.endsWith("/api") && (normalizedPath === "/api" || normalizedPath.startsWith("/api/"))) {
    return `${baseUrl}${normalizedPath.slice(4)}`;
  }

  return `${baseUrl}${normalizedPath}`;
}

function getDetailError(value: unknown): string | undefined {
  if (!value || typeof value !== "object") return undefined;
  const payload = value as Record<string, unknown>;
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  const error = payload.error;
  if (typeof error === "string") return error;
  return undefined;
}

function isInvalidTokenError(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const payload = value as Record<string, unknown>;
  return payload.code === "token_not_valid" || payload.detail === "Given token not valid for any token type";
}

function isGetRequest(init?: RequestInit) {
  return (init?.method ?? "GET").toUpperCase() === "GET";
}

function isRefreshPath(path: string) {
  const normalizedPath = normalizePath(path);
  return normalizedPath === "/api/auth/refresh" || normalizedPath === "/auth/refresh";
}

function buildHeaders(init?: RequestInit, token?: string | null) {
  const headers = new Headers(init?.headers ?? {});
  const isFormData = init?.body instanceof FormData;

  if (!isFormData) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else {
    headers.delete("Authorization");
  }

  return headers;
}

async function parseResponseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const store = useAuthStore.getState();
    const refreshToken = store.refreshToken;

    if (!refreshToken) {
      store.clear();
      return false;
    }

    let res: Response;
    try {
      res = await fetch(buildUrl("/api/auth/refresh"), {
        method: "POST",
        headers: buildHeaders({ method: "POST", body: JSON.stringify({ refreshToken }) }),
        body: JSON.stringify({ refreshToken }),
      });
    } catch {
      store.clear();
      return false;
    }

    const payload = await parseResponseBody(res);
    if (!res.ok || !payload || typeof payload !== "object") {
      store.clear();
      return false;
    }

    const nextAccessToken = (payload as RefreshResponse).accessToken;
    const nextRefreshToken = (payload as RefreshResponse).refreshToken;
    if (typeof nextAccessToken !== "string" || !nextAccessToken.trim()) {
      store.clear();
      return false;
    }

    store.updateTokens({
      accessToken: nextAccessToken,
      refreshToken: typeof nextRefreshToken === "string" ? nextRefreshToken : undefined,
    });
    return true;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

async function request<T>(path: string, init?: RequestInit, options: RequestOptions = {}): Promise<ApiResult<T>> {
  const token = options.skipAuth ? null : useAuthStore.getState().accessToken;

  let res: Response;
  try {
    res = await fetch(buildUrl(path), {
      ...init,
      headers: buildHeaders(init, token),
    });
  } catch (error) {
    const message =
      error instanceof Error && /redirect/i.test(error.message)
        ? "The API request was redirected unexpectedly. Please try again."
        : "The request could not be completed. Please check your connection and try again.";
    return { ok: false, error: message, status: 0 };
  }

  if (res.redirected) {
    return {
      ok: false,
      error: "The API request was redirected unexpectedly. Please try again.",
      status: res.status || 0,
    };
  }

  const maybeJson = await parseResponseBody(res);

  if (!res.ok) {
    if (
      res.status === 401 &&
      token &&
      !options.skipAuth &&
      !options.hasRetriedAfterRefresh &&
      !isRefreshPath(path) &&
      isInvalidTokenError(maybeJson)
    ) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        return request<T>(path, init, {
          ...options,
          hasRetriedAfterRefresh: true,
        });
      }

      if (isGetRequest(init) && !options.hasRetriedAnonymously) {
        return request<T>(path, init, {
          ...options,
          skipAuth: true,
          hasRetriedAfterRefresh: true,
          hasRetriedAnonymously: true,
        });
      }

      return {
        ok: false,
        error: "Your session has expired. Please log in again.",
        status: 401,
      };
    }

    const error = getDetailError(maybeJson) ?? `Request failed (${res.status})`;
    return { ok: false, error, status: res.status };
  }

  return { ok: true, data: maybeJson as T };
}

export const api = {
  get: <T>(path: string): Promise<ApiResult<T>> => {
    const hasSession = Boolean(useAuthStore.getState().accessToken);
    if (hasSession || !isPublicTutorGet(path)) {
      return request<T>(path);
    }

    const cached = publicGetCache.get(path);
    if (cached && cached.expiresAt > Date.now()) {
      return Promise.resolve({ ok: true, data: cached.data as T });
    }

    const inFlight = publicGetInFlight.get(path);
    if (inFlight) {
      return inFlight as Promise<ApiResult<T>>;
    }

    const nextRequest = request<T>(path)
      .then((result) => {
        if (result.ok) {
          publicGetCache.set(path, {
            expiresAt: Date.now() + PUBLIC_GET_CACHE_TTL_MS,
            data: result.data,
          });
        }
        return result;
      })
      .finally(() => {
        publicGetInFlight.delete(path);
      });

    publicGetInFlight.set(path, nextRequest as Promise<ApiResult<unknown>>);
    return nextRequest;
  },
  post: <T>(path: string, body?: unknown) => {
    if (body instanceof FormData) {
      return request<T>(path, { method: "POST", body });
    }
    return request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : "{}" });
  },
  postWithHeaders: <T>(path: string, body: unknown, headers: Record<string, string>) =>
    request<T>(path, {
      method: "POST",
      headers,
      body: body ? JSON.stringify(body) : "{}",
    }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : "{}" }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
