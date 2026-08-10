"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Info, XCircle } from "lucide-react";
import type { ToastVariant } from "@/types";
import { cn } from "@/lib/cn";

interface ToastItem {
  id: string;
  message: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  showToast: (message: string, variant?: ToastVariant) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const variantStyles: Record<
  ToastVariant,
  { icon: typeof Info; ring: string; iconColor: string }
> = {
  success: {
    icon: CheckCircle2,
    ring: "border-emerald-400/40",
    iconColor: "text-emerald-500",
  },
  error: {
    icon: XCircle,
    ring: "border-rose-400/40",
    iconColor: "text-rose-500",
  },
  info: {
    icon: Info,
    ring: "border-primary-400/40",
    iconColor: "text-primary-500",
  },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, variant: ToastVariant = "info") => {
      const id = `toast_${++counter.current}`;
      setToasts((prev) => [...prev.slice(-3), { id, message, variant }]);
      window.setTimeout(() => dismiss(id), 3600);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ showToast, dismiss }), [showToast, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="fixed top-4 right-4 z-[90] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2"
      >
        <AnimatePresence>
          {toasts.map((toast) => {
            const style = variantStyles[toast.variant];
            const Icon = style.icon;
            return (
              <motion.div
                key={toast.id}
                layout
                initial={{ opacity: 0, y: -16, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, transition: { duration: 0.2 } }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
                className={cn(
                  "glass-strong flex items-center gap-3 rounded-2xl px-4 py-3",
                  style.ring,
                )}
                role="status"
              >
                <Icon className={cn("h-5 w-5 shrink-0", style.iconColor)} />
                <p className="text-sm font-medium text-foreground">
                  {toast.message}
                </p>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return ctx;
}
