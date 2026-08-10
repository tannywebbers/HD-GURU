import { API_BASE_URL, isBackendEnabled } from "./api";
import { generateId } from "@/lib/format";

// Public-facing ad configuration + anonymous analytics ingestion.
// Endpoints are safe by construction: the server never sends API keys here,
// and the ingestion endpoints only ever receive coarse categories.

export interface AdSlotRender {
  kind: "script" | "iframe" | "html" | "custom";
  content?: string;
  src?: string;
}

export interface AdSlotConfig {
  provider_id: string;
  name: string;
  type: string;
  frequency: string;
  width: number | null;
  height: number | null;
  responsive: boolean;
  render: AdSlotRender;
}

export interface AdPlacementConfig {
  name: string;
  label: string;
  behavior: "lazy" | "eager";
  width: number | null;
  height: number | null;
  responsive: boolean;
  slots: AdSlotConfig[];
}

export interface AdConfig {
  enabled: boolean;
  placements: Record<string, AdPlacementConfig>;
  version: string;
}

export type TrackEventName =
  | "page_view"
  | "upload_started"
  | "upload_completed"
  | "upload_failed"
  | "processing_started"
  | "processing_completed"
  | "processing_failed"
  | "get_hd_clicked"
  | "whatsapp_opened"
  | "whatsapp_request"
  | "whatsapp_message_received"
  | "media_delivered";

const SESSION_KEY = "hdguru-session";
const CONFIG_CACHE_KEY = "hdguru-ad-config";
const CONFIG_CACHE_TTL_MS = 5 * 60 * 1000;

interface CachedConfig {
  fetchedAt: number;
  config: AdConfig;
}

function sessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = window.localStorage.getItem(SESSION_KEY);
    if (!id) {
      id = generateId("sess");
      window.localStorage.setItem(SESSION_KEY, id);
    }
    return id;
  } catch {
    return "";
  }
}

export function resetSession(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(SESSION_KEY);
  } catch {
    /* storage unavailable */
  }
}

export async function fetchAdConfig(force = false): Promise<AdConfig | null> {
  if (!isBackendEnabled) return null;
  try {
    const cachedRaw = window.localStorage.getItem(CONFIG_CACHE_KEY);
    if (!force && cachedRaw) {
      const cached = JSON.parse(cachedRaw) as CachedConfig;
      if (Date.now() - cached.fetchedAt < CONFIG_CACHE_TTL_MS) {
        return cached.config;
      }
    }
    const res = await fetch(`${API_BASE_URL}/api/v1/ads/config`);
    if (!res.ok) return null;
    const config = (await res.json()) as AdConfig;
    try {
      window.localStorage.setItem(
        CONFIG_CACHE_KEY,
        JSON.stringify({ fetchedAt: Date.now(), config }),
      );
    } catch {
      /* storage unavailable */
    }
    return config;
  } catch {
    return null;
  }
}

export function getCachedAdConfig(): AdConfig | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(CONFIG_CACHE_KEY);
    if (!raw) return null;
    return (JSON.parse(raw) as CachedConfig).config ?? null;
  } catch {
    return null;
  }
}

export function getPlacementConfig(
  config: AdConfig | null,
  name: string,
): AdPlacementConfig | null {
  if (!config?.enabled) return null;
  return config.placements[name] ?? null;
}

export function trackEvent(
  event: TrackEventName,
  opts: { page?: string; referrer?: string; props?: Record<string, unknown> } = {},
): void {
  if (!isBackendEnabled || typeof window === "undefined") return;
  const payload = {
    event,
    session_id: sessionId(),
    page: opts.page ?? window.location.pathname,
    referrer: opts.referrer ?? document.referrer,
    props: opts.props,
  };
  void fetch(`${API_BASE_URL}/api/v1/analytics/events`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => undefined);
}

export function trackAdEvent(
  eventType: "impression" | "click" | "load_failure",
  placement: string,
  opts: { page?: string; providerId?: string } = {},
): void {
  if (!isBackendEnabled || typeof window === "undefined") return;
  const payload = {
    event_type: eventType,
    placement,
    page: opts.page ?? window.location.pathname,
    session_id: sessionId(),
    provider_id: opts.providerId,
  };
  void fetch(`${API_BASE_URL}/api/v1/ads/event`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => undefined);
}
