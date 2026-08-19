"use client";

import { clsx } from "clsx";
import type { TextareaHTMLAttributes } from "react";

type Props = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  labelClassName?: string;
};

export function Textarea({ label, labelClassName, className, ...props }: Props) {
  return (
    <label className="grid gap-1">
      <div className={clsx("font-medium leading-[18px] text-black", labelClassName ?? "text-[12px]")}>{label}</div>
      <textarea
        className={clsx(
          "min-h-24 w-full resize-y rounded-xl border border-black/12 bg-white px-3 py-2 text-[14px] leading-[22px] text-black shadow-sm",
          "placeholder:text-[color:var(--form-placeholder)] focus:outline-none focus:ring-4 focus:ring-black/8 focus:border-black",
          "disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-500 disabled:opacity-100",
          className,
        )}
        {...props}
      />
    </label>
  );
}
