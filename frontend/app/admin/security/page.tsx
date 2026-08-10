"use client";

import { useCallback, useEffect, useState } from "react";
import { ShieldX } from "lucide-react";
import { adminApi } from "@/services/admin-api";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type {
  AdminApiKeyItem,
  AdminLoginHistoryPage,
  SecurityOverview,
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
} from "@/components/admin/ui";
import { useToast } from "@/components/ToastProvider";

type Tab = "overview" | "history" | "keys";

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

export default function AdminSecurityPage() {
  const { showToast } = useToast();
  const { hasPermission } = useAdminAuth();
  const canManage = hasPermission("security.manage");

  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<SecurityOverview | null>(null);
  const [history, setHistory] = useState<AdminLoginHistoryPage | null>(null);
  const [keys, setKeys] = useState<AdminApiKeyItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [success, setSuccess] = useState<string>("");

  const loadOverview = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.securityOverview();
    if (res.ok && res.data) {
      setOverview(res.data);
      setError(null);
    } else {
      setError(res.error ?? "Failed to load security overview.");
    }
    setLoading(false);
  }, []);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.loginHistory(page, 20, {
      success: success === "" ? undefined : success === "true",
    });
    if (res.ok && res.data) setHistory(res.data);
    setLoading(false);
  }, [page, success]);

  const loadKeys = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.apiKeys();
    if (res.ok && res.data) setKeys(res.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (tab === "overview") loadOverview();
    else if (tab === "history") loadHistory();
    else loadKeys();
  }, [tab, loadOverview, loadHistory, loadKeys]);

  const onRevoke = async (key: AdminApiKeyItem) => {
    if (!window.confirm(`Revoke API key "${key.name}"?`)) return;
    const res = await adminApi.revokeApiKey(key.id);
    if (res.ok) {
      showToast("API key revoked.", "success");
      loadKeys();
    } else {
      showToast(res.error ?? "Failed to revoke key.", "error");
    }
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "history", label: "Login history" },
    { id: "keys", label: "API keys" },
  ];

  return (
    <>
      <AdminPageHeader
        title="Security"
        description="Account lockouts, login attempts and API key management."
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
        ) : !overview ? (
          <ErrorState message={error ?? "No data."} onRetry={loadOverview} />
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
            <StatCard label="Users" value={overview.users_total} />
            <StatCard label="Locked accounts" value={overview.locked_accounts} />
            <StatCard label="Active API keys" value={overview.active_api_keys} />
            <StatCard label="Failed logins (24h)" value={overview.failed_logins_24h} />
            <StatCard label="Recent sessions" value={overview.recent_sessions} />
          </div>
        ))}

      {tab === "history" && (
        <AdminCard>
          <div className="mb-5">
            <select
              value={success}
              onChange={(e) => {
                setSuccess(e.target.value);
                setPage(1);
              }}
              className="rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 dark:bg-white/5"
            >
              <option value="">All attempts</option>
              <option value="true">Successful</option>
              <option value="false">Failed</option>
            </select>
          </div>
          {loading ? (
            <LoadingState />
          ) : !history || history.items.length === 0 ? (
            <EmptyState message="No login attempts recorded." />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                      <th className="pb-3 pr-4 font-semibold">Email</th>
                      <th className="pb-3 pr-4 font-semibold">Result</th>
                      <th className="pb-3 pr-4 font-semibold">Reason</th>
                      <th className="pb-3 pr-4 font-semibold">IP</th>
                      <th className="pb-3 font-semibold">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {history.items.map((h) => (
                      <tr key={h.id}>
                        <td className="py-3 pr-4 font-medium text-foreground">{h.email}</td>
                        <td className="py-3 pr-4">
                          <Badge tone={h.success ? "green" : "red"}>
                            {h.success ? "success" : "failed"}
                          </Badge>
                        </td>
                        <td className="py-3 pr-4 text-foreground/60">
                          {h.failure_reason ?? "—"}
                        </td>
                        <td className="py-3 pr-4 text-foreground/60">{h.ip_address ?? "—"}</td>
                        <td className="py-3 text-xs text-foreground/50">
                          {fmtDate(h.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={history.page}
                pages={history.pages}
                total={history.total}
                onChange={setPage}
              />
            </>
          )}
        </AdminCard>
      )}

      {tab === "keys" &&
        (loading ? (
          <LoadingState />
        ) : !keys || keys.length === 0 ? (
          <EmptyState message="No API keys found." />
        ) : (
          <AdminCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                    <th className="pb-3 pr-4 font-semibold">Name</th>
                    <th className="pb-3 pr-4 font-semibold">Owner</th>
                    <th className="pb-3 pr-4 font-semibold">Key</th>
                    <th className="pb-3 pr-4 font-semibold">Scopes</th>
                    <th className="pb-3 pr-4 font-semibold">Last used</th>
                    <th className="pb-3 font-semibold"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {keys.map((key) => (
                    <tr key={key.id}>
                      <td className="py-3 pr-4">
                        <p className="font-medium text-foreground">{key.name}</p>
                        <Badge tone={key.is_active ? "green" : "red"} className="mt-1">
                          {key.is_active ? "active" : "revoked"}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 text-foreground/60">{key.user_email ?? "—"}</td>
                      <td className="py-3 pr-4 font-mono text-xs text-foreground/60">
                        {key.key_prefix}…
                      </td>
                      <td className="py-3 pr-4 text-xs text-foreground/60">
                        {(key.scopes ?? []).join(", ") || "—"}
                      </td>
                      <td className="py-3 pr-4 text-xs text-foreground/50">
                        {fmtDate(key.last_used_at)}
                      </td>
                      <td className="py-3 text-right">
                        {canManage && key.is_active && (
                          <button
                            type="button"
                            onClick={() => onRevoke(key)}
                            className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/20 px-3 py-1.5 text-xs font-medium text-rose-500 transition hover:bg-rose-500/10"
                          >
                            <ShieldX className="h-3.5 w-3.5" />
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </AdminCard>
        ))}
    </>
  );
}
