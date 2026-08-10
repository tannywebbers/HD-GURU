"use client";

import type { ReactNode } from "react";
import { ThemeProvider } from "@/hooks/useTheme";
import { ToastProvider } from "@/components/ToastProvider";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>{children}</ToastProvider>
    </ThemeProvider>
  );
}
