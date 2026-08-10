"use client";

import { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { adminApi } from "@/services/admin-api";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { AdminRole, AdminUserItem, AdminUserPage, UserUpdateRequest } from "@/types/admin";
import {
  AdminCard,
  AdminPageHeader,
  Badge,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
} from "@/components/admin/ui";
import { useToast } from "@/components/ToastProvider";

const ROLES: AdminRole[] = ["viewer", "operator", "admin", "super_admin"];

const roleTone: Record<AdminRole, "gray" | "blue" | "purple" | "green" | "amber"> = {
  user: "gray",
  viewer: "blue",
  operator: "amber",
  admin: "purple",
  super_admin: "green",
};

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

const fieldClass =
  "w-full rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 focus:ring-2 focus:ring-primary-500/30 dark:bg-white/5";

export default function AdminUsersPage() {
  const { showToast } = useToast();
  const { user: me, hasPermission } = useAdminAuth();
  const canManage = hasPermission("users.manage");

  const [data, setData] = useState<AdminUserPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [role, setRole] = useState("");
  const [search, setSearch] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<AdminUserItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    role: "viewer" as AdminRole,
    is_active: true,
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await adminApi.listUsers(page, 20, {
      role: role || undefined,
      search: search || undefined,
    });
    if (res.ok && res.data) {
      setData(res.data);
    } else {
      setError(res.error ?? "Failed to load users.");
    }
    setLoading(false);
  }, [page, role, search]);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setForm({ email: "", password: "", full_name: "", role: "viewer", is_active: true });
    setEditing(null);
    setShowCreate(false);
  };

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const res = await adminApi.createUser({
      email: form.email,
      password: form.password,
      full_name: form.full_name || null,
      role: form.role,
      is_active: form.is_active,
      must_change_password: true,
    });
    setSaving(false);
    if (res.ok) {
      showToast("User created.", "success");
      resetForm();
      load();
    } else {
      showToast(res.error ?? "Failed to create user.", "error");
    }
  };

  const onUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    setSaving(true);
    const payload: UserUpdateRequest = {
      full_name: form.full_name || null,
      role: form.role,
      is_active: form.is_active,
    };
    const res = await adminApi.updateUser(editing.id, payload);
    setSaving(false);
    if (res.ok) {
      showToast("User updated.", "success");
      resetForm();
      load();
    } else {
      showToast(res.error ?? "Failed to update user.", "error");
    }
  };

  const onDelete = async (user: AdminUserItem) => {
    if (user.id === me?.id) {
      showToast("You cannot delete your own account.", "error");
      return;
    }
    if (!window.confirm(`Delete user "${user.email}"?`)) return;
    const res = await adminApi.deleteUser(user.id);
    if (res.ok) {
      showToast("User deleted.", "success");
      load();
    } else {
      showToast(res.error ?? "Failed to delete user.", "error");
    }
  };

  const openEdit = (user: AdminUserItem) => {
    setEditing(user);
    setShowCreate(true);
    setForm({
      email: user.email,
      password: "",
      full_name: user.full_name ?? "",
      role: user.role,
      is_active: user.is_active,
    });
  };

  const isMe = (id: string) => id === me?.id;

  return (
    <>
      <AdminPageHeader
        title="Users"
        description="Manage staff accounts and roles. Changes are audited."
        actions={
          canManage && (
            <button
              type="button"
              onClick={() => {
                resetForm();
                setShowCreate(true);
              }}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center]"
            >
              <Plus className="h-4 w-4" />
              Add user
            </button>
          )
        }
      />

      {showCreate && canManage && (
        <div className="mb-6">
          <AdminCard title={editing ? "Edit user" : "Add user"}>
            <form onSubmit={editing ? onUpdate : onCreate} className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Email
                </label>
                <input
                  type="email"
                  required
                  disabled={!!editing}
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className={fieldClass}
                />
              </div>
              {!editing && (
                <div>
                  <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    className={fieldClass}
                    placeholder="Min 8 characters"
                  />
                </div>
              )}
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Full name
                </label>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  className={fieldClass}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase">
                  Role
                </label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value as AdminRole })}
                  className={fieldClass}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-foreground/70">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  className="h-4 w-4 rounded border-white/10 accent-primary-500"
                />
                Active
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
                  className="inline-flex items-center gap-2 rounded-2xl bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-700 disabled:opacity-60"
                >
                  {saving ? "Saving…" : editing ? "Save changes" : "Create user"}
                </button>
              </div>
            </form>
          </AdminCard>
        </div>
      )}

      <AdminCard>
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            type="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by email or name…"
            className="w-full rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 sm:max-w-xs dark:bg-white/5"
          />
          <select
            value={role}
            onChange={(e) => {
              setRole(e.target.value);
              setPage(1);
            }}
            className="rounded-2xl border border-white/10 bg-white/60 px-4 py-2.5 text-sm text-foreground outline-none transition focus:border-primary-500/60 dark:bg-white/5"
          >
            <option value="">All roles</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} onRetry={load} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState message="No users found." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs tracking-wide text-foreground/50 uppercase">
                    <th className="pb-3 pr-4 font-semibold">User</th>
                    <th className="pb-3 pr-4 font-semibold">Role</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Last login</th>
                    <th className="pb-3 pr-4 font-semibold">Uploads</th>
                    <th className="pb-3 font-semibold"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {data.items.map((user) => (
                    <tr key={user.id}>
                      <td className="max-w-xs py-3 pr-4">
                        <p className="truncate font-medium text-foreground">
                          {user.full_name || user.email}
                          {isMe(user.id) && (
                            <span className="ml-2 text-xs text-foreground/40">(you)</span>
                          )}
                        </p>
                        <p className="truncate text-xs text-foreground/50">{user.email}</p>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge tone={roleTone[user.role] ?? "gray"}>
                          {user.role.replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4">
                        {!user.is_active ? (
                          <Badge tone="red">inactive</Badge>
                        ) : user.is_locked ? (
                          <Badge tone="amber">locked</Badge>
                        ) : user.must_change_password ? (
                          <Badge tone="amber">must reset</Badge>
                        ) : (
                          <Badge tone="green">active</Badge>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-xs text-foreground/50">
                        {fmtDate(user.last_login_at)}
                      </td>
                      <td className="py-3 pr-4 tabular-nums text-foreground/70">
                        {user.uploads_count}
                      </td>
                      <td className="py-3 text-right">
                        {canManage && (
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => openEdit(user)}
                              disabled={isMe(user.id) && (user.role === "admin" || user.role === "super_admin")}
                              className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 px-3 py-1.5 text-xs font-medium text-foreground/70 transition hover:bg-foreground/5 disabled:opacity-40"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                              Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => onDelete(user)}
                              disabled={isMe(user.id)}
                              className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/20 px-3 py-1.5 text-xs font-medium text-rose-500 transition hover:bg-rose-500/10 disabled:opacity-40"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
          </>
        )}
      </AdminCard>
    </>
  );
}
