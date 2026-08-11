export type AdminRole =
  | "user"
  | "viewer"
  | "operator"
  | "admin"
  | "super_admin";

export interface AdminMe {
  id: string;
  email: string;
  full_name: string | null;
  role: AdminRole;
  permissions: string[];
}

export interface DashboardCounters {
  uploads_total: number;
  uploads_today: number;
  media_total: number;
  media_completed: number;
  downloads_total: number;
  whatsapp_deliveries_total: number;
  whatsapp_messages_total: number;
  whatsapp_contacts_total: number;
  users_total: number;
  jobs_queued: number;
  jobs_running: number;
  jobs_failed: number;
  jobs_succeeded: number;
  error_logs_24h: number;
}

export interface DashboardResponse {
  counters: DashboardCounters;
  recent_uploads: Array<Record<string, unknown>>;
  recent_jobs: Array<Record<string, unknown>>;
  storage: Record<string, unknown>;
  system: Record<string, unknown>;
  health: Record<string, unknown>;
}

export interface PageMeta {
  items: unknown[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminMediaItem {
  id: string;
  public_id: string;
  seq: number;
  original_filename: string;
  mime_type: string;
  extension: string;
  file_size: number;
  width: number | null;
  height: number | null;
  duration: number | null;
  storage_provider: string;
  status: string;
  error: string | null;
  download_count: number;
  whatsapp_delivery_count: number;
  created_at: string;
  updated_at: string;
  upload_public_id: string | null;
  processed: Record<string, unknown> | null;
}

export interface AdminMediaPage extends PageMeta {
  items: AdminMediaItem[];
}

export interface AdminJobItem {
  id: string;
  job_type: string;
  status: string;
  upload_id: string | null;
  celery_task_id: string | null;
  args: Record<string, unknown>;
  result: Record<string, unknown> | null;
  retries: number;
  max_retries: number;
  worker_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminJobPage extends PageMeta {
  items: AdminJobItem[];
}

export interface JobRetryResult {
  job_id: string;
  status: string;
  celery_task_id: string | null;
}

export interface AdminUserItem {
  id: string;
  email: string;
  full_name: string | null;
  role: AdminRole;
  is_active: boolean;
  email_verified: boolean;
  last_login_at: string | null;
  failed_login_count: number;
  is_locked: boolean;
  locked_until: string | null;
  must_change_password: boolean;
  token_version: number;
  created_at: string;
  updated_at: string;
  uploads_count: number;
}

export interface AdminUserPage extends PageMeta {
  items: AdminUserItem[];
}

export interface UserCreateRequest {
  email: string;
  password: string;
  full_name?: string | null;
  role: AdminRole;
  is_active?: boolean;
  must_change_password?: boolean;
}

export interface UserUpdateRequest {
  full_name?: string | null;
  role?: AdminRole;
  is_active?: boolean;
  must_change_password?: boolean;
  email_verified?: boolean;
}

export interface AdminWhatsappConfig {
  enabled: boolean;
  phone_number_id: string | null;
  phone_number: string | null;
  business_account_id: string | null;
  api_version: string;
  graph_api_base_url: string | null;
  token_configured: boolean;
  verify_token_configured: boolean;
  app_secret_configured: boolean;
  access_token_masked: string | null;
  verify_token_masked: string | null;
  app_secret_masked: string | null;
  connected: boolean;
}

export interface AdminWhatsappStats {
  messages_total: number;
  messages_inbound: number;
  messages_outbound: number;
  messages_failed: number;
  messages_delivered: number;
  messages_read: number;
  contacts_total: number;
  events_total: number;
  events_failed: number;
  webhook: Record<string, unknown>;
  config: AdminWhatsappConfig;
}

export interface AdminWhatsappMessageItem {
  id: string;
  meta_message_id: string;
  direction: string;
  message_type: string;
  text: string | null;
  media_public_id: string | null;
  status: string;
  error_code: string | null;
  error_message: string | null;
  timestamp: string | null;
  created_at: string;
  contact_phone: string | null;
  contact_name: string | null;
}

export interface AdminWhatsappMessagePage extends PageMeta {
  items: AdminWhatsappMessageItem[];
}

export interface AdminWhatsappContactItem {
  id: string;
  wa_id: string;
  phone_number: string;
  display_name: string | null;
  first_seen: string;
  last_seen: string;
  created_at: string;
}

export interface AdminWhatsappContactPage extends PageMeta {
  items: AdminWhatsappContactItem[];
}

export interface AdminWhatsappEventItem {
  id: string;
  object: string | null;
  entry_id: string | null;
  event_type: string;
  status: string;
  error: string | null;
  received_at: string;
  processed_at: string | null;
  created_at: string;
}

export interface AdminWhatsappEventPage extends PageMeta {
  items: AdminWhatsappEventItem[];
}

export interface AdminWatermarkItem {
  id: string;
  name: string;
  type: "text" | "image";
  text: string | null;
  image_url: string | null;
  position: string;
  opacity: number;
  size_percent: number;
  margin: number | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface WatermarkIn {
  name: string;
  type: "text" | "image";
  text?: string | null;
  image_url?: string | null;
  position?: string;
  opacity?: number;
  size_percent?: number;
  margin?: number | null;
  enabled?: boolean;
}

export interface WatermarkUpdate {
  name?: string;
  type?: "text" | "image";
  text?: string | null;
  image_url?: string | null;
  position?: string;
  opacity?: number;
  size_percent?: number;
  margin?: number | null;
  enabled?: boolean;
}

export interface StorageResponse {
  driver: string;
  provider: string;
  base_path: string | null;
  bucket: string | null;
  endpoint: string | null;
  region: string | null;
  media_url_mode: string;
  writable: boolean;
  objects: number;
  used_bytes: number | null;
}

export interface AdminSettingItem {
  key: string;
  group: string;
  value: unknown;
  description: string | null;
  is_secret: boolean;
  updated_at: string | null;
}

export interface AdminSettingsOut {
  settings: AdminSettingItem[];
}

export interface AdminLogItem {
  id: string;
  level: string;
  logger_name: string | null;
  message: string;
  context: Record<string, unknown>;
  created_at: string;
}

export interface AdminLogPage extends PageMeta {
  items: AdminLogItem[];
}

export interface AdminAuditItem {
  id: string;
  actor_id: string | null;
  actor_type: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  result: string;
  created_at: string;
}

export interface AdminAuditPage extends PageMeta {
  items: AdminAuditItem[];
}

export interface AdminLoginHistoryItem {
  id: string;
  email: string;
  success: boolean;
  failure_reason: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AdminLoginHistoryPage extends PageMeta {
  items: AdminLoginHistoryItem[];
}

export interface AdminApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  scopes: unknown[];
  last_used_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
  user_email: string | null;
}

export interface SecurityOverview {
  users_total: number;
  locked_accounts: number;
  active_api_keys: number;
  failed_logins_24h: number;
  recent_sessions: number;
}

export interface AdminHealthResponse {
  status: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  components: Record<string, unknown>;
  timestamp: string;
  workers: Array<Record<string, unknown>>;
}

// --- ads & monetization -----------------------------------------------------

export type AdProviderType =
  | "script"
  | "iframe"
  | "html"
  | "javascript"
  | "native"
  | "banner"
  | "custom";

export interface AdProviderItem {
  id: string;
  name: string;
  provider_type: AdProviderType;
  base_url: string | null;
  publisher_id: string | null;
  zone_id: string | null;
  site_id: string | null;
  placement_config: Record<string, unknown>;
  custom_script: string | null;
  click_through_url: string | null;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdProviderCreate {
  name: string;
  provider_type?: AdProviderType;
  base_url?: string | null;
  publisher_id?: string | null;
  zone_id?: string | null;
  site_id?: string | null;
  placement_config?: Record<string, unknown> | null;
  custom_script?: string | null;
  click_through_url?: string | null;
  enabled?: boolean;
}

export interface AdSlotItem {
  id: string;
  provider_id: string;
  provider_name: string;
  provider_enabled: boolean;
  priority: number;
  frequency: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

export interface AdPlacementItem {
  id: string;
  name: string;
  label: string;
  enabled: boolean;
  width: number | null;
  height: number | null;
  responsive: boolean;
  behavior: "lazy" | "eager";
  slots: AdSlotItem[];
  created_at: string | null;
  updated_at: string | null;
}

export interface AdPlacementCreate {
  name: string;
  label: string;
  enabled?: boolean;
  width?: number | null;
  height?: number | null;
  responsive?: boolean;
  behavior?: "lazy" | "eager";
  slots?: AdSlotIn[];
}

export interface AdSlotIn {
  provider_id: string;
  priority?: number;
  frequency?: string;
  enabled?: boolean;
  config?: Record<string, unknown> | null;
}

export interface AdPlacementReorder {
  provider_ids: string[];
}

export interface AdProviderTestResult {
  ok: boolean;
  missing: string[];
  render_kind: string;
  render_ready: boolean;
  snippet_preview: string;
}

export interface AdsOverview {
  enabled: boolean;
  providers_total: number;
  providers_enabled: number;
  placements_total: number;
  placements_enabled: number;
  active_slots: number;
  impressions: number;
  impressions_today: number;
  clicks: number;
  clicks_today: number;
  load_failures: number;
  load_failures_today: number;
  ctr: number;
  default_behavior: string;
  providers: Array<{
    id: string;
    name: string;
    provider_type: string;
    enabled: boolean;
  }>;
}

export interface AdAnalyticsItem {
  key: string;
  impression: number;
  click: number;
  load_failure: number;
  ctr?: number;
}

export interface AdAnalyticsResponse {
  days: number;
  totals: {
    impressions: number;
    clicks: number;
    load_failures: number;
    ctr: number;
  };
  group: string;
  items: AdAnalyticsItem[];
}

export interface PlacementPreview {
  enabled: boolean;
  placement: {
    name: string;
    label: string;
    behavior: string;
    width: number | null;
    height: number | null;
    responsive: boolean;
    slots: Array<{
      provider_id: string;
      name: string;
      type: string;
      frequency: string;
      width: number | null;
      height: number | null;
      responsive: boolean;
      render: { kind: string; content?: string; src?: string };
    }>;
  } | null;
}

// --- traffic analytics ------------------------------------------------------

export interface AnalyticsOverview {
  range_days: number;
  visitors: number;
  page_views: number;
  uploads: number;
  uploads_completed: number;
  get_hd_clicks: number;
  whatsapp_opens: number;
  whatsapp_requests: number;
  media_deliveries: number;
  errors: number;
  processing_rate: number | null;
  ad_impressions: number;
  ad_clicks: number;
  ad_load_failures: number;
}

export interface AnalyticsTimePoint {
  date: string;
  visitors: number;
  page_views: number;
  uploads: number;
  get_hd_clicks: number;
  media_deliveries: number;
  errors: number;
}

export interface AnalyticsTimeseries {
  points: AnalyticsTimePoint[];
}

export interface AnalyticsEventItem {
  id: string;
  event_type: string;
  session_id: string | null;
  page: string | null;
  device: string | null;
  browser: string | null;
  os: string | null;
  country: string | null;
  referrer_category: string | null;
  created_at: string;
}

export interface AnalyticsEventPage extends PageMeta {
  items: AnalyticsEventItem[];
}

export interface AnalyticsTopItem {
  key: string;
  count: number;
}

export interface AnalyticsTopList {
  items: AnalyticsTopItem[];
}

export interface RetentionResult {
  analytics_events_deleted: number;
  ad_events_deleted: number;
}
