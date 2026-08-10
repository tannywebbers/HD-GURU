"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpDown,
  Megaphone,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { adminApi } from "@/services/admin-api";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type {
  AdAnalyticsResponse,
  AdPlacementItem,
  AdProviderItem,
  AdsOverview,
} from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  Badge,
  EmptyState,
  ErrorState,
  LoadingState,
  StatCard,
} from "@/components/admin/ui";
import { useToast } from "@/components/ToastProvider";

type Tab = "overview" | "providers" | "placements" | "analytics";

const PROVIDER_TYPES = [
  "script",
  "iframe",
  "html",
  "javascript",
  "native",
  "banner",
  "custom",
];
const FREQUENCIES = [
  "every_page",
  "every_session",
  "once_per_session",
  "interval",
];

interface ProviderDraft {
  id?: string;
  name: string;
  provider_type: string;
  base_url: string;
  publisher_id: string;
  zone_id: string;
  site_id: string;
  custom_script: string;
  click_through_url: string;
  enabled: boolean;
}

interface SlotDraft {
  provider_id: string;
  priority: number;
  frequency: string;
  enabled: boolean;
}

interface PlacementDraft {
  id?: string;
  name: string;
  label: string;
  enabled: boolean;
  width: string;
  height: string;
  responsive: boolean;
  behavior: "lazy" | "eager";
  slots: SlotDraft[];
}

const EMPTY_PROVIDER: ProviderDraft = {
  name: "",
  provider_type: "script",
  base_url: "",
  publisher_id: "",
  zone_id: "",
  site_id: "",
  custom_script: "",
  click_through_url: "",
  enabled: false,
};

const EMPTY_PLACEMENT: PlacementDraft = {
  name: "",
  label: "",
  enabled: true,
  width: "",
  height: "",
  responsive: true,
  behavior: "lazy",
  slots: [],
};

export default function AdminAdsPage() {
  const { showToast } = useToast();
  const { hasPermission } = useAdminAuth();
  const canManage = hasPermission("ads.manage");

  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<AdsOverview | null>(null);
  const [providers, setProviders] = useState<AdProviderItem[]>([]);
  const [placements, setPlacements] = useState<AdPlacementItem[]>([]);
  const [adAnalytics, setAdAnalytics] = useState<AdAnalyticsResponse | null>(null);
  const [analyticsGroup, setAnalyticsGroup] = useState<"provider" | "placement" | "day">("provider");

  const [providerDraft, setProviderDraft] = useState<ProviderDraft | null>(null);
  const [placementDraft, setPlacementDraft] = useState<PlacementDraft | null>(null);
  const [saving, setSaving] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [overviewRes, providersRes, placementsRes] = await Promise.all([
      adminApi.adsOverview(),
      adminApi.listAdProviders(),
      adminApi.listAdPlacements(),
    ]);
    if (overviewRes.ok && overviewRes.data) setOverview(overviewRes.data);
    if (providersRes.ok && providersRes.data) setProviders(providersRes.data);
    if (placementsRes.ok && placementsRes.data) setPlacements(placementsRes.data);
    if (!overviewRes.ok && !providersRes.ok && !placementsRes.ok) {
      setError(overviewRes.error ?? "Failed to load ads data.");
    }
    setLoading(false);
  }, []);

  const loadAnalytics = useCallback(async () => {
    const res = await adminApi.adAnalytics(30, analyticsGroup);
    if (res.ok && res.data) setAdAnalytics(res.data);
  }, [analyticsGroup]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (tab === "analytics") void loadAnalytics();
  }, [tab, loadAnalytics]);

  const toggleAdsEnabled = async () => {
    if (!overview) return;
    const next = !overview.enabled;
    const res = await adminApi.updateSettings([{ key: "ads.enabled", value: next }]);
    if (res.ok) {
      showToast(`Ads ${next ? "enabled" : "disabled"}.`, "success");
      void loadAll();
    } else {
      showToast(res.error ?? "Could not toggle ads.", "error");
    }
  };

  const onSaveProvider = async () => {
    if (!providerDraft) return;
    if (!providerDraft.name.trim()) {
      showToast("Provider name is required.", "error");
      return;
    }
    setSaving(true);
    const payload = {
      name: providerDraft.name.trim(),
      provider_type: providerDraft.provider_type as AdProviderItem["provider_type"],
      base_url: providerDraft.base_url || null,
      publisher_id: providerDraft.publisher_id || null,
      zone_id: providerDraft.zone_id || null,
      site_id: providerDraft.site_id || null,
      custom_script: providerDraft.custom_script || null,
      click_through_url: providerDraft.click_through_url || null,
      enabled: providerDraft.enabled,
    };
    const res = providerDraft.id
      ? await adminApi.updateAdProvider(providerDraft.id, payload)
      : await adminApi.createAdProvider(payload);
    setSaving(false);
    if (res.ok && res.data) {
      showToast("Provider saved.", "success");
      setProviderDraft(null);
      void loadAll();
    } else {
      showToast(res.error ?? "Could not save provider.", "error");
    }
  };

  const onTestProvider = async (id: string) => {
    const res = await adminApi.testAdProvider(id);
    if (res.ok && res.data) {
      if (res.data.ok) {
        showToast("Configuration looks good.", "success");
      } else {
        showToast(`Missing: ${res.data.missing.join(", ") || "unknown"}.`, "error");
      }
    } else {
      showToast(res.error ?? "Test failed.", "error");
    }
  };

  const onDeleteProvider = async (id: string, name: string) => {
    if (!window.confirm(`Delete provider "${name}"?`)) return;
    const res = await adminApi.deleteAdProvider(id);
    if (res.ok) {
      showToast("Provider deleted.", "success");
      void loadAll();
    } else {
      showToast(res.error ?? "Could not delete provider.", "error");
    }
  };

  const onSavePlacement = async () => {
    if (!placementDraft) return;
    if (!placementDraft.name.trim() || !placementDraft.label.trim()) {
      showToast("Placement name and label are required.", "error");
      return;
    }
    setSaving(true);
    const slots = placementDraft.slots
      .filter((s) => s.provider_id)
      .map((s) => ({
        provider_id: s.provider_id,
        priority: s.priority,
        frequency: s.frequency,
        enabled: s.enabled,
      }));
    const payload = {
      name: placementDraft.name.trim(),
      label: placementDraft.label.trim(),
      enabled: placementDraft.enabled,
      width: placementDraft.width ? Number(placementDraft.width) : null,
      height: placementDraft.height ? Number(placementDraft.height) : null,
      responsive: placementDraft.responsive,
      behavior: placementDraft.behavior,
      slots,
    };
    const res = placementDraft.id
      ? await adminApi.updateAdPlacement(placementDraft.id, {
          label: payload.label,
          enabled: payload.enabled,
          width: payload.width,
          height: payload.height,
          responsive: payload.responsive,
          behavior: payload.behavior,
        })
      : await adminApi.createAdPlacement(payload);
    setSaving(false);
    if (res.ok && res.data) {
      if (placementDraft.id) {
        await adminApi.replaceAdPlacementSlots(placementDraft.id, slots);
      }
      showToast("Placement saved.", "success");
      setPlacementDraft(null);
      void loadAll();
    } else {
      showToast(res.error ?? "Could not save placement.", "error");
    }
  };

  const onDeletePlacement = async (id: string, name: string) => {
    if (!window.confirm(`Delete placement "${name}"?`)) return;
    const res = await adminApi.deleteAdPlacement(id);
    if (res.ok) {
      showToast("Placement deleted.", "success");
      void loadAll();
    } else {
      showToast(res.error ?? "Could not delete placement.", "error");
    }
  };

  const moveSlot = (index: number, direction: -1 | 1) => {
    if (!placementDraft) return;
    const slots = [...placementDraft.slots];
    const target = index + direction;
    if (target < 0 || target >= slots.length) return;
    [slots[index], slots[target]] = [slots[target], slots[index]];
    setPlacementDraft({
      ...placementDraft,
      slots: slots.map((s, i) => ({ ...s, priority: i + 1 })),
    });
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "providers", label: "Providers" },
    { id: "placements", label: "Placements" },
    { id: "analytics", label: "Analytics" },
  ];

  return (
    <>
      <AdminPageHeader
        title="Ads & Monetization"
        description="Configure ad providers, placements and track monetization performance."
        actions={
          overview && (
            <button
              type="button"
              onClick={toggleAdsEnabled}
              className="inline-flex items-center gap-2 rounded-2xl border border-foreground/10 px-5 py-2.5 text-sm font-semibold text-foreground/80 transition hover:bg-foreground/5"
            >
              <Megaphone className="h-4 w-4" />
              {overview.enabled ? "Ads enabled" : "Ads disabled"}
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
          <ErrorState message={error ?? "No data."} onRetry={loadAll} />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
              <StatCard label="Providers" value={overview.providers_total} />
              <StatCard label="Providers enabled" value={overview.providers_enabled} />
              <StatCard label="Placements" value={overview.placements_total} />
              <StatCard label="Placements enabled" value={overview.placements_enabled} />
              <StatCard label="Active slots" value={overview.active_slots} />
              <StatCard label="Impressions" value={overview.impressions} />
              <StatCard label="Clicks" value={overview.clicks} />
              <StatCard label="CTR" value={`${overview.ctr}%`} />
              <StatCard label="Load failures" value={overview.load_failures} />
              <StatCard label="Today impressions" value={overview.impressions_today} />
              <StatCard label="Today clicks" value={overview.clicks_today} />
              <StatCard label="Default behavior" value={overview.default_behavior} />
            </div>

            <AdminCard className="mt-6" title="Providers">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                      <th className="pb-3 pr-4 font-semibold">Name</th>
                      <th className="pb-3 pr-4 font-semibold">Type</th>
                      <th className="pb-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {overview.providers.map((p) => (
                      <tr key={p.id}>
                        <td className="py-3 pr-4 font-medium text-foreground">{p.name}</td>
                        <td className="py-3 pr-4 text-foreground/70">{p.provider_type}</td>
                        <td className="py-3">
                          <Badge tone={p.enabled ? "green" : "gray"}>
                            {p.enabled ? "enabled" : "disabled"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AdminCard>
          </>
        ))}

      {tab === "providers" && (
        <>
          <div className="mb-4 flex justify-end">
            {canManage && (
              <button
                type="button"
                onClick={() => setProviderDraft({ ...EMPTY_PROVIDER })}
                className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center]"
              >
                <Plus className="h-4 w-4" /> Add provider
              </button>
            )}
          </div>

          {providerDraft && (
            <ProviderForm
              draft={providerDraft}
              saving={saving}
              onChange={setProviderDraft}
              onSave={onSaveProvider}
              onCancel={() => setProviderDraft(null)}
            />
          )}

          <AdminCard>
            {loading ? (
              <LoadingState />
            ) : providers.length === 0 ? (
              <EmptyState message="No providers yet." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                      <th className="pb-3 pr-4 font-semibold">Name</th>
                      <th className="pb-3 pr-4 font-semibold">Type</th>
                      <th className="pb-3 pr-4 font-semibold">Ids</th>
                      <th className="pb-3 pr-4 font-semibold">Status</th>
                      <th className="pb-3 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {providers.map((p) => (
                      <tr key={p.id}>
                        <td className="py-3 pr-4 font-medium text-foreground">{p.name}</td>
                        <td className="py-3 pr-4 text-foreground/70">{p.provider_type}</td>
                        <td className="py-3 pr-4 text-xs text-foreground/50">
                          {p.publisher_id || "—"} / {p.zone_id || "—"} / {p.site_id || "—"}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge tone={p.enabled ? "green" : "gray"}>
                            {p.enabled ? "enabled" : "disabled"}
                          </Badge>
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            {canManage && (
                              <>
                                <button
                                  type="button"
                                  onClick={() =>
                                    setProviderDraft({
                                      id: p.id,
                                      name: p.name,
                                      provider_type: p.provider_type,
                                      base_url: p.base_url ?? "",
                                      publisher_id: p.publisher_id ?? "",
                                      zone_id: p.zone_id ?? "",
                                      site_id: p.site_id ?? "",
                                      custom_script: p.custom_script ?? "",
                                      click_through_url: p.click_through_url ?? "",
                                      enabled: p.enabled,
                                    })
                                  }
                                  className="rounded-xl border border-foreground/10 px-3 py-1.5 text-xs font-medium text-foreground/70 transition hover:bg-foreground/5"
                                >
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  onClick={() => onTestProvider(p.id)}
                                  className="rounded-xl border border-foreground/10 px-3 py-1.5 text-xs font-medium text-foreground/70 transition hover:bg-foreground/5"
                                >
                                  Test
                                </button>
                                <button
                                  type="button"
                                  onClick={() => onDeleteProvider(p.id, p.name)}
                                  className="rounded-xl border border-rose-500/20 px-3 py-1.5 text-xs font-medium text-rose-500 transition hover:bg-rose-500/10"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </AdminCard>
        </>
      )}

      {tab === "placements" && (
        <>
          <div className="mb-4 flex justify-end">
            {canManage && (
              <button
                type="button"
                onClick={() => setPlacementDraft({ ...EMPTY_PLACEMENT })}
                className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center]"
              >
                <Plus className="h-4 w-4" /> Add placement
              </button>
            )}
          </div>

          {placementDraft && (
            <PlacementForm
              draft={placementDraft}
              providers={providers}
              saving={saving}
              onChange={setPlacementDraft}
              onSave={onSavePlacement}
              onCancel={() => setPlacementDraft(null)}
              onMove={moveSlot}
            />
          )}

          <AdminCard>
            {loading ? (
              <LoadingState />
            ) : placements.length === 0 ? (
              <EmptyState message="No placements yet." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                      <th className="pb-3 pr-4 font-semibold">Name</th>
                      <th className="pb-3 pr-4 font-semibold">Label</th>
                      <th className="pb-3 pr-4 font-semibold">Slots</th>
                      <th className="pb-3 pr-4 font-semibold">Behavior</th>
                      <th className="pb-3 pr-4 font-semibold">Status</th>
                      <th className="pb-3 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {placements.map((p) => (
                      <tr key={p.id}>
                        <td className="py-3 pr-4 font-mono text-sm text-foreground">{p.name}</td>
                        <td className="py-3 pr-4 text-foreground/70">{p.label}</td>
                        <td className="py-3 pr-4 text-foreground/70">
                          {p.slots
                            .map((s) => `${s.provider_name}#${s.priority}`)
                            .join(", ") || "—"}
                        </td>
                        <td className="py-3 pr-4 text-foreground/70">{p.behavior}</td>
                        <td className="py-3 pr-4">
                          <Badge tone={p.enabled ? "green" : "gray"}>
                            {p.enabled ? "enabled" : "disabled"}
                          </Badge>
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            {canManage && (
                              <>
                                <button
                                  type="button"
                                  onClick={() =>
                                    setPlacementDraft({
                                      id: p.id,
                                      name: p.name,
                                      label: p.label,
                                      enabled: p.enabled,
                                      width: p.width ? String(p.width) : "",
                                      height: p.height ? String(p.height) : "",
                                      responsive: p.responsive,
                                      behavior: p.behavior,
                                      slots: p.slots.map((s) => ({
                                        provider_id: s.provider_id,
                                        priority: s.priority,
                                        frequency: s.frequency,
                                        enabled: s.enabled,
                                      })),
                                    })
                                  }
                                  className="rounded-xl border border-foreground/10 px-3 py-1.5 text-xs font-medium text-foreground/70 transition hover:bg-foreground/5"
                                >
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  onClick={() => onDeletePlacement(p.id, p.name)}
                                  className="rounded-xl border border-rose-500/20 px-3 py-1.5 text-xs font-medium text-rose-500 transition hover:bg-rose-500/10"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </AdminCard>
        </>
      )}

      {tab === "analytics" &&
        (adAnalytics ? (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard label="Impressions" value={adAnalytics.totals.impressions} />
              <StatCard label="Clicks" value={adAnalytics.totals.clicks} />
              <StatCard label="Load failures" value={adAnalytics.totals.load_failures} />
              <StatCard label="CTR" value={`${adAnalytics.totals.ctr}%`} />
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-2">
              {(["provider", "placement", "day"] as const).map((group) => (
                <button
                  key={group}
                  type="button"
                  onClick={() => setAnalyticsGroup(group)}
                  className={`rounded-2xl px-4 py-2 text-sm font-medium transition ${
                    analyticsGroup === group
                      ? "bg-primary-500/10 text-primary-600 dark:text-primary-300"
                      : "text-foreground/60 hover:bg-foreground/5"
                  }`}
                >
                  {group}
                </button>
              ))}
              <button
                type="button"
                onClick={() => void loadAnalytics()}
                className="ml-auto inline-flex items-center gap-1.5 rounded-2xl border border-foreground/10 px-3 py-2 text-xs font-medium text-foreground/70 transition hover:bg-foreground/5"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Refresh
              </button>
            </div>

            <AdminCard className="mt-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                      <th className="pb-3 pr-4 font-semibold">{adAnalytics.group}</th>
                      <th className="pb-3 pr-4 font-semibold">Impressions</th>
                      <th className="pb-3 pr-4 font-semibold">Clicks</th>
                      <th className="pb-3 pr-4 font-semibold">Load failures</th>
                      <th className="pb-3 font-semibold">CTR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {adAnalytics.items.map((item) => (
                      <tr key={item.key}>
                        <td className="py-3 pr-4 font-medium text-foreground">{item.key}</td>
                        <td className="py-3 pr-4 text-foreground/80">{item.impression}</td>
                        <td className="py-3 pr-4 text-foreground/80">{item.click}</td>
                        <td className="py-3 pr-4 text-foreground/80">{item.load_failure}</td>
                        <td className="py-3 text-foreground/80">{item.ctr ?? 0}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AdminCard>
          </>
        ) : (
          <LoadingState />
        ))}
    </>
  );
}

// --- forms ------------------------------------------------------------------

function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={`block ${className ?? ""}`}>
      <span className="mb-1.5 block text-xs font-medium tracking-wide text-foreground/50 uppercase">
        {label}
      </span>
      {children}
    </label>
  );
}

const inputClass =
  "w-full rounded-xl border border-foreground/10 bg-background/60 px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/20";

function FormActions({
  saving,
  onSave,
  onCancel,
}: {
  saving: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        disabled={saving}
        onClick={onSave}
        className="rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center] disabled:opacity-60"
      >
        {saving ? "Saving…" : "Save"}
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="rounded-2xl border border-foreground/10 px-5 py-2.5 text-sm font-medium text-foreground/70 transition hover:bg-foreground/5"
      >
        Cancel
      </button>
    </div>
  );
}

function ProviderForm({
  draft,
  saving,
  onChange,
  onSave,
  onCancel,
}: {
  draft: ProviderDraft;
  saving: boolean;
  onChange: (draft: ProviderDraft) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  const set = (patch: Partial<ProviderDraft>) => onChange({ ...draft, ...patch });
  return (
    <AdminCard className="mb-6" title={draft.id ? "Edit provider" : "New provider"}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Name">
          <input
            className={inputClass}
            value={draft.name}
            onChange={(e) => set({ name: e.target.value })}
            placeholder="e.g. Google AdSense"
          />
        </Field>
        <Field label="Type">
          <select
            className={inputClass}
            value={draft.provider_type}
            onChange={(e) => set({ provider_type: e.target.value })}
          >
            {PROVIDER_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Publisher ID">
          <input
            className={inputClass}
            value={draft.publisher_id}
            onChange={(e) => set({ publisher_id: e.target.value })}
            placeholder="ca-pub-…"
          />
        </Field>
        <Field label="Zone ID">
          <input
            className={inputClass}
            value={draft.zone_id}
            onChange={(e) => set({ zone_id: e.target.value })}
            placeholder="12345678"
          />
        </Field>
        <Field label="Site ID">
          <input
            className={inputClass}
            value={draft.site_id}
            onChange={(e) => set({ site_id: e.target.value })}
          />
        </Field>
        <Field label="Base URL (iframe only)">
          <input
            className={inputClass}
            value={draft.base_url}
            onChange={(e) => set({ base_url: e.target.value })}
          />
        </Field>
        <Field label="Click-through URL">
          <input
            className={inputClass}
            value={draft.click_through_url}
            onChange={(e) => set({ click_through_url: e.target.value })}
          />
        </Field>
        <Field label="Enabled">
          <input
            type="checkbox"
            checked={draft.enabled}
            onChange={(e) => set({ enabled: e.target.checked })}
            className="mt-2 h-5 w-5 accent-primary-500"
          />
        </Field>
        <Field label="Custom script" className="sm:col-span-2">
          <textarea
            className={`${inputClass} h-24 resize-y font-mono`}
            value={draft.custom_script}
            onChange={(e) => set({ custom_script: e.target.value })}
            placeholder="Trusted-admin only: mounted in an isolated sandboxed frame."
          />
        </Field>
      </div>
      <div className="mt-5">
        <FormActions saving={saving} onSave={onSave} onCancel={onCancel} />
      </div>
    </AdminCard>
  );
}

function PlacementForm({
  draft,
  providers,
  saving,
  onChange,
  onSave,
  onCancel,
  onMove,
}: {
  draft: PlacementDraft;
  providers: AdProviderItem[];
  saving: boolean;
  onChange: (draft: PlacementDraft) => void;
  onSave: () => void;
  onCancel: () => void;
  onMove: (index: number, direction: -1 | 1) => void;
}) {
  const set = (patch: Partial<PlacementDraft>) => onChange({ ...draft, ...patch });
  const updateSlot = (index: number, patch: Partial<SlotDraft>) => {
    const slots = draft.slots.map((s, i) => (i === index ? { ...s, ...patch } : s));
    set({ slots });
  };
  const addSlot = () => {
    const first = providers.find((p) => p.enabled);
    if (!first) {
      set({ slots: [...draft.slots, { provider_id: "", priority: draft.slots.length + 1, frequency: "every_page", enabled: true }] });
      return;
    }
    set({
      slots: [
        ...draft.slots,
        { provider_id: first.id, priority: draft.slots.length + 1, frequency: "every_page", enabled: true },
      ],
    });
  };
  const removeSlot = (index: number) => {
    set({ slots: draft.slots.filter((_, i) => i !== index) });
  };

  return (
    <AdminCard className="mb-6" title={draft.id ? "Edit placement" : "New placement"}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Name">
          <input
            className={inputClass}
            value={draft.name}
            disabled={Boolean(draft.id)}
            onChange={(e) => set({ name: e.target.value.replace(/[^a-z0-9_]/g, "") })}
            placeholder="landing_top"
          />
        </Field>
        <Field label="Label">
          <input
            className={inputClass}
            value={draft.label}
            onChange={(e) => set({ label: e.target.value })}
            placeholder="Landing top"
          />
        </Field>
        <Field label="Width (px)">
          <input
            className={inputClass}
            value={draft.width}
            onChange={(e) => set({ width: e.target.value.replace(/\D/g, "") })}
          />
        </Field>
        <Field label="Height (px)">
          <input
            className={inputClass}
            value={draft.height}
            onChange={(e) => set({ height: e.target.value.replace(/\D/g, "") })}
          />
        </Field>
        <Field label="Behavior">
          <select
            className={inputClass}
            value={draft.behavior}
            onChange={(e) => set({ behavior: e.target.value as "lazy" | "eager" })}
          >
            <option value="lazy">lazy</option>
            <option value="eager">eager</option>
          </select>
        </Field>
        <div className="flex items-end gap-6 pb-2">
          <label className="flex items-center gap-2 text-sm text-foreground/70">
            <input
              type="checkbox"
              checked={draft.responsive}
              onChange={(e) => set({ responsive: e.target.checked })}
              className="h-5 w-5 accent-primary-500"
            />
            Responsive
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground/70">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => set({ enabled: e.target.checked })}
              className="h-5 w-5 accent-primary-500"
            />
            Enabled
          </label>
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold tracking-wide text-foreground/80 uppercase">
            Slots (priority order)
          </h3>
          <button
            type="button"
            onClick={addSlot}
            className="inline-flex items-center gap-1.5 rounded-xl border border-foreground/10 px-3 py-1.5 text-xs font-medium text-foreground/70 transition hover:bg-foreground/5"
          >
            <Plus className="h-3.5 w-3.5" /> Add slot
          </button>
        </div>
        {draft.slots.length === 0 ? (
          <p className="py-4 text-center text-sm text-foreground/50">
            No slots. Add at least one provider to serve an ad.
          </p>
        ) : (
          <div className="space-y-3">
            {draft.slots.map((slot, index) => (
              <div
                key={index}
                className="flex flex-col gap-3 rounded-2xl border border-foreground/10 p-3 sm:flex-row sm:items-center"
              >
                <button
                  type="button"
                  onClick={() => onMove(index, -1)}
                  disabled={index === 0}
                  className="rounded-lg border border-foreground/10 p-1.5 text-foreground/50 transition hover:bg-foreground/5 disabled:opacity-30"
                  aria-label="Move up"
                >
                  <ArrowUpDown className="h-3.5 w-3.5 rotate-180" />
                </button>
                <span className="w-6 text-center text-sm font-bold text-foreground/50">
                  {slot.priority}
                </span>
                <select
                  className={`${inputClass} flex-1`}
                  value={slot.provider_id}
                  onChange={(e) => updateSlot(index, { provider_id: e.target.value })}
                >
                  <option value="">— select provider —</option>
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.enabled ? "enabled" : "disabled"})
                    </option>
                  ))}
                </select>
                <select
                  className={`${inputClass} sm:w-40`}
                  value={slot.frequency}
                  onChange={(e) => updateSlot(index, { frequency: e.target.value })}
                >
                  {FREQUENCIES.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-2 text-sm text-foreground/70">
                  <input
                    type="checkbox"
                    checked={slot.enabled}
                    onChange={(e) => updateSlot(index, { enabled: e.target.checked })}
                    className="h-5 w-5 accent-primary-500"
                  />
                  Active
                </label>
                <button
                  type="button"
                  onClick={() => removeSlot(index)}
                  className="rounded-lg border border-rose-500/20 p-1.5 text-rose-500 transition hover:bg-rose-500/10"
                  aria-label="Remove slot"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-5">
        <FormActions saving={saving} onSave={onSave} onCancel={onCancel} />
      </div>
    </AdminCard>
  );
}
