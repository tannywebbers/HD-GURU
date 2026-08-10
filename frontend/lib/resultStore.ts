"use client";

import type { HDResult } from "@/types";

const STORAGE_KEY = "hdguru-result";

export function saveResult(result: HDResult) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result));
  } catch {
    /* storage unavailable */
  }
}

export function loadResult(): HDResult | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as HDResult) : null;
  } catch {
    return null;
  }
}
