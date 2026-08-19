"use client";

export function resolveMediaUrl(pathOrUrl?: string | null) {
  if (!pathOrUrl) return null;
  const normalized = pathOrUrl.trim();
  if (!normalized) return null;
  if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
    return normalized;
  }
  const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8500").replace(/\/$/, "");
  return `${baseUrl}${normalized.startsWith("/") ? "" : "/"}${normalized}`;
}
