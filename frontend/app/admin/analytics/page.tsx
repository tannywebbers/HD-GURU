"use client";

import { useCallback, useEffect, useState } from "react";
import { BarChart3, RefreshCw, Trash2 } from "lucide-react";
import { adminApi } from "@/services/admin-api";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type {
  AnalyticsEventPage,
  AnalyticsOverview,
  AnalyticsTimeseries,
  AnalyticsTopList,
} from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
  StatCard,
} from "@/components/admin/ui";
import { useToast } from "@/components/ToastProvider";

type Tab = "overview" | "top" | "events";

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

export default function AdminAnalyticsPage() {
  const { showToast } = useToast();
  const { hasPermission } = useAdminAuth();
  const canManage = hasPermission("ads.manage");

  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [series, setSeries] = useState<AnalyticsTimeseries | null>(null);
  const [topPages, setTopPages] = useState<AnalyticsTopList | null>(null);
  const [devices, setDevices] = useState<AnalyticsTopList | null>(null);
  const [referrers, setReferrers] = useState<AnalyticsTopList | null>(null);
  const [dimension, setDimension] = useState<"device" | "browser" | "os">("device");
  const [events, setEvents] = useState<AnalyticsEventPage | null>(null);
  const [eventFilter, setEventFilter] = useState("");
  const [eventPage, setEventPage] = useState(1);
  const [runningRetention, setRunningRetention] = useState(false);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [overviewRes, seriesRes, pagesRes, devicesRes, referrersRes] =
      await Promise.all([
        adminApi.analyticsOverview(30),
        adminApi.analyticsTimeseries(30),
        adminApi.analyticsTopPages(30, 10),
        adminApi.analyticsDevices("device", 30, 10),
        adminApi.analyticsReferrers(30, 10),
      ]);
    if (overviewRes.ok && overviewRes.data) setOverview(overviewRes.data);
    if (seriesRes.ok && seriesRes.data) setSeries(seriesRes.data);
    if (pagesRes.ok && pagesRes.data) setTopPages(pagesRes.data);
    if (devicesRes.ok && devicesRes.data) setDevices(devicesRes.data);
    if (referrersRes.ok && referrersRes.data) setReferrers(referrersRes.data);
    if (
      !overviewRes.ok &&
      !seriesRes.ok &&
      !pagesRes.ok &&
      !devicesRes.ok &&
      !referrersRes.ok
    ) {
      setError(overviewRes.error ?? "Failed to load analytics.");
    }
    setLoading(false);
  }, []);

  const loadDevices = useCallback(async () => {
    const res = await adminApi.analyticsDevices(dimension, 30, 10);
    if (res.ok && res.data) setDevices(res.data);
  }, [dimension]);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.analyticsEvents(eventPage, 20, {
      event: eventFilter || undefined,
    });
    if (res.ok && res.data) setEvents(res.data);
    setLoading(false);
  }, [eventPage, eventFilter]);

  useEffect(() => {
    if (tab === "overview") void loadOverview();
    else if (tab === "top") {
      void loadOverview();
      void loadDevices();
    } else void loadEvents();
  }, [tab, loadOverview, loadDevices, loadEvents]);

  const onRunRetention = async () => {
    if (!window.confirm("Purge raw events older than the retention window?")) return;
    setRunningRetention(true);
    const res = await adminApi.runAnalyticsRetention();
    setRunningRetention(false);
    if (res.ok && res.data) {
      showToast(
        `Purged ${res.data.analytics_events_deleted} events and ${res.data.ad_events_deleted} ad events.`,
        "success",
      );
    } else {
      showToast(res.error ?? "Could not run retention.", "error");
    }
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "top", label: "Top lists" },
    { id: "events", label: "Events" },
  ];

  return (
    <>
      <AdminPageHeader
        title="Analytics"
        description="Traffic, upload funnel, WhatsApp delivery and ad performance."
        actions={
          canManage && (
            <button
              type="button"
              onClick={onRunRetention}
              disabled={runningRetention}
              className="inline-flex items-center gap-2 rounded-2xl border border-foreground/10 px-5 py-2.5 text-sm font-semibold text-foreground/80 transition hover:bg-foreground/5 disabled:opacity-60"
            >
              {runningRetention ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Run retention
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
        ) : error || !overview ? (
          <ErrorState message={error ?? "No data."} onRetry={loadOverview} />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
              <StatCard label="Visitors (30d)" value={overview.visitors} />
              <StatCard label="Page views" value={overview.page_views} />
              <StatCard label="Uploads" value={overview.uploads} />
              <StatCard label="Uploads completed" value={overview.uploads_completed} />
              <StatCard label="Processing rate" value={overview.processing_rate != null ? `${overview.processing_rate}%` : "—"} />
              <StatCard label="GET HD clicks" value={overview.get_hd_clicks} />
              <StatCard label="WhatsApp opens" value={overview.whatsapp_opens} />
              <StatCard label="WhatsApp requests" value={overview.whatsapp_requests} />
              <StatCard label="Media deliveries" value={overview.media_deliveries} />
              <StatCard label="Errors" value={overview.errors} />
              <StatCard label="Ad impressions" value={overview.ad_impressions} />
              <StatCard label="Ad clicks" value={overview.ad_clicks} />
            </div>

            <AdminCard className="mt-6" title="Daily timeseries">
              {series && series.points.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                        <th className="pb-3 pr-4 font-semibold">Date</th>
                        <th className="pb-3 pr-4 font-semibold">Visitors</th>
                        <th className="pb-3 pr-4 font-semibold">Page views</th>
                        <th className="pb-3 pr-4 font-semibold">Uploads</th>
                        <th className="pb-3 pr-4 font-semibold">GET HD</th>
                        <th className="pb-3 pr-4 font-semibold">Deliveries</th>
                        <th className="pb-3 font-semibold">Errors</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {series.points.map((p) => (
                        <tr key={p.date}>
                          <td className="py-2.5 pr-4 font-medium text-foreground">{p.date}</td>
                          <td className="py-2.5 pr-4 text-foreground/80">{p.visitors}</td>
                          <td className="py-2.5 pr-4 text-foreground/80">{p.page_views}</td>
                          <td className="py-2.5 pr-4 text-foreground/80">{p.uploads}</td>
                          <td className="py-2.5 pr-4 text-foreground/80">{p.get_hd_clicks}</td>
                          <td className="py-2.5 pr-4 text-foreground/80">{p.media_deliveries}</td>
                          <td className="py-2.5 text-foreground/80">{p.errors}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState message="No data for the last 30 days yet." />
              )}
            </AdminCard>
          </>
        ))}

      {tab === "top" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <AdminCard title="Top pages">
            {topPages && topPages.items.length > 0 ? (
              <ul className="space-y-2">
                {topPages.items.map((item) => (
                  <li key={item.key} className="flex items-center justify-between gap-4 text-sm">
                    <span className="truncate font-medium text-foreground">{item.key}</span>
                    <span className="shrink-0 text-foreground/60">{item.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState message="No pages yet." />
            )}
          </AdminCard>

          <AdminCard
            title={`By ${dimension}`}
            action={
              <div className="flex gap-2">
                {(["device", "browser", "os"] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDimension(d)}
                    className={`rounded-xl px-3 py-1.5 text-xs font-medium transition ${
                      dimension === d
                        ? "bg-primary-500/10 text-primary-600 dark:text-primary-300"
                        : "text-foreground/60 hover:bg-foreground/5"
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            }
          >
            {devices && devices.items.length > 0 ? (
              <ul className="space-y-2">
                {devices.items.map((item) => (
                  <li key={item.key} className="flex items-center justify-between gap-4 text-sm">
                    <span className="truncate font-medium text-foreground">{item.key}</span>
                    <span className="shrink-0 text-foreground/60">{item.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState message="No data yet." />
            )}
          </AdminCard>

          <AdminCard title="Referrers">
            {referrers && referrers.items.length > 0 ? (
              <ul className="space-y-2">
                {referrers.items.map((item) => (
                  <li key={item.key} className="flex items-center justify-between gap-4 text-sm">
                    <span className="truncate font-medium text-foreground">{item.key}</span>
                    <span className="shrink-0 text-foreground/60">{item.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState message="No referrers yet." />
            )}
          </AdminCard>
        </div>
      )}

      {tab === "events" && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <input
              value={eventFilter}
              onChange={(e) => {
                setEventFilter(e.target.value);
                setEventPage(1);
              }}
              placeholder="Filter by event…"
              className="w-64 rounded-xl border border-foreground/10 bg-background/60 px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/20"
            />
            <button
              type="button"
              onClick={() => void loadEvents()}
              className="inline-flex items-center gap-1.5 rounded-xl border border-foreground/10 px-3 py-2 text-xs font-medium text-foreground/70 transition hover:bg-foreground/5"
            >
              <BarChart3 className="h-3.5 w-3.5" /> Apply
            </button>
          </div>

          {loading ? (
            <LoadingState />
          ) : !events || events.items.length === 0 ? (
            <EmptyState message="No events recorded yet." />
          ) : (
            <AdminCard>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                      <th className="pb-3 pr-4 font-semibold">Event</th>
                      <th className="pb-3 pr-4 font-semibold">Page</th>
                      <th className="pb-3 pr-4 font-semibold">Device</th>
                      <th className="pb-3 pr-4 font-semibold">Country</th>
                      <th className="pb-3 pr-4 font-semibold">Referrer</th>
                      <th className="pb-3 font-semibold">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {events.items.map((ev) => (
                      <tr key={ev.id}>
                        <td className="py-3 pr-4">
                          <span className="font-mono text-xs text-primary-600 dark:text-primary-300">
                            {ev.event_type}
                          </span>
                        </td>
                        <td className="max-w-[180px] truncate py-3 pr-4 text-foreground/70">
                          {ev.page ?? "—"}
                        </td>
                        <td className="py-3 pr-4 text-foreground/70">
                          {ev.browser ?? "—"} · {ev.os ?? "—"}
                        </td>
                        <td className="py-3 pr-4 text-foreground/70">{ev.country ?? "—"}</td>
                        <td className="py-3 pr-4 text-foreground/70">
                          {ev.referrer_category ?? "—"}
                        </td>
                        <td className="py-3 text-xs text-foreground/50">
                          {fmtDate(ev.created_at)}
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
                onChange={setEventPage}
              />
            </AdminCard>
          )}
        </>
      )}
    </>
  );
}
