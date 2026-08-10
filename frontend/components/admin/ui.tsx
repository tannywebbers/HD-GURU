"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function AdminPageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm text-foreground/60">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function AdminCard({
  children,
  className,
  title,
  action,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  action?: ReactNode;
}) {
  return (
    <div className={cn("glass-strong rounded-3xl p-6", className)}>
      {(title || action) && (
        <div className="mb-5 flex items-center justify-between gap-4">
          {title && (
            <h2 className="text-sm font-semibold tracking-wide text-foreground/80 uppercase">
              {title}
            </h2>
          )}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  icon,
  hint,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  hint?: string;
}) {
  return (
    <div className="glass-strong rounded-3xl p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold tracking-wide text-foreground/50 uppercase">
          {label}
        </span>
        {icon && <span className="text-primary-500">{icon}</span>}
      </div>
      <div className="mt-3 text-3xl font-bold tabular-nums text-foreground">
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-foreground/50">{hint}</div>}
    </div>
  );
}

const badgeTones: Record<string, string> = {
  green: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  red: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
  amber: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  blue: "bg-primary-500/10 text-primary-600 dark:text-primary-300 border-primary-500/20",
  purple: "bg-accent-500/10 text-accent-600 dark:text-accent-400 border-accent-500/20",
  gray: "bg-foreground/5 text-foreground/60 border-foreground/10",
};

export function Badge({
  children,
  tone = "gray",
  className,
}: {
  children: ReactNode;
  tone?: keyof typeof badgeTones;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        badgeTones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function statusTone(status: string): keyof typeof badgeTones {
  const s = status.toLowerCase();
  if (["completed", "success", "delivered", "active", "ok", "read", "succeeded"].includes(s)) {
    return "green";
  }
  if (["failed", "error", "expired", "dead", "revoked", "locked", "rejected", "cancelled"].includes(s)) {
    return "red";
  }
  if (["queued", "pending", "processing", "running", "received", "in_progress", "uploading"].includes(s)) {
    return "amber";
  }
  if (["enhancing", "watermarking", "compressing", "storing", "sending"].includes(s)) {
    return "blue";
  }
  return "gray";
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={statusTone(status)}>{status}</Badge>;
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-sm text-foreground/50">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
      {label}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="py-16 text-center text-sm text-foreground/50">{message}</div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="py-12 text-center">
      <p className="text-sm text-rose-500">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-xl border border-foreground/10 px-4 py-2 text-sm font-medium text-foreground/70 transition hover:bg-foreground/5"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function Pagination({
  page,
  pages,
  total,
  onChange,
}: {
  page: number;
  pages: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (pages <= 1) {
    return (
      <div className="pt-4 text-center text-xs text-foreground/50">
        {total} total
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between gap-4 pt-4">
      <span className="text-xs text-foreground/50">{total} total</span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className="rounded-xl border border-foreground/10 px-3 py-1.5 text-sm text-foreground/70 transition hover:bg-foreground/5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Previous
        </button>
        <span className="px-2 text-xs text-foreground/60">
          {page} / {pages}
        </span>
        <button
          type="button"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
          className="rounded-xl border border-foreground/10 px-3 py-1.5 text-sm text-foreground/70 transition hover:bg-foreground/5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
