"use client";

import { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { adminApi } from "@/services/admin-api";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { AdminWatermarkItem } from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  Badge,
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/admin/ui";
import { useToast } from "@/components/ToastProvider";

const POSITIONS = [
  "top-left",
  "top-right",
  "bottom-left",
  "bottom-right",
  "center",
];

const fieldClass =
  "w-full rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 focus:ring-2 focus:ring-primary-500/30 dark:bg-white/5";

interface FormState {
  name: string;
  type: "text" | "image";
  text: string;
  image_url: string;
  position: string;
  opacity: number;
  size_percent: number;
  margin: string;
  enabled: boolean;
}

const emptyForm: FormState = {
  name: "",
  type: "text",
  text: "",
  image_url: "",
  position: "bottom-right",
  opacity: 0.35,
  size_percent: 8,
  margin: "",
  enabled: true,
};

export default function AdminWatermarkPage() {
  const { showToast } = useToast();
  const { hasPermission } = useAdminAuth();
  const canManage = hasPermission("watermark.manage");

  const [items, setItems] = useState<AdminWatermarkItem[] | null>(null);
  const [positions, setPositions] = useState<string[]>(POSITIONS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<AdminWatermarkItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [listRes, posRes] = await Promise.all([
      adminApi.listWatermarks(),
      adminApi.watermarkPositions(),
    ]);
    if (listRes.ok && listRes.data) {
      setItems(listRes.data);
    } else {
      setError(listRes.error ?? "Failed to load watermarks.");
    }
    if (posRes.ok && posRes.data) setPositions(posRes.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setForm(emptyForm);
    setEditing(null);
    setShowForm(false);
  };

  const openCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const openEdit = (item: AdminWatermarkItem) => {
    setEditing(item);
    setShowForm(true);
    setForm({
      name: item.name,
      type: item.type,
      text: item.text ?? "",
      image_url: item.image_url ?? "",
      position: item.position,
      opacity: item.opacity,
      size_percent: item.size_percent,
      margin: item.margin != null ? String(item.margin) : "",
      enabled: item.enabled,
    });
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      type: form.type,
      text: form.type === "text" ? form.text.trim() : null,
      image_url: form.type === "image" ? form.image_url.trim() : null,
      position: form.position,
      opacity: form.opacity,
      size_percent: form.size_percent,
      margin: form.margin === "" ? null : Number(form.margin),
      enabled: form.enabled,
    };
    const res = editing
      ? await adminApi.updateWatermark(editing.id, payload)
      : await adminApi.createWatermark(payload);
    setSaving(false);
    if (res.ok) {
      showToast(editing ? "Watermark updated." : "Watermark created.", "success");
      resetForm();
      load();
    } else {
      showToast(res.error ?? "Failed to save watermark.", "error");
    }
  };

  const onDelete = async (item: AdminWatermarkItem) => {
    if (!window.confirm(`Delete watermark "${item.name}"?`)) return;
    const res = await adminApi.deleteWatermark(item.id);
    if (res.ok) {
      showToast("Watermark deleted.", "success");
      load();
    } else {
      showToast(res.error ?? "Failed to delete watermark.", "error");
    }
  };

  return (
    <>
      <AdminPageHeader
        title="Watermark"
        description="Watermark presets applied to processed media."
        actions={
          canManage && (
            <button
              type="button"
              onClick={openCreate}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center]"
            >
              <Plus className="h-4 w-4" />
              New watermark
            </button>
          )
        }
      />

      {showForm && canManage && (
        <div className="mb-6">
          <AdminCard title={editing ? "Edit watermark" : "New watermark"}>
            <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Name
                </label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Type
                </label>
                <select
                  value={form.type}
                  onChange={(e) =>
                    setForm({ ...form, type: e.target.value as "text" | "image" })
                  }
                  className={fieldClass}
                >
                  <option value="text">Text</option>
                  <option value="image">Image</option>
                </select>
              </div>
              {form.type === "text" ? (
                <div className="sm:col-span-2">
                  <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                    Text
                  </label>
                  <input
                    type="text"
                    required
                    value={form.text}
                    onChange={(e) => setForm({ ...form, text: e.target.value })}
                    className={fieldClass}
                  />
                </div>
              ) : (
                <div className="sm:col-span-2">
                  <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                    Image URL
                  </label>
                  <input
                    type="url"
                    required
                    value={form.image_url}
                    onChange={(e) => setForm({ ...form, image_url: e.target.value })}
                    className={fieldClass}
                  />
                </div>
              )}
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Position
                </label>
                <select
                  value={form.position}
                  onChange={(e) => setForm({ ...form, position: e.target.value })}
                  className={fieldClass}
                >
                  {positions.map((p) => (
                    <option key={p} value={p}>
                      {p.replace("-", " ")}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Size (%)
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  step={0.5}
                  value={form.size_percent}
                  onChange={(e) => setForm({ ...form, size_percent: Number(e.target.value) })}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Opacity
                </label>
                <input
                  type="number"
                  min={0.05}
                  max={1}
                  step={0.05}
                  value={form.opacity}
                  onChange={(e) => setForm({ ...form, opacity: Number(e.target.value) })}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Margin (px)
                </label>
                <input
                  type="number"
                  min={0}
                  max={1000}
                  value={form.margin}
                  onChange={(e) => setForm({ ...form, margin: e.target.value })}
                  placeholder="auto"
                  className={fieldClass}
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-foreground/70">
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
                  className="h-4 w-4 rounded border-white/10 accent-primary-500"
                />
                Enabled
              </label>
              <div className="flex items-end justify-end gap-2 sm:col-span-2">
                <button
                  type="button"
                  onClick={resetForm}
                  className="rounded-2xl border border-white/10 px-4 py-2.5 text-sm font-medium text-foreground/70 transition hover:bg-foreground/5"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-700 disabled:opacity-60"
                >
                  {saving ? "Saving…" : editing ? "Save changes" : "Create"}
                </button>
              </div>
            </form>
          </AdminCard>
        </div>
      )}

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !items || items.length === 0 ? (
        <EmptyState message="No watermarks configured." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <div key={item.id} className="glass-strong rounded-3xl p-5">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-foreground">{item.name}</h3>
                  <div className="mt-1.5 flex flex-wrap gap-2">
                    <Badge tone={item.enabled ? "green" : "gray"}>
                      {item.enabled ? "enabled" : "disabled"}
                    </Badge>
                    <Badge tone="blue">{item.type}</Badge>
                  </div>
                </div>
                {canManage && (
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      onClick={() => openEdit(item)}
                      className="rounded-xl border border-white/10 p-2 text-foreground/60 transition hover:bg-foreground/5"
                      aria-label={`Edit ${item.name}`}
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(item)}
                      className="rounded-xl border border-rose-500/20 p-2 text-rose-500 transition hover:bg-rose-500/10"
                      aria-label={`Delete ${item.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>
              <div className="space-y-1.5 text-sm text-foreground/70">
                <p className="truncate">
                  {item.type === "text" ? item.text : "Image watermark"}
                </p>
                <p>Position: {item.position.replace("-", " ")}</p>
                <p>
                  Size {item.size_percent}% · Opacity {Math.round(item.opacity * 100)}%
                  {item.margin != null ? ` · Margin ${item.margin}px` : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
