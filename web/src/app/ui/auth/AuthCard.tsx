"use client";

import { clsx } from "clsx";
import type { ReactNode } from "react";

export function AuthCard({ title, subtitle, children, className }: { title: string; subtitle: string; children: ReactNode; className?: string }) {
  return (
    <div className={clsx("form-panel mx-auto w-full max-w-[460px] rounded-[26px] p-6 backdrop-blur-sm", className)}>
      <h1 className="brand-heading text-[24px] font-semibold leading-[32px]">{title}</h1>
      <p className="mt-2 text-[14px] leading-[22px] text-black/65">{subtitle}</p>
      <div className={clsx("mt-6 grid gap-3")}>{children}</div>
    </div>
  );
}
