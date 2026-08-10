"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Droplets,
  FileText,
  Fingerprint,
  LayoutDashboard,
  Loader2,
  LogOut,
  Megaphone,
  MessageSquare,
  Moon,
  ScrollText,
  Settings,
  ShieldCheck,
  Sun,
  Users,
} from "lucide-react";
import { AdminAuthProvider, useAdminAuth } from "@/hooks/useAdminAuth";
import { useTheme } from "@/hooks/useTheme";
import { cn } from "@/lib/cn";
import { Logo } from "@/components/ui/Logo";

const NAV_ITEMS = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/admin/media", label: "Media", icon: FileText },
  { href: "/admin/jobs", label: "Jobs", icon: Activity },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/whatsapp", label: "WhatsApp", icon: MessageSquare },
  { href: "/admin/watermark", label: "Watermark", icon: Droplets },
  { href: "/admin/ads", label: "Ads", icon: Megaphone },
  { href: "/admin/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/admin/settings", label: "Settings", icon: Settings },
  { href: "/admin/security", label: "Security", icon: ShieldCheck },
  { href: "/admin/logs", label: "Logs & Audit", icon: ScrollText },
  { href: "/admin/health", label: "Health", icon: Fingerprint },
];

function AdminShell({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAdminAuth();
  const pathname = usePathname();
  const { resolvedTheme, toggleTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  const isLogin = pathname === "/admin/login";

  if (isLogin) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!user) return null;

  const navClass = (item: { href: string; exact?: boolean }) => {
    const active = item.exact
      ? pathname === item.href
      : pathname.startsWith(item.href);
    return cn(
      "flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-colors",
      active
        ? "bg-primary-500/10 text-primary-600 dark:text-primary-300"
        : "text-foreground/65 hover:bg-foreground/5 hover:text-foreground",
    );
  };

  const sidebar = (
    <div className="flex h-full flex-col gap-6">
      <div className="flex items-center gap-3 px-2">
        <Logo />
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className={navClass(item)}>
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-white/10 pt-4">
        <div className="mb-3 px-4">
          <p className="truncate text-sm font-semibold text-foreground">
            {user.full_name || user.email}
          </p>
          <p className="truncate text-xs text-foreground/50">{user.email}</p>
          <span className="mt-2 inline-flex rounded-full bg-accent-500/10 px-2.5 py-0.5 text-xs font-medium text-accent-600 dark:text-accent-400">
            {user.role.replace("_", " ")}
          </span>
        </div>
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium text-foreground/65 transition hover:bg-foreground/5 hover:text-rose-500"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Sign out
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-mesh">
      <div className="flex min-h-screen">
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-white/10 bg-background/70 p-4 backdrop-blur-xl lg:block">
          {sidebar}
        </aside>

        {sidebarOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => setSidebarOpen(false)}
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            />
            <aside className="glass-strong absolute inset-y-0 left-0 w-64 p-4">
              {sidebar}
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-white/10 bg-background/70 px-4 backdrop-blur-xl sm:px-6">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="glass flex h-10 w-10 items-center justify-center rounded-full lg:hidden"
              aria-label="Open menu"
            >
              <span className="text-foreground/70">☰</span>
            </button>
            <div className="hidden text-sm text-foreground/50 sm:block">
              {NAV_ITEMS.find(
                (item) =>
                  (item.exact && pathname === item.href) ||
                  (!item.exact && pathname.startsWith(item.href)),
              )?.label ?? "Admin"}
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={toggleTheme}
                aria-label="Toggle theme"
                className="glass flex h-10 w-10 items-center justify-center rounded-full transition-transform hover:scale-105"
              >
                {resolvedTheme === "dark" ? (
                  <Sun className="h-4 w-4" />
                ) : (
                  <Moon className="h-4 w-4" />
                )}
              </button>
            </div>
          </header>

          <main className="flex-1 px-4 py-8 sm:px-6 lg:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminShell>{children}</AdminShell>
    </AdminAuthProvider>
  );
}
