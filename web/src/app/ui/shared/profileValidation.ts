"use client";

export const NIGERIAN_MOBILE_NUMBER_REGEX = /^\+234\d{10}$/;
export const NIN_NUMBER_REGEX = /^\d{11}$/;
export const BVN_NUMBER_REGEX = /^\d{11}$/;

export function sanitizeMobileNumberInput(value: string) {
  const compact = value.replace(/\s+/g, "");
  const hasLeadingPlus = compact.startsWith("+");
  const digits = compact.replace(/\D/g, "").slice(0, 13);
  return `${hasLeadingPlus ? "+" : ""}${digits}`;
}

export function sanitizeNinInput(value: string) {
  return value.replace(/\D/g, "").slice(0, 11);
}

export function sanitizeBvnInput(value: string) {
  return value.replace(/\D/g, "").slice(0, 11);
}

export function getMobileNumberError(value: string, { required = true }: { required?: boolean } = {}) {
  const normalized = value.replace(/\s+/g, "");
  if (!normalized) {
    return required ? "Mobile number is required." : null;
  }
  if (!NIGERIAN_MOBILE_NUMBER_REGEX.test(normalized)) {
    return "Mobile number must start with +234 and contain 13 digits excluding the + sign.";
  }
  return null;
}

export function getNinNumberError(value: string, { required = true }: { required?: boolean } = {}) {
  const normalized = value.trim();
  if (!normalized) {
    return required ? "NIN number is required." : null;
  }
  if (!NIN_NUMBER_REGEX.test(normalized)) {
    return "NIN number must be exactly 11 digits.";
  }
  return null;
}

export function getBvnNumberError(value: string, { required = true }: { required?: boolean } = {}) {
  const normalized = value.trim();
  if (!normalized) {
    return required ? "BVN number is required." : null;
  }
  if (!BVN_NUMBER_REGEX.test(normalized)) {
    return "BVN number must be exactly 11 digits.";
  }
  return null;
}
