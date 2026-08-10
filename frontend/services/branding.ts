import { APP_DESCRIPTION, APP_NAME } from "@/lib/constants";
import { API_BASE_URL, isBackendEnabled } from "./api";

// Runtime branding served by GET /api/v1/settings/public (non-secret rows
// only). The server always returns a complete payload, so the client can rely
// on every field being present. When the backend is disabled or unreachable we
// fall back to the compiled-in HD Guru defaults so nothing ever breaks.

export interface Branding {
  app_name: string;
  app_description: string;
  app_logo_url: string | null;
  app_theme_color: string | null;
  app_primary_color: string | null;
}

const CACHE_KEY = "hdguru-branding";
const CACHE_TTL_MS = 5 * 60 * 1000;

let memoryCache: Branding | null = null;
let memoryCacheAt = 0;

export function defaultBranding(): Branding {
  return {
    app_name: APP_NAME,
    app_description: APP_DESCRIPTION,
    app_logo_url: null,
    app_theme_color: null,
    app_primary_color: null,
  };
}

export function getCachedBranding(): Branding | null {
  if (memoryCache && Date.now() - memoryCacheAt < CACHE_TTL_MS) {
    return memoryCache;
  }
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(CACHE_KEY);
    if (raw) {
      const cached = JSON.parse(raw) as { fetchedAt: number; branding: Branding };
      if (Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
        memoryCache = cached.branding;
        memoryCacheAt = Date.now();
        return cached.branding;
      }
    }
  } catch {
    /* storage unavailable */
  }
  return null;
}

export async function fetchBranding(force = false): Promise<Branding> {
  if (!isBackendEnabled) return defaultBranding();
  if (!force) {
    const cached = getCachedBranding();
    if (cached) return cached;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/settings/public`, {
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) return defaultBranding();
    const branding = (await res.json()) as Branding;
    memoryCache = branding;
    memoryCacheAt = Date.now();
    try {
      window.localStorage.setItem(
        CACHE_KEY,
        JSON.stringify({ fetchedAt: Date.now(), branding }),
      );
    } catch {
      /* storage unavailable */
    }
    return branding;
  } catch {
    return defaultBranding();
  }
}

// Apply branding to document-level surfaces that are static at build time.
// Full runtime rebranding of every server-rendered page title / OG tag is not
// attempted; this keeps the visible brand consistent where it matters most.
export function applyBrandingToDocument(branding: Branding): void {
  if (typeof document === "undefined") return;

  if (branding.app_theme_color) {
    document
      .querySelectorAll('meta[name="theme-color"]')
      .forEach((el) => el.setAttribute("content", branding.app_theme_color as string));
  }

  if (branding.app_description) {
    const setContent = (selector: string) => {
      const el = document.querySelector(selector);
      if (el) el.setAttribute("content", branding.app_description);
    };
    setContent('meta[name="description"]');
    setContent('meta[property="og:description"]');
    setContent('meta[name="twitter:description"]');
  }

  if (branding.app_name && branding.app_name !== APP_NAME) {
    const siteName = document.querySelector('meta[property="og:site_name"]');
    if (siteName) siteName.setAttribute("content", branding.app_name);
    const homeTitle = `${APP_NAME} — Free AI HD Photo & Video Enhancer`;
    if (document.title === homeTitle) {
      document.title = `${branding.app_name} — Free AI HD Photo & Video Enhancer`;
    }
  }

  if (branding.app_primary_color) {
    document.documentElement.style.setProperty("--brand-primary", branding.app_primary_color);
  }
}
