"use client";

import { useCallback, useEffect, useRef } from "react";

type FormDraft = Record<string, unknown>;

function getStorage(storageType: "local" | "session") {
  if (typeof window === "undefined") return null;
  return storageType === "session" ? window.sessionStorage : window.localStorage;
}

export function useFormDraft<T extends FormDraft>(
  key: string | null,
  value: T,
  restore: (draft: Partial<T>) => void,
  ready = true,
  storageType: "local" | "session" = "local",
) {
  const restoreRef = useRef(restore);
  const restoredKeyRef = useRef<string | null>(null);
  const skipNextWriteRef = useRef(false);
  const clearedValueRef = useRef<string | null>(null);
  const serializedValue = JSON.stringify(value);
  const latestSerializedValueRef = useRef(serializedValue);
  restoreRef.current = restore;
  latestSerializedValueRef.current = serializedValue;

  useEffect(() => {
    if (!key || !ready || restoredKeyRef.current === key) return;

    restoredKeyRef.current = key;
    clearedValueRef.current = null;
    const storage = getStorage(storageType);
    const saved = storage?.getItem(key);
    if (!saved) {
      clearedValueRef.current = serializedValue;
      return;
    }

    try {
      skipNextWriteRef.current = true;
      restoreRef.current(JSON.parse(saved) as Partial<T>);
    } catch {
      storage?.removeItem(key);
    }
  }, [key, ready, serializedValue, storageType]);

  useEffect(() => {
    if (!key || !ready || restoredKeyRef.current !== key) return;
    if (skipNextWriteRef.current) {
      skipNextWriteRef.current = false;
      return;
    }
    if (clearedValueRef.current === serializedValue) return;
    clearedValueRef.current = null;
    getStorage(storageType)?.setItem(key, serializedValue);
  }, [key, ready, serializedValue, storageType]);

  return useCallback(() => {
    if (!key) return;
    const storage = getStorage(storageType);
    storage?.removeItem(key);
    clearedValueRef.current = serializedValue;
    window.setTimeout(() => {
      storage?.removeItem(key);
      clearedValueRef.current = latestSerializedValueRef.current;
    }, 0);
  }, [key, serializedValue, storageType]);
}
