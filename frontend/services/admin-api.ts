import { API_BASE_URL } from "./api";
import type { ApiResponse } from "@/types";
import type {
  AdminApiKeyItem,
  AdminAuditPage,
  AdminHealthResponse,
  AdminJobPage,
  AdminLoginHistoryPage,
  AdminLogPage,
  AdminMediaPage,
  AdminMe,
  AdminSettingsOut,
  AdminUserItem,
  AdminUserPage,
  AdminWhatsappContactPage,
  AdminWhatsappEventPage,
  AdminWhatsappMessagePage,
  AdminWhatsappStats,
  AdminWatermarkItem,
  AdAnalyticsResponse,
  AdPlacementCreate,
  AdPlacementItem,
  AdPlacementReorder,
  AdProviderCreate,
  AdProviderItem,
  AdProviderTestResult,
  AdsOverview,
  AnalyticsEventPage,
  AnalyticsOverview,
  AnalyticsTimeseries,
  AnalyticsTopList,
  PlacementPreview,
  RetentionResult,
  DashboardResponse,
  JobRetryResult,
  SecurityOverview,
  StorageResponse,
  UserCreateRequest,
  UserUpdateRequest,
  WatermarkIn,
  WatermarkUpdate,
} from "@/types/admin";

const TOKEN_KEY = "hdguru-admin-tokens";

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

export class AdminAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AdminAuthError";
  }
}

function readTokens(): StoredTokens | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(TOKEN_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredTokens;
    if (!parsed?.accessToken) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeTokens(tokens: StoredTokens | null) {
  if (typeof window === "undefined") return;
  try {
    if (tokens) {
      window.localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
    } else {
      window.localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    /* storage unavailable */
  }
}

export function getStoredTokens(): StoredTokens | null {
  return readTokens();
}

export function clearAdminTokens(): void {
  writeTokens(null);
}

function errorPayload(data: unknown): string {
  const body = data as { error?: { message?: string } };
  return body?.error?.message ?? "Something went wrong. Please try again.";
}

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    return errorPayload(data);
  } catch {
    return fallback;
  }
}

async function refreshAccessToken(
  refreshToken: string,
): Promise<StoredTokens | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      access_token: string;
      refresh_token: string;
    };
    const next = {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    };
    writeTokens(next);
    return next;
  } catch {
    return null;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retried = false,
): Promise<ApiResponse<T>> {
  const tokens = readTokens();
  if (!tokens) {
    return { ok: false, error: "Not authenticated." };
  }

  const headers = new Headers(init.headers);
  if (init.body && typeof init.body === "string") {
    headers.set("content-type", "application/json");
  }
  headers.set("authorization", `Bearer ${tokens.accessToken}`);

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    return { ok: false, error: "Could not reach the server. Please try again." };
  }

  if (res.status === 401 && !retried && tokens.refreshToken) {
    const refreshed = await refreshAccessToken(tokens.refreshToken);
    if (refreshed) {
      return request<T>(path, init, true);
    }
    clearAdminTokens();
    return { ok: false, error: "Session expired. Please log in again." };
  }

  if (!res.ok) {
    return {
      ok: false,
      error: await parseError(
        res,
        `Request failed with status ${res.status}.`,
      ),
    };
  }

  try {
    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch {
    return { ok: false, error: "The server returned an invalid response." };
  }
}

function toQuery(
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  }
  return parts.length ? `?${parts.join("&")}` : "";
}

export const adminApi = {
  login: async (
    email: string,
    password: string,
  ): Promise<ApiResponse<AdminMe>> => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = (await res.json()) as {
        access_token: string;
        refresh_token: string;
      };
      if (!res.ok) {
        return { ok: false, error: errorPayload(data) };
      }
      writeTokens({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      });
      return adminApi.me();
    } catch {
      return { ok: false, error: "Could not reach the server. Please try again." };
    }
  },

  logout: async (): Promise<void> => {
    const tokens = readTokens();
    if (tokens?.refreshToken) {
      try {
        await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ refresh_token: tokens.refreshToken }),
        });
      } catch {
        /* best-effort */
      }
    }
    clearAdminTokens();
  },

  me: (): Promise<ApiResponse<AdminMe>> => request<AdminMe>("/api/v1/admin/me"),

  dashboard: (): Promise<ApiResponse<DashboardResponse>> =>
    request<DashboardResponse>("/api/v1/admin/dashboard"),

  listMedia: (
    page = 1,
    perPage = 20,
    opts: { status?: string; search?: string } = {},
  ): Promise<ApiResponse<AdminMediaPage>> =>
    request<AdminMediaPage>(
      `/api/v1/admin/media${toQuery({
        page,
        per_page: perPage,
        status: opts.status,
        search: opts.search,
      })}`,
    ),

  deleteMedia: (publicId: string): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>(`/api/v1/admin/media/${publicId}`, {
      method: "DELETE",
    }),

  listJobs: (
    page = 1,
    perPage = 20,
    opts: { status?: string; jobType?: string } = {},
  ): Promise<ApiResponse<AdminJobPage>> =>
    request<AdminJobPage>(
      `/api/v1/admin/jobs${toQuery({
        page,
        per_page: perPage,
        status: opts.status,
        job_type: opts.jobType,
      })}`,
    ),

  retryJob: (jobId: string): Promise<ApiResponse<JobRetryResult>> =>
    request<JobRetryResult>(`/api/v1/admin/jobs/${jobId}/retry`, {
      method: "POST",
    }),

  listUsers: (
    page = 1,
    perPage = 20,
    opts: { role?: string; active?: boolean; search?: string } = {},
  ): Promise<ApiResponse<AdminUserPage>> =>
    request<AdminUserPage>(
      `/api/v1/admin/users${toQuery({
        page,
        per_page: perPage,
        role: opts.role,
        active: opts.active,
        search: opts.search,
      })}`,
    ),

  createUser: (payload: UserCreateRequest): Promise<ApiResponse<AdminUserItem>> =>
    request<AdminUserItem>("/api/v1/admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateUser: (
    userId: string,
    payload: UserUpdateRequest,
  ): Promise<ApiResponse<AdminUserItem>> =>
    request<AdminUserItem>(`/api/v1/admin/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deleteUser: (userId: string): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>(`/api/v1/admin/users/${userId}`, {
      method: "DELETE",
    }),

  whatsappOverview: (): Promise<ApiResponse<AdminWhatsappStats>> =>
    request<AdminWhatsappStats>("/api/v1/admin/whatsapp/overview"),

  whatsappMessages: (
    page = 1,
    perPage = 20,
    opts: { direction?: string; status?: string; search?: string } = {},
  ): Promise<ApiResponse<AdminWhatsappMessagePage>> =>
    request<AdminWhatsappMessagePage>(
      `/api/v1/admin/whatsapp/messages${toQuery({
        page,
        per_page: perPage,
        direction: opts.direction,
        status: opts.status,
        search: opts.search,
      })}`,
    ),

  whatsappContacts: (
    page = 1,
    perPage = 20,
    opts: { search?: string } = {},
  ): Promise<ApiResponse<AdminWhatsappContactPage>> =>
    request<AdminWhatsappContactPage>(
      `/api/v1/admin/whatsapp/contacts${toQuery({
        page,
        per_page: perPage,
        search: opts.search,
      })}`,
    ),

  whatsappEvents: (
    page = 1,
    perPage = 20,
    opts: { status?: string } = {},
  ): Promise<ApiResponse<AdminWhatsappEventPage>> =>
    request<AdminWhatsappEventPage>(
      `/api/v1/admin/whatsapp/webhook-events${toQuery({
        page,
        per_page: perPage,
        status: opts.status,
      })}`,
    ),

  whatsappConfig: (): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>("/api/v1/admin/whatsapp/config"),

  whatsappUpdateConfig: (
    payload: Record<string, unknown>,
  ): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>("/api/v1/admin/whatsapp/config", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  whatsappTest: (): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>("/api/v1/admin/whatsapp/test", {
      method: "POST",
    }),

  listWatermarks: (): Promise<ApiResponse<AdminWatermarkItem[]>> =>
    request<AdminWatermarkItem[]>("/api/v1/admin/watermark"),

  watermarkPositions: (): Promise<ApiResponse<string[]>> =>
    request<string[]>("/api/v1/admin/watermark/positions"),

  createWatermark: (payload: WatermarkIn): Promise<ApiResponse<AdminWatermarkItem>> =>
    request<AdminWatermarkItem>("/api/v1/admin/watermark", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateWatermark: (
    id: string,
    payload: WatermarkUpdate,
  ): Promise<ApiResponse<AdminWatermarkItem>> =>
    request<AdminWatermarkItem>(`/api/v1/admin/watermark/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deleteWatermark: (
    id: string,
  ): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>(`/api/v1/admin/watermark/${id}`, {
      method: "DELETE",
    }),

  storage: (): Promise<ApiResponse<StorageResponse>> =>
    request<StorageResponse>("/api/v1/admin/storage"),

  settings: (): Promise<ApiResponse<AdminSettingsOut>> =>
    request<AdminSettingsOut>("/api/v1/admin/settings"),

  updateSettings: (
    items: Array<{ key: string; value: unknown }>,
  ): Promise<ApiResponse<AdminSettingsOut>> =>
    request<AdminSettingsOut>("/api/v1/admin/settings", {
      method: "PUT",
      body: JSON.stringify(items),
    }),

  logs: (
    page = 1,
    perPage = 20,
    opts: { level?: string } = {},
  ): Promise<ApiResponse<AdminLogPage>> =>
    request<AdminLogPage>(
      `/api/v1/admin/logs${toQuery({ page, per_page: perPage, level: opts.level })}`,
    ),

  auditLogs: (
    page = 1,
    perPage = 20,
    opts: { action?: string; actorType?: string } = {},
  ): Promise<ApiResponse<AdminAuditPage>> =>
    request<AdminAuditPage>(
      `/api/v1/admin/audit-logs${toQuery({
        page,
        per_page: perPage,
        action: opts.action,
        actor_type: opts.actorType,
      })}`,
    ),

  securityOverview: (): Promise<ApiResponse<SecurityOverview>> =>
    request<SecurityOverview>("/api/v1/admin/security/overview"),

  loginHistory: (
    page = 1,
    perPage = 20,
    opts: { success?: boolean } = {},
  ): Promise<ApiResponse<AdminLoginHistoryPage>> =>
    request<AdminLoginHistoryPage>(
      `/api/v1/admin/security/login-history${toQuery({
        page,
        per_page: perPage,
        success: opts.success,
      })}`,
    ),

  apiKeys: (): Promise<ApiResponse<AdminApiKeyItem[]>> =>
    request<AdminApiKeyItem[]>("/api/v1/admin/security/api-keys"),

  revokeApiKey: (keyId: string): Promise<ApiResponse<AdminApiKeyItem>> =>
    request<AdminApiKeyItem>(`/api/v1/admin/security/api-keys/${keyId}/revoke`, {
      method: "POST",
    }),

  logoutAllUserSessions: (
    userId: string,
  ): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>(
      `/api/v1/admin/security/users/${userId}/logout-all`,
      { method: "POST" },
    ),

  health: (): Promise<ApiResponse<AdminHealthResponse>> =>
    request<AdminHealthResponse>("/api/v1/admin/health"),

  // --- ads ---

  adsOverview: (): Promise<ApiResponse<AdsOverview>> =>
    request<AdsOverview>("/api/v1/admin/ads/overview"),

  listAdProviders: (): Promise<ApiResponse<AdProviderItem[]>> =>
    request<AdProviderItem[]>("/api/v1/admin/ads/providers"),

  createAdProvider: (
    payload: AdProviderCreate,
  ): Promise<ApiResponse<AdProviderItem>> =>
    request<AdProviderItem>("/api/v1/admin/ads/providers", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateAdProvider: (
    id: string,
    payload: Partial<AdProviderCreate>,
  ): Promise<ApiResponse<AdProviderItem>> =>
    request<AdProviderItem>(`/api/v1/admin/ads/providers/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deleteAdProvider: (id: string): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>(`/api/v1/admin/ads/providers/${id}`, {
      method: "DELETE",
    }),

  testAdProvider: (id: string): Promise<ApiResponse<AdProviderTestResult>> =>
    request<AdProviderTestResult>(`/api/v1/admin/ads/providers/${id}/test`, {
      method: "POST",
    }),

  listAdPlacements: (): Promise<ApiResponse<AdPlacementItem[]>> =>
    request<AdPlacementItem[]>("/api/v1/admin/ads/placements"),

  createAdPlacement: (
    payload: AdPlacementCreate,
  ): Promise<ApiResponse<AdPlacementItem>> =>
    request<AdPlacementItem>("/api/v1/admin/ads/placements", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateAdPlacement: (
    id: string,
    payload: Partial<AdPlacementCreate>,
  ): Promise<ApiResponse<AdPlacementItem>> =>
    request<AdPlacementItem>(`/api/v1/admin/ads/placements/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deleteAdPlacement: (
    id: string,
  ): Promise<ApiResponse<Record<string, unknown>>> =>
    request<Record<string, unknown>>(`/api/v1/admin/ads/placements/${id}`, {
      method: "DELETE",
    }),

  replaceAdPlacementSlots: (
    id: string,
    slots: Array<{
      provider_id: string;
      priority?: number;
      frequency?: string;
      enabled?: boolean;
    }>,
  ): Promise<ApiResponse<AdPlacementItem>> =>
    request<AdPlacementItem>(`/api/v1/admin/ads/placements/${id}/slots`, {
      method: "PUT",
      body: JSON.stringify(slots),
    }),

  reorderAdPlacementSlots: (
    id: string,
    payload: AdPlacementReorder,
  ): Promise<ApiResponse<AdPlacementItem>> =>
    request<AdPlacementItem>(`/api/v1/admin/ads/placements/${id}/reorder`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  previewAdPlacement: (id: string): Promise<ApiResponse<PlacementPreview>> =>
    request<PlacementPreview>(`/api/v1/admin/ads/placements/${id}/preview`),

  adAnalytics: (
    days = 30,
    group: "provider" | "placement" | "day" = "provider",
  ): Promise<ApiResponse<AdAnalyticsResponse>> =>
    request<AdAnalyticsResponse>(
      `/api/v1/admin/ads/analytics${toQuery({ days, group })}`,
    ),

  // --- analytics ---

  analyticsOverview: (
    days = 30,
  ): Promise<ApiResponse<AnalyticsOverview>> =>
    request<AnalyticsOverview>(
      `/api/v1/admin/analytics/overview${toQuery({ days })}`,
    ),

  analyticsTimeseries: (
    days = 30,
  ): Promise<ApiResponse<AnalyticsTimeseries>> =>
    request<AnalyticsTimeseries>(
      `/api/v1/admin/analytics/timeseries${toQuery({ days })}`,
    ),

  analyticsEvents: (
    page = 1,
    perPage = 20,
    opts: { event?: string; pagePath?: string } = {},
  ): Promise<ApiResponse<AnalyticsEventPage>> =>
    request<AnalyticsEventPage>(
      `/api/v1/admin/analytics/events${toQuery({
        page,
        per_page: perPage,
        event: opts.event,
        page_path: opts.pagePath,
      })}`,
    ),

  analyticsTopPages: (
    days = 30,
    limit = 10,
  ): Promise<ApiResponse<AnalyticsTopList>> =>
    request<AnalyticsTopList>(
      `/api/v1/admin/analytics/top-pages${toQuery({ days, limit })}`,
    ),

  analyticsDevices: (
    dimension: "device" | "browser" | "os" = "device",
    days = 30,
    limit = 10,
  ): Promise<ApiResponse<AnalyticsTopList>> =>
    request<AnalyticsTopList>(
      `/api/v1/admin/analytics/devices${toQuery({ dimension, days, limit })}`,
    ),

  analyticsReferrers: (
    days = 30,
    limit = 10,
  ): Promise<ApiResponse<AnalyticsTopList>> =>
    request<AnalyticsTopList>(
      `/api/v1/admin/analytics/referrers${toQuery({ days, limit })}`,
    ),

  runAnalyticsRetention: (): Promise<ApiResponse<RetentionResult>> =>
    request<RetentionResult>("/api/v1/admin/analytics/retention/run", {
      method: "POST",
    }),
};
