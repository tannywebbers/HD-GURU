"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi } from "@/services/admin-api";
import type { AdminAuditPage, AdminLogPage } from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  Badge,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
} from "@/components/admin/ui";

type Tab = "logs" | "audit";

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

const levelTone: Record<string, "red" | "amber" | "blue" | "gray" | "green"> = {
  ERROR: "red",
  WARNING: "amber",
  INFO: "blue",
  DEBUG: "gray",
};

export default function AdminLogsPage() {
  const [tab, setTab] = useState<Tab>("logs");
  const [logs, setLogs] = useState<AdminLogPage | null>(null);
  const [audit, setAudit] = useState<AdminAuditPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logPage, setLogPage] = useState(1);
  const [auditPage, setAuditPage] = useState(1);
  const [level, setLevel] = useState("");
  const [action, setAction] = useState("");

  const loadLogs = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.logs(logPage, 20, { level: level || undefined });
    if (res.ok && res.data) setLogs(res.data);
    else setError(res.error ?? "Failed to load logs.");
    setLoading(false);
  }, [logPage, level]);

  const loadAudit = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.auditLogs(auditPage, 20, { action: action || undefined });
    if (res.ok && res.data) setAudit(res.data);
    else setError(res.error ?? "Failed to load audit log.");
    setLoading(false);
  }, [auditPage, action]);

  useEffect(() => {
    if (tab === "logs") loadLogs();
    else loadAudit();
  }, [tab, loadLogs, loadAudit]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "logs", label: "System logs" },
    { id: "audit", label: "Audit trail" },
  ];

  return (
    <>
      <AdminPageHeader
        title="Logs & Audit"
        description="System logs and the full audit trail of administrative actions."
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

      {tab === "logs" && (
        <AdminCard
          title="System logs"
          action={
            <select
              value={level}
              onChange={(e) => {
                setLevel(e.target.value);
                setLogPage(1);
              }}
              className="rounded-2xl border border-white/10 bg-white/60 px-3 py-2 text-sm text-foreground outline-none dark:bg-white/5"
            >
              <option value="">All levels</option>
              <option value="ERROR">ERROR</option>
              <option value="WARNING">WARNING</option>
              <option value="INFO">INFO</option>
              <option value="DEBUG">DEBUG</option>
            </select>
          }
        >
          {loading ? (
            <LoadingState />
          ) : error && !logs ? (
            <ErrorState message={error} />
          ) : !logs || logs.items.length === 0 ? (
            <EmptyState message="No log entries." />
          ) : (
            <>
              <div className="divide-y divide-white/5">
                {logs.items.map((log) => (
                  <div key={log.id} className="py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Badge tone={levelTone[log.level] ?? "gray"}>{log.level}</Badge>
                        <span className="text-xs text-foreground/50">
                          {log.logger_name ?? "app"}
                        </span>
                        <span className="text-xs text-foreground/40">
                          {fmtDate(log.created_at)}
                        </span>
                      </div>
                    </div>
                    <p className="mt-1.5 font-mono text-xs break-words text-foreground/80">
                      {log.message}
                    </p>
                    {Object.keys(log.context ?? {}).length > 0 && (
                      <pre className="mt-2 overflow-x-auto rounded-xl bg-black/5 p-2 font-mono text-[11px] text-foreground/60 dark:bg-white/5">
                        {JSON.stringify(log.context, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
              <Pagination
                page={logs.page}
                pages={logs.pages}
                total={logs.total}
                onChange={setLogPage}
              />
            </>
          )}
        </AdminCard>
      )}

      {tab === "audit" && (
        <AdminCard
          title="Audit trail"
          action={
            <input
              type="search"
              value={action}
              onChange={(e) => {
                setAction(e.target.value);
                setAuditPage(1);
              }}
              placeholder="Filter by action…"
              className="rounded-2xl border border-white/10 bg-white/60 px-3 py-2 text-sm text-foreground outline-none dark:bg-white/5"
            />
          }
        >
          {loading ? (
            <LoadingState />
          ) : error && !audit ? (
            <ErrorState message={error} />
          ) : !audit || audit.items.length === 0 ? (
            <EmptyState message="No audit entries." />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                      <th className="pb-3 pr-4 font-semibold">Action</th>
                      <th className="pb-3 pr-4 font-semibold">Actor</th>
                      <th className="pb-3 pr-4 font-semibold">Resource</th>
                      <th className="pb-3 pr-4 font-semibold">Result</th>
                      <th className="pb-3 pr-4 font-semibold">IP</th>
                      <th className="pb-3 font-semibold">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {audit.items.map((entry) => (
                      <tr key={entry.id}>
                        <td className="py-3 pr-4 font-mono text-xs font-medium text-foreground">
                          {entry.action}
                        </td>
                        <td className="py-3 pr-4 text-foreground/60">
                          {entry.actor_type}
                        </td>
                        <td className="py-3 pr-4">
                          <p className="text-foreground/60">{entry.resource_type ?? "—"}</p>
                          {entry.resource_id && (
                            <p className="truncate font-mono text-xs text-foreground/40">
                              {entry.resource_id}
                            </p>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge tone={entry.result === "success" ? "green" : "red"}>
                            {entry.result}
                          </Badge>
                        </td>
                        <td className="py-3 pr-4 text-foreground/60">
                          {entry.ip_address ?? "—"}
                        </td>
                        <td className="py-3 text-xs text-foreground/50">
                          {fmtDate(entry.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={audit.page}
                pages={audit.pages}
                total={audit.total}
                onChange={setAuditPage}
              />
            </>
          )}
        </AdminCard>
      )}
    </>
  );
}
