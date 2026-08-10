"use client";

import type { StoredMediaFile } from "@/types";

const STORAGE_KEY = "hdguru-files";

export function saveFiles(files: StoredMediaFile[]) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(files));
  } catch {
    /* storage unavailable */
  }
}

export function loadFiles(): StoredMediaFile[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StoredMediaFile[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function clearFiles() {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable */
  }
}
