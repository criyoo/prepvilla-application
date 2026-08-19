"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import type { UserRole } from "@prepvilla/types";
import { useAuthStore } from "./authStore";

export function RequireAuth({ children, allow }: { children: React.ReactNode; allow?: UserRole[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const { accessToken, role, loadFromStorage, isLoaded } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    if (isLoaded && !accessToken) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (allow && role && !allow.includes(role)) {
      router.replace("/dashboard");
    }
  }, [accessToken, role, allow, router, pathname, isLoaded]);

  if (!isLoaded || !accessToken || (allow && role && !allow.includes(role))) {
    return <div className="min-h-[520px]" aria-busy="true" />;
  }

  return <>{children}</>;
}
