"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  adminApi,
  clearAdminTokens,
  getStoredTokens,
} from "@/services/admin-api";
import type { AdminMe } from "@/types/admin";

interface AdminAuthContextValue {
  user: AdminMe | null;
  loading: boolean;
  hasPermission: (permission: string) => boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<string | null>;
  logout: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextValue | undefined>(
  undefined,
);

const ADMIN_PREFIX = "/admin";
const LOGIN_PATH = "/admin/login";

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AdminMe | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const validate = useCallback(async () => {
    if (!getStoredTokens()) {
      setUser(null);
      setLoading(false);
      return;
    }
    const res = await adminApi.me();
    if (res.ok && res.data) {
      setUser(res.data);
    } else {
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (pathname.startsWith(ADMIN_PREFIX) && !pathname.startsWith(LOGIN_PATH)) {
      validate();
    } else {
      setLoading(false);
    }
  }, [pathname, validate]);

  const login = useCallback(
    async (email: string, password: string): Promise<string | null> => {
      const res = await adminApi.login(email, password);
      if (!res.ok || !res.data) {
        return res.error ?? "Login failed.";
      }
      setUser(res.data);
      return null;
    },
    [],
  );

  const logout = useCallback(async () => {
    await adminApi.logout();
    setUser(null);
    clearAdminTokens();
    router.push(LOGIN_PATH);
  }, [router]);

  const value = useMemo<AdminAuthContextValue>(() => {
    const permissions = user?.permissions ?? [];
    return {
      user,
      loading,
      isAdmin: user?.role === "admin" || user?.role === "super_admin",
      hasPermission: (permission: string) => permissions.includes(permission),
      login,
      logout,
    };
  }, [user, loading, login, logout]);

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth(): AdminAuthContextValue {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) {
    throw new Error("useAdminAuth must be used within an AdminAuthProvider");
  }
  return ctx;
}
