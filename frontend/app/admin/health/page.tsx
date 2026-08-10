"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi } from "@/services/admin-api";
import type { AdminHealthResponse } from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  Badge,
  ErrorState,
  LoadingState,
  StatCard,
} from "@/components/admin/ui";

function toneFor(status: string): "green" | "red" | "amber" | "gray" {
  if (status === "ok") return "green";
  if (status === "error" || status === "unavailable") return "red";
  if (status === "degraded") return "amber";
  return "gray";
}

function fmtUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function AdminHealthPage() {
  const [data, setData] = useState<AdminHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await adminApi.health();
    if (res.ok && res.data) setData(res.data);
    else setError(res.error ?? "Failed to load health status.");
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, [load]);

  if (loading && !data) return <LoadingState label="Checking health…" />;
  if (error && !data) return <ErrorState message={error} onRetry={load} />;
  if (!data) return null;

  const components = data.components ?? {};

  return (
    <>
      <AdminPageHeader
        title="Health"
        description="Live status of the backend services. Refreshes every 30 seconds."
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          label="Status"
          value={
            <span className="inline-flex items-center gap-2">
              <Badge tone={toneFor(data.status)}>{data.status}</Badge>
            </span>
          }
        />
        <StatCard label="Version" value={data.version} />
        <StatCard label="Environment" value={data.environment} />
        <StatCard label="Uptime" value={fmtUptime(data.uptime_seconds)} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <AdminCard title="Components">
          <dl className="space-y-3">
            {Object.entries(components).map(([name, info]) => {
              const state = info as Record<string, unknown>;
              const status = String(state.status ?? "unknown");
              return (
                <div key={name} className="flex items-center justify-between gap-4">
                  <dt className="text-sm text-foreground/60">{name}</dt>
                  <dd className="flex items-center gap-3">
                    <span className="text-xs text-foreground/40">
                      {Object.entries(state)
                        .filter(([k]) => k !== "status")
                        .map(([k, v]) => `${k}: ${String(v)}`)
                        .join(" · ")}
                    </span>
                    <Badge tone={toneFor(status)}>{status}</Badge>
                  </dd>
                </div>
              );
            })}
          </dl>
        </AdminCard>

        <AdminCard title="Workers">
          {data.workers.length === 0 ? (
            <p className="py-8 text-center text-sm text-foreground/50">
              No workers registered.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                    <th className="pb-3 pr-4 font-semibold">Worker</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Heartbeat</th>
                    <th className="pb-3 font-semibold">Tasks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {data.workers.map((worker, i) => {
                    const w = worker as Record<string, unknown>;
                    const status = String(w.status ?? "unknown");
                    return (
                      <tr key={String(w.id ?? i)}>
                        <td className="py-3 pr-4 font-medium text-foreground">
                          {String(w.id ?? "worker")}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge tone={toneFor(status)}>{status}</Badge>
                        </td>
                        <td className="py-3 pr-4 text-xs text-foreground/50">
                          {w.last_heartbeat
                            ? fmtDate(String(w.last_heartbeat))
                            : "—"}
                        </td>
                        <td className="py-3 tabular-nums text-foreground/70">
                          {w.current_tasks != null ? String(w.current_tasks) : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </AdminCard>
      </div>
    </>
  );
}
