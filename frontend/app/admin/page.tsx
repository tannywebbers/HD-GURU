"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  CloudUpload,
  Download,
  FileText,
  MessageSquare,
  Users,
} from "lucide-react";
import { adminApi } from "@/services/admin-api";
import type { DashboardResponse } from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  ErrorState,
  LoadingState,
  StatCard,
  StatusBadge,
} from "@/components/admin/ui";
import { formatBytes } from "@/lib/format";

function fmt(n: number | undefined | null): string {
  return new Intl.NumberFormat().format(n ?? 0);
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

export default function AdminDashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await adminApi.dashboard();
    if (res.ok && res.data) {
      setData(res.data);
    } else {
      setError(res.error ?? "Failed to load dashboard.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <LoadingState label="Loading dashboard…" />;
  if (error || !data) return <ErrorState message={error ?? "No data."} onRetry={load} />;

  const c = data.counters;
  const health = data.health as { status?: string };

  return (
    <>
      <AdminPageHeader
        title="Dashboard"
        description="Overview of uploads, media, delivery and system health."
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
        <StatCard label="Uploads" value={fmt(c.uploads_total)} icon={<CloudUpload className="h-5 w-5" />} hint={`${fmt(c.uploads_today)} today`} />
        <StatCard label="Media files" value={fmt(c.media_total)} icon={<FileText className="h-5 w-5" />} hint={`${fmt(c.media_completed)} completed`} />
        <StatCard label="Downloads" value={fmt(c.downloads_total)} icon={<Download className="h-5 w-5" />} />
        <StatCard label="WhatsApp" value={fmt(c.whatsapp_deliveries_total)} icon={<MessageSquare className="h-5 w-5" />} hint={`${fmt(c.whatsapp_messages_total)} messages`} />
        <StatCard label="Users" value={fmt(c.users_total)} icon={<Users className="h-5 w-5" />} />
        <StatCard label="Jobs queued" value={fmt(c.jobs_queued)} icon={<Activity className="h-5 w-5" />} hint={`${fmt(c.jobs_running)} running`} />
        <StatCard label="Jobs failed" value={fmt(c.jobs_failed)} icon={<Activity className="h-5 w-5" />} />
        <StatCard label="Errors (24h)" value={fmt(c.error_logs_24h)} icon={<Activity className="h-5 w-5" />} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <AdminCard title="Recent uploads">
          {data.recent_uploads.length === 0 ? (
            <p className="py-8 text-center text-sm text-foreground/50">No uploads yet.</p>
          ) : (
            <ul className="divide-y divide-white/5">
              {data.recent_uploads.slice(0, 6).map((row, i) => {
                const id = String(row.public_id ?? row.id ?? i);
                return (
                  <li key={id} className="flex items-center justify-between gap-4 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {String(row.original_filename ?? "Upload")}
                      </p>
                      <p className="text-xs text-foreground/50">{id}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className="text-xs text-foreground/50">
                        {fmtDate(row.created_at as string | null)}
                      </span>
                      <StatusBadge status={String(row.status ?? "unknown")} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </AdminCard>

        <AdminCard title="Recent jobs">
          {data.recent_jobs.length === 0 ? (
            <p className="py-8 text-center text-sm text-foreground/50">No jobs yet.</p>
          ) : (
            <ul className="divide-y divide-white/5">
              {data.recent_jobs.slice(0, 6).map((row, i) => {
                const id = String(row.id ?? row.celery_task_id ?? i);
                return (
                  <li key={id} className="flex items-center justify-between gap-4 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {String(row.job_type ?? "job")}
                      </p>
                      <p className="text-xs text-foreground/50">
                        {row.celery_task_id ? String(row.celery_task_id) : id}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className="text-xs text-foreground/50">
                        {fmtDate(row.created_at as string | null)}
                      </span>
                      <StatusBadge status={String(row.status ?? "unknown")} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </AdminCard>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <AdminCard title="Storage">
          <dl className="space-y-3 text-sm">
            {[
              ["Provider", String(data.storage.provider ?? "—")],
              ["Driver", String(data.storage.driver ?? "—")],
              ["Objects", fmt(Number(data.storage.objects ?? 0))],
              [
                "Used",
                data.storage.used_bytes != null
                  ? formatBytes(Number(data.storage.used_bytes))
                  : "—",
              ],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between gap-4">
                <dt className="text-foreground/50">{k}</dt>
                <dd className="font-medium text-foreground">{v}</dd>
              </div>
            ))}
          </dl>
        </AdminCard>

        <AdminCard title="System">
          <dl className="space-y-3 text-sm">
            {[
              ["Status", <StatusBadge key="s" status={String(health.status ?? "unknown")} />],
              ["Version", String(data.system.version ?? "—")],
              ["Environment", String(data.system.environment ?? "—")],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex items-center justify-between gap-4">
                <dt className="text-foreground/50">{String(k)}</dt>
                <dd className="font-medium text-foreground">{v}</dd>
              </div>
            ))}
          </dl>
        </AdminCard>
      </div>
    </>
  );
}
