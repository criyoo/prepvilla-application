"use client";

import { clsx } from "clsx";
import type { SelectHTMLAttributes } from "react";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  labelClassName?: string;
  options: { value: string; label: string }[];
};

export function Select({ label, labelClassName, options, className, ...props }: Props) {
  const isPlaceholderSelected =
    props.value === "" || props.value === undefined || props.value === null;

  return (
    <label className="grid gap-1">
      <div className={clsx("font-medium leading-[18px] text-black", labelClassName ?? "text-[12px]")}>{label}</div>
      <select
        className={clsx(
          "h-10 w-full rounded-xl border border-black/12 bg-white px-3 text-[14px] leading-[22px] shadow-sm",
          "focus:outline-none focus:ring-4 focus:ring-black/8 focus:border-black",
          "disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-500 disabled:opacity-100",
          isPlaceholderSelected ? "text-slate-400" : "text-foreground",
          className,
        )}
        {...props}
      >
        {options.map((o) => (
          <option
            key={o.value}
            value={o.value}
            className={o.value ? "text-foreground" : "text-slate-400"}
          >
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
