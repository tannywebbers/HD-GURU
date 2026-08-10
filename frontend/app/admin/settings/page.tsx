"use client";

import { useCallback, useEffect, useState } from "react";
import { Save } from "lucide-react";
import { adminApi } from "@/services/admin-api";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { AdminSettingItem, AdminSettingsOut } from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  ErrorState,
  LoadingState,
} from "@/components/admin/ui";
import { useToast } from "@/components/ToastProvider";

const fieldClass =
  "w-full rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 focus:ring-2 focus:ring-primary-500/30 dark:bg-white/5";

type Draft = Record<string, string>;

export default function AdminSettingsPage() {
  const { showToast } = useToast();
  const { hasPermission } = useAdminAuth();
  const canManage = hasPermission("settings.manage");

  const [data, setData] = useState<AdminSettingsOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await adminApi.settings();
    if (res.ok && res.data) {
      setData(res.data);
      const next: Draft = {};
      for (const item of res.data.settings) {
        next[item.key] =
          item.is_secret
            ? "***"
            : item.value === null || item.value === undefined
              ? ""
              : String(item.value);
      }
      setDraft(next);
    } else {
      setError(res.error ?? "Failed to load settings.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const grouped: Record<string, AdminSettingItem[]> = {};
  for (const item of data?.settings ?? []) {
    (grouped[item.group] ??= []).push(item);
  }

  const onSave = async () => {
    if (!data) return;
    const items = data.settings
      .map((item) => {
        const value = draft[item.key] ?? "";
        if (item.is_secret && value === "***") return null;
        let parsed: unknown = value;
        if (item.key.includes("allowed_mime_types")) {
          parsed = value
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
        }
        return { key: item.key, value: parsed };
      })
      .filter(Boolean) as Array<{ key: string; value: unknown }>;

    setSaving(true);
    const res = await adminApi.updateSettings(items);
    setSaving(false);
    if (res.ok) {
      showToast("Settings saved.", "success");
      load();
    } else {
      showToast(res.error ?? "Failed to save settings.", "error");
    }
  };

  return (
    <>
      <AdminPageHeader
        title="Settings"
        description="Application configuration. Secret values are masked and never shown."
        actions={
          canManage && (
            <button
              type="button"
              onClick={onSave}
              disabled={saving || loading}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center] disabled:opacity-60"
            >
              <Save className="h-4 w-4" />
              Save changes
            </button>
          )
        }
      />

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([group, items]) => (
            <AdminCard key={group} title={group}>
              <div className="grid gap-5 sm:grid-cols-2">
                {items.map((item) => (
                  <div key={item.key}>
                    <label
                      htmlFor={item.key}
                      className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase"
                    >
                      {item.key}
                      {item.is_secret && (
                        <span className="ml-2 text-accent-500">secret</span>
                      )}
                    </label>
                    <input
                      id={item.key}
                      type={item.is_secret ? "password" : "text"}
                      disabled={!canManage}
                      value={draft[item.key] ?? ""}
                      onChange={(e) =>
                        setDraft({ ...draft, [item.key]: e.target.value })
                      }
                      className={fieldClass}
                      spellCheck={false}
                    />
                    {item.description && (
                      <p className="mt-1.5 text-xs text-foreground/45">
                        {item.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </AdminCard>
          ))}
        </div>
      )}
    </>
  );
}
