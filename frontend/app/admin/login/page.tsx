"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Lock, Mail } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useToast } from "@/components/ToastProvider";
import { Logo } from "@/components/ui/Logo";
import { cn } from "@/lib/cn";

function LoginForm() {
  const { login, user, loading } = useAdminAuth();
  const router = useRouter();
  const { showToast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.replace("/admin");
    }
  }, [loading, user, router]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    const error = await login(email.trim(), password);
    setSubmitting(false);
    if (error) {
      showToast(error, "error");
    } else {
      router.replace("/admin");
    }
  };

  const fieldClass =
    "w-full rounded-2xl border border-white/10 bg-white/60 px-4 py-3 text-sm text-foreground outline-none transition focus:border-primary-500/60 focus:ring-2 focus:ring-primary-500/30 dark:bg-white/5";

  return (
    <div className="flex min-h-screen items-center justify-center bg-mesh px-4">
      <div className="w-full max-w-md">
        <div className="glass-strong rounded-3xl p-8">
          <div className="mb-8 flex flex-col items-center gap-3 text-center">
            <Logo />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Admin Console
            </h1>
            <p className="text-sm text-foreground/60">
              Sign in with an administrator account
            </p>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase"
              >
                Email
              </label>
              <div className="relative">
                <Mail className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-foreground/40" />
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@example.com"
                  className={cn(fieldClass, "pl-10")}
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-xs font-semibold tracking-wide text-foreground/60 uppercase"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-foreground/40" />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={cn(fieldClass, "pl-10")}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] px-6 py-3 text-sm font-semibold text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] transition-all duration-300 hover:bg-[position:right_center] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Sign in
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-foreground/40">
          Restricted area. Access is logged and audited.
        </p>
      </div>
    </div>
  );
}

export default function AdminLoginPage() {
  return <LoginForm />;
}
