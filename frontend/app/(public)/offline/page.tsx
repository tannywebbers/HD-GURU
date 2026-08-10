"use client";

import { WifiOff } from "lucide-react";
import { Logo } from "@/components/ui/Logo";

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <Logo showWordmark={false} />
      <div className="mt-8 flex h-20 w-20 items-center justify-center rounded-3xl bg-foreground/5 text-foreground/50">
        <WifiOff className="h-10 w-10" />
      </div>
      <h1 className="mt-6 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
        You&apos;re offline
      </h1>
      <p className="mx-auto mt-3 max-w-md text-sm text-foreground/60">
        Check your connection and try again. Your previous results are cached,
        so you can still browse the pages you&apos;ve visited.
      </p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="mt-8 cursor-pointer rounded-2xl bg-gradient-to-r from-primary-600 to-accent-600 px-6 py-3 text-sm font-semibold text-white shadow-glow transition-transform hover:scale-105"
      >
        Try again
      </button>
    </div>
  );
}
