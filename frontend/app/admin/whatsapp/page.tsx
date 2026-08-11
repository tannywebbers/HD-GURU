"use client";

import { useCallback, useEffect, useState } from "react";
import { PlugZap, RefreshCw, Save } from "lucide-react";
import { adminApi } from "@/services/admin-api";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type {
  AdminWhatsappConfig,
  AdminWhatsappEventPage,
  AdminWhatsappMessagePage,
  AdminWhatsappStats,
} from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  Badge,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
  StatCard,
  StatusBadge,
} from "@/components/admin/ui";
import { useToast } from "@/components/ToastProvider";

type Tab = "overview" | "messages" | "events" | "config";

const WEBHOOK_FIELDS = ["webhook_url", "webhook_token", "webhook_secret", "verify_token"];

const SECRET_FIELDS = ["access_token", "verify_token", "app_secret"] as const;

// Sentinel the backend uses to keep an unchanged secret intact.
const UNCHANGED = "***";

function configInputClass(disabled: boolean): string {
  return `w-full rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 focus:ring-2 focus:ring-primary-500/30 dark:bg-white/5 ${
    disabled ? "cursor-not-allowed opacity-60" : ""
  }`;
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export default function AdminWhatsappPage() {
  const { showToast } = useToast();
  const { hasPermission } = useAdminAuth();
  const canManage = hasPermission("whatsapp.manage");
  const canEditCredentials = hasPermission("whatsapp.credentials");
  const canEditConfig = canManage || canEditCredentials;

  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<AdminWhatsappStats | null>(null);
  const [messages, setMessages] = useState<AdminWhatsappMessagePage | null>(null);
  const [events, setEvents] = useState<AdminWhatsappEventPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msgPage, setMsgPage] = useState(1);
  const [evtPage, setEvtPage] = useState(1);
  const [testing, setTesting] = useState(false);
  const [config, setConfig] = useState<AdminWhatsappConfig | null>(null);
  const [configDraft, setConfigDraft] = useState<Record<string, string | boolean>>({});
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);

  const loadConfig = useCallback(async () => {
    setConfigLoading(true);
    setConfigError(null);
    const res = await adminApi.whatsappConfig();
    if (res.ok && res.data) {
      setConfig(res.data);
      const next: Record<string, string | boolean> = {
        enabled: res.data.enabled,
        phone_number_id: res.data.phone_number_id ?? "",
        phone_number: res.data.phone_number ?? "",
        business_account_id: res.data.business_account_id ?? "",
        api_version: res.data.api_version ?? "v22.0",
        graph_api_base_url: res.data.graph_api_base_url ?? "",
      };
      for (const field of SECRET_FIELDS) next[field] = UNCHANGED;
      setConfigDraft(next);
    } else {
      setConfigError(res.error ?? "Failed to load configuration.");
    }
    setConfigLoading(false);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await adminApi.whatsappOverview();
    if (res.ok && res.data) {
      setStats(res.data);
    } else {
      setError(res.error ?? "Failed to load WhatsApp data.");
    }
    setLoading(false);
  }, []);

  const loadMessages = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.whatsappMessages(msgPage, 20);
    if (res.ok && res.data) setMessages(res.data);
    setLoading(false);
  }, [msgPage]);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.whatsappEvents(evtPage, 20);
    if (res.ok && res.data) setEvents(res.data);
    setLoading(false);
  }, [evtPage]);

  useEffect(() => {
    if (tab === "overview") load();
    else if (tab === "messages") loadMessages();
    else if (tab === "events") loadEvents();
    else loadConfig();
  }, [tab, load, loadMessages, loadEvents, loadConfig]);

  const onTest = async () => {
    setTesting(true);
    const res = await adminApi.whatsappTest();
    setTesting(false);
    if (res.ok) {
      showToast("Connection test completed.", "success");
      load();
    } else {
      showToast(res.error ?? "Connection test failed.", "error");
    }
  };

  const onSaveConfig = async () => {
    if (!config) return;
    const payload: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(configDraft)) {
      if (key === "enabled") {
        payload[key] = value;
        continue;
      }
      if (SECRET_FIELDS.includes(key as (typeof SECRET_FIELDS)[number])) {
        if (value !== UNCHANGED) payload[key] = String(value);
        continue;
      }
      payload[key] = String(value).trim();
    }

    setConfigSaving(true);
    const res = await adminApi.whatsappUpdateConfig(payload);
    setConfigSaving(false);
    if (res.ok && res.data) {
      showToast("WhatsApp configuration saved.", "success");
      const updated = res.data;
      setConfig(updated);
      const next: Record<string, string | boolean> = {
        enabled: updated.enabled,
        phone_number_id: updated.phone_number_id ?? "",
        phone_number: updated.phone_number ?? "",
        business_account_id: updated.business_account_id ?? "",
        api_version: updated.api_version ?? "v22.0",
        graph_api_base_url: updated.graph_api_base_url ?? "",
      };
      for (const field of SECRET_FIELDS) next[field] = UNCHANGED;
      setConfigDraft(next);
    } else {
      showToast(res.error ?? "Failed to save configuration.", "error");
    }
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "messages", label: "Messages" },
    { id: "events", label: "Webhook events" },
    { id: "config", label: "Configuration" },
  ];

  const webhook = stats?.webhook ?? {};

  return (
    <>
      <AdminPageHeader
        title="WhatsApp"
        description="Delivery stats, messages, webhook health and configuration."
        actions={
          canManage && (
            <button
              type="button"
              onClick={onTest}
              disabled={testing}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center] disabled:opacity-60"
            >
              {testing ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <PlugZap className="h-4 w-4" />
              )}
              Test connection
            </button>
          )
        }
      />

      <div className="mb-6 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-2xl px-4 py-2 text-sm font-medium transition ${
              tab === t.id
                ? "bg-primary-500/10 text-primary-600 dark:text-primary-300"
                : "text-foreground/60 hover:bg-foreground/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" &&
        (loading ? (
          <LoadingState />
        ) : error || !stats ? (
          <ErrorState message={error ?? "No data."} onRetry={load} />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
              <StatCard label="Messages" value={stats.messages_total} />
              <StatCard label="Inbound" value={stats.messages_inbound} />
              <StatCard label="Outbound" value={stats.messages_outbound} />
              <StatCard label="Delivered" value={stats.messages_delivered} />
              <StatCard label="Read" value={stats.messages_read} />
              <StatCard label="Failed" value={stats.messages_failed} />
              <StatCard label="Contacts" value={stats.contacts_total} />
              <StatCard label="Events" value={stats.events_total} />
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <AdminCard title="Webhook">
                <dl className="space-y-3 text-sm">
                  {WEBHOOK_FIELDS.map((field) => {
                    const value = webhook[field];
                    return (
                      <div key={field} className="flex items-center justify-between gap-4">
                        <dt className="text-foreground/50">{field}</dt>
                        <dd className="max-w-[60%] truncate font-medium text-foreground">
                          {typeof value === "string" && value ? value : "—"}
                        </dd>
                      </div>
                    );
                  })}
                  {Object.entries(webhook)
                    .filter(([k]) => !WEBHOOK_FIELDS.includes(k))
                    .map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between gap-4">
                        <dt className="text-foreground/50">{k}</dt>
                        <dd className="font-medium text-foreground">
                          {typeof v === "boolean" ? (v ? "yes" : "no") : String(v ?? "—")}
                        </dd>
                      </div>
                    ))}
                </dl>
              </AdminCard>

              <AdminCard title="Config">
                {Object.entries(stats.config ?? {}).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between gap-4 border-b border-white/5 py-2.5 text-sm last:border-0">
                    <dt className="text-foreground/50">{k}</dt>
                    <dd className="max-w-[60%] truncate font-medium text-foreground">
                      {typeof v === "boolean" ? (v ? "yes" : "no") : String(v ?? "—")}
                    </dd>
                  </div>
                ))}
              </AdminCard>
            </div>
          </>
        ))}

      {tab === "messages" &&
        (loading ? (
          <LoadingState />
        ) : !messages || messages.items.length === 0 ? (
          <EmptyState message="No messages yet." />
        ) : (
          <AdminCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                    <th className="pb-3 pr-4 font-semibold">Contact</th>
                    <th className="pb-3 pr-4 font-semibold">Direction</th>
                    <th className="pb-3 pr-4 font-semibold">Type</th>
                    <th className="pb-3 pr-4 font-semibold">Content</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 font-semibold">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {messages.items.map((m) => (
                    <tr key={m.id}>
                      <td className="max-w-[160px] py-3 pr-4">
                        <p className="truncate text-sm font-medium text-foreground">
                          {m.contact_name || m.contact_phone || "—"}
                        </p>
                        {m.contact_phone && m.contact_name && (
                          <p className="truncate text-xs text-foreground/50">{m.contact_phone}</p>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge tone={m.direction === "inbound" ? "blue" : "purple"}>
                          {m.direction}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 text-foreground/70">{m.message_type}</td>
                      <td className="max-w-[240px] py-3 pr-4">
                        <p className="truncate text-foreground/70">
                          {m.text ?? m.media_public_id ?? "—"}
                        </p>
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={m.status} />
                        {m.error_message && (
                          <p className="mt-1 truncate text-xs text-rose-500">{m.error_message}</p>
                        )}
                      </td>
                      <td className="py-3 text-xs text-foreground/50">
                        {fmtDate(m.timestamp ?? m.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={messages.page}
              pages={messages.pages}
              total={messages.total}
              onChange={setMsgPage}
            />
          </AdminCard>
        ))}

      {tab === "events" &&
        (loading ? (
          <LoadingState />
        ) : !events || events.items.length === 0 ? (
          <EmptyState message="No webhook events yet." />
        ) : (
          <AdminCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                    <th className="pb-3 pr-4 font-semibold">Type</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Error</th>
                    <th className="pb-3 font-semibold">Received</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {events.items.map((ev) => (
                    <tr key={ev.id}>
                      <td className="py-3 pr-4">
                        <p className="font-medium text-foreground">{ev.event_type}</p>
                        <p className="text-xs text-foreground/50">{ev.object ?? "—"}</p>
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={ev.status} />
                      </td>
                      <td className="max-w-[220px] py-3 pr-4">
                        <p className="truncate text-xs text-rose-500">{ev.error ?? "—"}</p>
                      </td>
                      <td className="py-3 text-xs text-foreground/50">
                        {fmtDate(ev.received_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={events.page}
              pages={events.pages}
              total={events.total}
              onChange={setEvtPage}
            />
          </AdminCard>
        ))}

      {tab === "config" &&
        (configLoading ? (
          <LoadingState />
        ) : configError ? (
          <ErrorState message={configError} onRetry={loadConfig} />
        ) : !config ? (
          <ErrorState message="Configuration unavailable." onRetry={loadConfig} />
        ) : (
          <div className="space-y-6">
            <AdminCard title="Connection">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-foreground">WhatsApp enabled</p>
                  <p className="mt-0.5 text-xs text-foreground/45">
                    Master switch for click-to-chat HD delivery.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {config.connected ? (
                    <Badge tone="green">Connected</Badge>
                  ) : (
                    <Badge tone="amber">Not connected</Badge>
                  )}
                  <input
                    type="checkbox"
                    checked={configDraft.enabled === true}
                    disabled={!canEditConfig}
                    onChange={(e) =>
                      setConfigDraft({ ...configDraft, enabled: e.target.checked })
                    }
                    className="h-5 w-5 accent-primary-500"
                  />
                </div>
              </div>
            </AdminCard>

            <AdminCard title="Operational settings">
              <div className="grid gap-5 sm:grid-cols-2">
                {(
                  [
                    ["phone_number_id", "Phone number ID"],
                    ["phone_number", "Phone number (E.164, e.g. +15551234567)"],
                    ["business_account_id", "Business account ID"],
                    ["api_version", "Graph API version"],
                    ["graph_api_base_url", "Graph API base URL"],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key}>
                    <label
                      htmlFor={`whatsapp-${key}`}
                      className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase"
                    >
                      {label}
                    </label>
                    <input
                      id={`whatsapp-${key}`}
                      type="text"
                      disabled={!canEditConfig}
                      value={String(configDraft[key] ?? "")}
                      onChange={(e) =>
                        setConfigDraft({ ...configDraft, [key]: e.target.value })
                      }
                      className={configInputClass(!canEditConfig)}
                      spellCheck={false}
                    />
                  </div>
                ))}
              </div>
            </AdminCard>

            <AdminCard title="Credentials">
              <p className="mb-4 text-xs text-foreground/45">
                Tokens are never shown again. Leave a field untouched to keep the stored
                value.
              </p>
              <div className="grid gap-5 sm:grid-cols-3">
                {SECRET_FIELDS.map((field) => {
                  const masked =
                    field === "access_token"
                      ? config.access_token_masked
                      : field === "verify_token"
                        ? config.verify_token_masked
                        : config.app_secret_masked;
                  return (
                    <div key={field}>
                      <label
                        htmlFor={`whatsapp-${field}`}
                        className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase"
                      >
                        {field.replace(/_/g, " ")}
                      </label>
                      <input
                        id={`whatsapp-${field}`}
                        type="password"
                        disabled={!canEditCredentials}
                        placeholder={
                          configDraft[field] === UNCHANGED
                            ? masked ?? "Not configured"
                            : "Enter new value"
                        }
                        value={configDraft[field] === UNCHANGED ? "" : String(configDraft[field] ?? "")}
                        onChange={(e) =>
                          setConfigDraft({
                            ...configDraft,
                            [field]: e.target.value === "" ? UNCHANGED : e.target.value,
                          })
                        }
                        className={configInputClass(!canEditCredentials)}
                      />
                    </div>
                  );
                })}
              </div>
              {canEditConfig && (
                <div className="mt-6 flex justify-end">
                  <button
                    type="button"
                    onClick={onSaveConfig}
                    disabled={configSaving}
                    className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center] disabled:opacity-60"
                  >
                    <Save className="h-4 w-4" />
                    {configSaving ? "Saving…" : "Save configuration"}
                  </button>
                </div>
              )}
            </AdminCard>
          </div>
        ))}
    </>
  );
}
