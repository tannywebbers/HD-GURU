"use client";

import { useCallback, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { adminApi } from "@/services/admin-api";
import type { AdminMediaItem, AdminMediaPage } from "@/types/admin";
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
import { formatBytes } from "@/lib/format";

const STATUS_OPTIONS = [
  "queued",
  "analyzing",
  "enhancing",
  "watermarking",
  "compressing",
  "storing",
  "completed",
  "failed",
  "expired",
];

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

export default function AdminMediaPage() {
  const { showToast } = useToast();
  const [data, setData] = useState<AdminMediaPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await adminApi.listMedia(page, 20, {
      status: status || undefined,
      search: search || undefined,
    });
    if (res.ok && res.data) {
      setData(res.data);
    } else {
      setError(res.error ?? "Failed to load media.");
    }
    setLoading(false);
  }, [page, status, search]);

  useEffect(() => {
    load();
  }, [load]);

  const onDelete = async (item: AdminMediaItem) => {
    if (!window.confirm(`Delete "${item.original_filename}"? This cannot be undone.`)) return;
    setDeleting(item.public_id);
    const res = await adminApi.deleteMedia(item.public_id);
    setDeleting(null);
    if (res.ok) {
      showToast("Media deleted.", "success");
      load();
    } else {
      showToast(res.error ?? "Failed to delete media.", "error");
    }
  };

  return (
    <>
      <AdminPageHeader
        title="Media"
        description="All uploaded media files with processing status and delivery counters."
      />

      <AdminCard>
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            type="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by filename or public id…"
            className="w-full rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 focus:ring-2 focus:ring-primary-500/30 sm:max-w-xs dark:bg-white/5"
          />
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
          <EmptyState message="No media found." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                    <th className="pb-3 pr-4 font-semibold">File</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Size</th>
                    <th className="pb-3 pr-4 font-semibold">Dimensions</th>
                    <th className="pb-3 pr-4 font-semibold">Downloads</th>
                    <th className="pb-3 pr-4 font-semibold">WhatsApp</th>
                    <th className="pb-3 pr-4 font-semibold">Created</th>
                    <th className="pb-3 font-semibold"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {data.items.map((item) => (
                    <tr key={item.id}>
                      <td className="max-w-xs py-3 pr-4">
                        <p className="truncate font-medium text-foreground">
                          {item.original_filename}
                        </p>
                        <p className="truncate text-xs text-foreground/50">
                          {item.public_id}
                        </p>
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={item.status} />
                        {item.error && (
                          <p className="mt-1 max-w-[180px] truncate text-xs text-rose-500">
                            {item.error}
                          </p>
                        )}
                      </td>
                      <td className="py-3 pr-4 tabular-nums text-foreground/70">
                        {formatBytes(item.file_size)}
                      </td>
                      <td className="py-3 pr-4 text-foreground/70">
                        {item.width && item.height
                          ? `${item.width}×${item.height}`
                          : "—"}
                      </td>
                      <td className="py-3 pr-4 tabular-nums text-foreground/70">
                        {item.download_count}
                      </td>
                      <td className="py-3 pr-4 tabular-nums text-foreground/70">
                        {item.whatsapp_delivery_count}
                      </td>
                      <td className="py-3 pr-4 text-xs text-foreground/50">
                        {fmtDate(item.created_at)}
                      </td>
                      <td className="py-3 text-right">
                        <button
                          type="button"
                          onClick={() => onDelete(item)}
                          disabled={deleting === item.public_id}
                          className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/20 px-3 py-1.5 text-xs font-medium text-rose-500 transition hover:bg-rose-500/10 disabled:opacity-50"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </button>
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
