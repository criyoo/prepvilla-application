"use client";

import { clsx } from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "destructive"
  | "gradient"
  | "google"
  | "outline"
  | "elevated"
  | "menu"
  | "menuActive";
type ButtonSize = "sm" | "md" | "lg" | "xl";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  isLoading?: boolean;
  fullWidth?: boolean;
};

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "border border-transparent bg-[linear-gradient(135deg,var(--primary-hover)_0%,var(--primary)_64%,var(--accent)_100%)] text-white shadow-[0_18px_34px_rgba(15,23,40,0.18)] hover:-translate-y-0.5 hover:brightness-105 hover:shadow-[0_20px_38px_rgba(15,23,40,0.24)] active:bg-[linear-gradient(135deg,var(--primary-hover)_0%,var(--primary-hover)_100%)]",
  gradient:
    "border border-white/10 bg-[linear-gradient(120deg,var(--primary-deep)_0%,var(--secondary-color)_52%,var(--accent)_100%)] text-white shadow-[0_20px_40px_rgba(15,23,40,0.18)] hover:-translate-y-0.5 hover:brightness-105 hover:shadow-[0_22px_44px_rgba(139,97,120,0.24)]",
  google:
    "border border-white/15 bg-[linear-gradient(120deg,#2563eb_0%,#4f46e5_34%,#9333ea_68%,var(--palette-coral)_100%)] !font-bold text-white shadow-[0_18px_36px_rgba(79,70,229,0.28)] hover:-translate-y-0.5 hover:brightness-110 hover:shadow-[0_22px_42px_rgba(147,51,234,0.3)] active:brightness-95",
  secondary:
    "border border-[rgba(23,32,51,0.12)] bg-[linear-gradient(135deg,rgba(255,255,255,0.98)_0%,rgba(247,241,232,0.94)_100%)] text-primary-deep shadow-[0_12px_26px_rgba(15,23,40,0.06)] hover:-translate-y-0.5 hover:border-[rgba(139,97,120,0.36)] hover:bg-[linear-gradient(135deg,rgba(255,255,255,0.98)_0%,rgba(239,226,232,0.92)_100%)] hover:text-primary-deep",
  outline:
    "border-2 border-accent/70 bg-transparent text-accent hover:-translate-y-0.5 hover:bg-accent-soft/70 hover:text-accent-hover",
  ghost:
    "bg-transparent text-foreground hover:-translate-y-0.5 hover:bg-[rgba(139,97,120,0.12)] hover:text-primary-deep",
  destructive:
    "bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-lg shadow-red-500/25",
  elevated:
    "border border-[rgba(23,32,51,0.1)] bg-[linear-gradient(180deg,rgba(255,255,255,0.98)_0%,rgba(247,241,232,0.94)_100%)] text-primary-deep shadow-[0_22px_44px_rgba(15,23,40,0.08)] hover:-translate-y-0.5 hover:shadow-[0_26px_48px_rgba(139,97,120,0.16)]",
  menu:
    "border border-[rgba(23,32,51,0.12)] bg-[linear-gradient(180deg,rgba(255,255,255,0.98)_0%,rgba(247,241,232,0.94)_100%)] text-primary-deep shadow-[0_10px_20px_rgba(15,23,40,0.06)] hover:-translate-y-0.5 hover:border-[rgba(139,97,120,0.36)] hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.98)_0%,rgba(239,226,232,0.96)_100%)] hover:shadow-[0_16px_30px_rgba(15,23,40,0.08),0_8px_18px_rgba(139,97,120,0.12)] active:translate-y-0 active:border-[rgba(15,23,40,0.28)] active:bg-[linear-gradient(135deg,var(--primary-deep)_0%,var(--primary)_66%,var(--accent)_100%)] active:text-white active:shadow-[0_14px_26px_rgba(15,23,40,0.18)]",
  menuActive:
    "border border-[rgba(15,23,40,0.28)] bg-[linear-gradient(135deg,var(--primary-deep)_0%,var(--primary)_66%,var(--accent)_100%)] text-white shadow-[0_16px_30px_rgba(15,23,40,0.18),0_8px_18px_rgba(139,97,120,0.12)]",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs gap-1.5 rounded-lg",
  md: "h-10 px-4 text-sm gap-2 rounded-xl",
  lg: "h-12 px-6 text-base gap-2 rounded-xl",
  xl: "h-14 px-8 text-lg gap-3 rounded-2xl",
};

export function Button({
  className,
  variant = "primary",
  size = "md",
  leftIcon,
  rightIcon,
  isLoading,
  fullWidth,
  children,
  disabled,
  ...props
}: Props) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center font-semibold transition-all duration-200",
        "relative overflow-hidden",
        "focus:outline-none focus:ring-2 focus:ring-accent/60 focus:ring-offset-2 focus:ring-offset-background",
        "active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100",
        variantStyles[variant],
        sizeStyles[size],
        fullWidth && "w-full",
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Loading...</span>
        </>
      ) : (
        <>
          {leftIcon}
          {children}
          {rightIcon}
        </>
      )}
    </button>
  );
}

// Icon Button variant
export function IconButton({
  className,
  variant = "ghost",
  size = "md",
  isLoading,
  children,
  disabled,
  ...props
}: Omit<Props, "leftIcon" | "rightIcon" | "fullWidth">) {
  const iconSizeStyles: Record<ButtonSize, string> = {
    sm: "h-8 w-8 rounded-lg",
    md: "h-10 w-10 rounded-xl",
    lg: "h-12 w-12 rounded-xl",
    xl: "h-14 w-14 rounded-2xl",
  };

  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center font-semibold transition-all duration-200",
        "relative overflow-hidden",
        "focus:outline-none focus:ring-2 focus:ring-accent/60 focus:ring-offset-2 focus:ring-offset-background",
        "active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100",
        variantStyles[variant],
        iconSizeStyles[size],
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <svg
          className="animate-spin h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : (
        children
      )}
    </button>
  );
}
