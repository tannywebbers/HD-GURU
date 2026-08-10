"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Check, MessageCircle, Wand2 } from "lucide-react";
import { useCountdown } from "@/hooks/useCountdown";
import { COUNTDOWN_SECONDS } from "@/lib/constants";
import { getResult } from "@/services/api";
import { loadFiles } from "@/lib/fileStore";
import { saveResult } from "@/lib/resultStore";
import { trackEvent } from "@/services/ads";
import { useToast } from "@/components/ToastProvider";

const RADIUS = 104;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function CountdownFlow() {
  const router = useRouter();
  const { showToast } = useToast();
  const { seconds, isComplete, start } = useCountdown(COUNTDOWN_SECONDS);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stored = loadFiles();
    if (stored.length === 0) {
      router.replace("/upload");
      return;
    }
    start();
  }, [router, start]);

  const progress = seconds / COUNTDOWN_SECONDS;
  const dashOffset = CIRCUMFERENCE * (1 - progress);

  const handleGetHD = async () => {
    if (loading) return;
    setLoading(true);
    trackEvent("get_hd_clicked");
    const stored = loadFiles();
    const res = await getResult(stored[0]?.id ?? "hdguru");
    if (!res.ok || !res.data) {
      showToast("Could not prepare your file. Please try again.", "error");
      setLoading(false);
      return;
    }
    saveResult(res.data);
    router.push("/result");
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
      <span className="glass mb-6 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold tracking-wide text-primary-600 uppercase dark:text-primary-300">
        Step 3 of 4 · Finalizing
      </span>
      <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-5xl">
        Your HD file is almost <span className="text-gradient">ready</span>
      </h1>
      <p className="mt-4 max-w-xl text-sm text-foreground/60 sm:text-base">
        We&apos;re handing your enhanced file to WhatsApp. Grab it in a moment.
      </p>

      <div className="relative mt-12 flex items-center justify-center">
        <svg width="260" height="260" viewBox="0 0 260 260" className="-rotate-90">
          <defs>
            <linearGradient id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="55%" stopColor="#a855f7" />
              <stop offset="100%" stopColor="#ec4899" />
            </linearGradient>
          </defs>
          <circle
            cx="130"
            cy="130"
            r={RADIUS}
            fill="none"
            stroke="currentColor"
            strokeWidth="14"
            className="text-foreground/10"
          />
          <circle
            cx="130"
            cy="130"
            r={RADIUS}
            fill="none"
            stroke="url(#ringGradient)"
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
            style={{ transition: "stroke-dashoffset 1s linear" }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <AnimatePresence mode="wait">
            {isComplete ? (
              <motion.div
                key="done"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: "spring", stiffness: 260, damping: 18 }}
                className="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-500"
              >
                <Check className="h-10 w-10" />
              </motion.div>
            ) : (
              <motion.div
                key="count"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-center"
              >
                <p className="text-gradient text-7xl font-black tabular-nums">
                  {seconds}
                </p>
                <p className="mt-1 text-xs font-semibold tracking-widest text-foreground/50 uppercase">
                  seconds
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="mt-12 min-h-[7rem] w-full max-w-sm">
        <AnimatePresence mode="wait">
          {isComplete ? (
            <motion.div
              key="button"
              initial={{ opacity: 0, y: 24, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 16 }}
              className="relative flex flex-col items-center gap-3"
            >
              <motion.div
                className="relative"
                animate={{ y: [0, -6, 0] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
              >
                <span className="absolute inset-0 animate-ripple rounded-full bg-emerald-400/40" />
                <span
                  className="absolute inset-0 animate-ripple rounded-full bg-emerald-400/40"
                  style={{ animationDelay: "0.5s" }}
                />
                <button
                  type="button"
                  onClick={handleGetHD}
                  disabled={loading}
                  className="relative flex w-full cursor-pointer items-center justify-center gap-3 rounded-full bg-gradient-to-r from-emerald-500 to-green-500 px-10 py-5 text-lg font-black tracking-wide text-white shadow-[0_12px_40px_rgb(16_185_129/0.5)] transition-transform hover:scale-[1.04] active:scale-[0.97] disabled:cursor-wait disabled:opacity-80 animate-pulse-glow"
                >
                  {loading ? (
                    <Wand2 className="h-6 w-6 animate-spin" />
                  ) : (
                    <>
                      <MessageCircle className="h-6 w-6" fill="currentColor" />
                      GET HD
                    </>
                  )}
                </button>
              </motion.div>
              <p className="text-xs text-foreground/50">
                Opens WhatsApp with your HD file ready to download
              </p>
            </motion.div>
          ) : (
            <motion.p
              key="waiting"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-sm text-foreground/50"
            >
              Preparing your download link…
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
