"use client";

import { Eye, EyeOff } from "lucide-react";
import { clsx } from "clsx";
import { useState, type InputHTMLAttributes, type ReactNode } from "react";

type InputSize = "sm" | "md" | "lg";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  helperText?: string;
  error?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  inputSize?: InputSize;
  isLoading?: boolean;
};

const sizeStyles: Record<InputSize, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-4 text-sm",
  lg: "h-14 px-5 text-base",
};

export function Input({
  label,
  helperText,
  error,
  leftIcon,
  rightIcon,
  inputSize = "md",
  className,
  disabled,
  isLoading,
  type,
  ...props
}: Props) {
  const hasError = !!error;
  const isPasswordField = type === "password";
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const resolvedType = isPasswordField ? (isPasswordVisible ? "text" : "password") : type;
  const hasTrailingAdornment = Boolean(rightIcon || isLoading || isPasswordField);

  return (
    <div className="w-full">
      {label && (
        <label className="mb-2 block text-sm font-medium text-black">
          {label}
        </label>
      )}
      <div className="relative">
        {leftIcon && (
          <div className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-black/45">
            {leftIcon}
          </div>
        )}
        <input
          className={clsx(
            "w-full rounded-xl border bg-white text-black placeholder:text-[color:var(--form-placeholder)] shadow-sm",
            "transition-all duration-200 ease-in-out",
            "focus:outline-none focus:ring-4 focus:ring-black/8 focus:border-black",
            "disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-500 disabled:opacity-100",
            hasError && "border-danger focus:ring-danger/50 focus:border-danger animate-shake",
            !hasError && "border-black/12 hover:border-black/25",
            leftIcon && "pl-10",
            hasTrailingAdornment && "pr-11",
            sizeStyles[inputSize],
            className
          )}
          disabled={disabled || isLoading}
          type={resolvedType}
          {...props}
        />
        {isPasswordField && !isLoading ? (
          <button
            type="button"
            onClick={() => setIsPasswordVisible((current) => !current)}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-black/45 transition hover:text-black focus:outline-none focus:ring-2 focus:ring-black/10 disabled:cursor-not-allowed disabled:text-slate-400"
            aria-label={isPasswordVisible ? "Hide password" : "Show password"}
            aria-pressed={isPasswordVisible}
            disabled={disabled}
          >
            {isPasswordVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        ) : rightIcon ? (
          <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-black/45">
            {rightIcon}
          </div>
        ) : null}
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <svg
              className="h-4 w-4 animate-spin text-black/45"
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
          </div>
        )}
      </div>
      {helperText && !hasError && (
        <p className="mt-1.5 text-xs text-black/55">{helperText}</p>
      )}
      {hasError && (
        <p className="mt-1.5 text-xs text-danger flex items-center gap-1">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}

// Search input variant
export function SearchInput({
  className,
  ...props
}: Omit<Props, "leftIcon">) {
  return (
    <Input
      leftIcon={
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      }
      className={clsx("pl-10", className)}
      {...props}
    />
  );
}
