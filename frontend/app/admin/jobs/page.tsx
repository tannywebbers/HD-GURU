"use client";

import { useCallback, useEffect, useState } from "react";
import { RotateCcw } from "lucide-react";
import { adminApi } from "@/services/admin-api";
import type { AdminJobPage } from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
  StatusBadge,
} from "@/components/admin/ui";
import { useToast } from "@/components/ToastProvider";

const STATUS_OPTIONS = ["queued", "processing", "succeeded", "failed", "dead", "cancelled"];

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

export default function AdminJobsPage() {
  const { showToast } = useToast();
  const [data, setData] = useState<AdminJobPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [retrying, setRetrying] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await adminApi.listJobs(page, 20, { status: status || undefined });
    if (res.ok && res.data) {
      setData(res.data);
    } else {
      setError(res.error ?? "Failed to load jobs.");
    }
    setLoading(false);
  }, [page, status]);

  useEffect(() => {
    load();
  }, [load]);

  const onRetry = async (jobId: string) => {
    if (!window.confirm("Re-queue this job?")) return;
    setRetrying(jobId);
    const res = await adminApi.retryJob(jobId);
    setRetrying(null);
    if (res.ok) {
      showToast("Job re-queued.", "success");
      load();
    } else {
      showToast(res.error ?? "Failed to retry job.", "error");
    }
  };

  const retryable = (status: string) =>
    status === "failed" || status === "dead" || status === "cancelled";

  return (
    <>
      <AdminPageHeader
        title="Jobs"
        description="Background processing jobs. Failed jobs can be re-queued."
      />

      <AdminCard>
        <div className="mb-5">
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className="rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 dark:bg-white/5"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} onRetry={load} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState message="No jobs found." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                    <th className="pb-3 pr-4 font-semibold">Type</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Task</th>
                    <th className="pb-3 pr-4 font-semibold">Retries</th>
                    <th className="pb-3 pr-4 font-semibold">Started</th>
                    <th className="pb-3 pr-4 font-semibold">Finished</th>
                    <th className="pb-3 font-semibold"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {data.items.map((job) => (
                    <tr key={job.id}>
                      <td className="py-3 pr-4 font-medium text-foreground">
                        {job.job_type}
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="max-w-[220px] py-3 pr-4">
                        <p className="truncate text-xs text-foreground/60">
                          {job.celery_task_id ?? "—"}
                        </p>
                        {job.worker_id && (
                          <p className="truncate text-xs text-foreground/40">
                            {job.worker_id}
                          </p>
                        )}
                      </td>
                      <td className="py-3 pr-4 tabular-nums text-foreground/70">
                        {job.retries}/{job.max_retries}
                      </td>
                      <td className="py-3 pr-4 text-xs text-foreground/50">
                        {fmtDate(job.started_at)}
                      </td>
                      <td className="py-3 pr-4 text-xs text-foreground/50">
                        {fmtDate(job.finished_at)}
                      </td>
                      <td className="py-3 text-right">
                        {retryable(job.status) && (
                          <button
                            type="button"
                            onClick={() => onRetry(job.id)}
                            disabled={retrying === job.id}
                            className="inline-flex items-center gap-1.5 rounded-xl border border-primary-500/20 px-3 py-1.5 text-xs font-medium text-primary-600 transition hover:bg-primary-500/10 disabled:opacity-50 dark:text-primary-300"
                          >
                            <RotateCcw className="h-3.5 w-3.5" />
                            Retry
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              onChange={setPage}
            />
          </>
        )}
      </AdminCard>
    </>
  );
}
