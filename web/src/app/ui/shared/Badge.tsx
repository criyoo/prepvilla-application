import { clsx } from "clsx";
import type { ReactNode } from "react";

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "danger" | "accent";
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[12px] font-medium leading-[18px]",
        tone === "neutral" && "border-border bg-surface text-muted",
        tone === "accent" && "border-accent/80 bg-accent text-white",
        tone === "success" && "border-success/30 bg-success/10 text-success",
        tone === "danger" && "border-danger/30 bg-danger/10 text-danger",
      )}
    >
      {children}
    </span>
  );
}
