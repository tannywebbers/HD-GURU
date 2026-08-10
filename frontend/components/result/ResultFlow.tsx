"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import Lottie from "lottie-react";
import {
  ArrowDownToLine,
  CheckCircle2,
  Download,
  MessageCircle,
  RefreshCcw,
  Timer,
} from "lucide-react";
import { GlassButton } from "@/components/ui/GlassButton";
import { loadResult } from "@/lib/resultStore";
import { clearFiles } from "@/lib/fileStore";
import { formatBytes, formatDuration } from "@/lib/format";
import { trackEvent } from "@/services/ads";
import type { HDResult } from "@/types";
import successAnimation from "@/public/lottie/success.json";

export function ResultFlow() {
  const router = useRouter();
  const [result, setResult] = useState<HDResult | null>(null);

  useEffect(() => {
    const stored = loadResult();
    if (!stored) {
      router.replace("/upload");
      return;
    }
    setResult(stored);
    clearFiles();
  }, [router]);

  if (!result) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-foreground/50">
        Loading your result…
      </div>
    );
  }

  const savingsPercent = result.originalSize > 0
    ? Math.max(0, Math.round((1 - result.outputSize / result.originalSize) * 100))
    : 0;

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 16 }}
        className="relative"
      >
        <div className="h-40 w-40">
          <Lottie
            animationData={successAnimation}
            loop={false}
            className="h-full w-full"
          />
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-balance sm:text-5xl">
          <span className="text-gradient">Success!</span> Your HD file is ready
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-sm text-foreground/60 sm:text-base">
          Your enhanced file is ready. Open WhatsApp to download it in full HD
          — no compression, no quality loss.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.5 }}
        className="glass-strong mt-10 w-full overflow-hidden rounded-[2rem]"
      >
        <div className="relative aspect-video bg-gradient-to-br from-primary-600/30 via-accent-600/30 to-rose-500/30">
          <div className="absolute inset-0 bg-mesh" />
          {result.thumbnailUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={result.thumbnailUrl}
              alt={result.title}
              className="absolute inset-0 h-full w-full object-cover"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <CheckCircle2 className="h-16 w-16 text-white/70" />
            </div>
          )}
          <span className="glass absolute top-4 left-4 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold text-white uppercase">
            <CheckCircle2 className="h-3.5 w-3.5" /> HD Ready
          </span>
        </div>

        <div className="grid grid-cols-3 divide-x divide-white/10 px-6 py-5 text-center">
          <div>
            <p className="text-lg font-black text-foreground">
              {result.originalSize > 0 ? formatBytes(result.outputSize) : "HD"}
            </p>
            <p className="text-[11px] text-foreground/50">Output size</p>
          </div>
          <div>
            <p className="text-lg font-black text-foreground">
              {result.originalSize > 0 ? `${savingsPercent}%` : "—"}
            </p>
            <p className="text-[11px] text-foreground/50">Smaller</p>
          </div>
          <div>
            <p className="inline-flex items-center gap-1 text-lg font-black text-foreground">
              <Timer className="h-4 w-4" />
              {result.duration ? formatDuration(result.duration) : "HD"}
            </p>
            <p className="text-[11px] text-foreground/50">Duration</p>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.5 }}
        className="mt-8 flex w-full flex-col gap-3 sm:max-w-md"
      >
        <AnimatePresence>
          <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <GlassButton
              href={result.whatsappUrl}
              size="lg"
              onClick={() => trackEvent("whatsapp_opened")}
              className="w-full bg-gradient-to-r from-emerald-500 to-green-500 shadow-[0_12px_40px_rgb(16_185_129/0.45)]"
            >
              <MessageCircle className="h-5 w-5" fill="currentColor" />
              Open WhatsApp
            </GlassButton>
          </motion.div>
        </AnimatePresence>
        <div className="flex gap-3">
          <GlassButton
            href={result.downloadUrl}
            size="lg"
            variant="secondary"
            className="flex-1"
          >
            <Download className="h-4 w-4" /> Direct download
          </GlassButton>
          <GlassButton
            size="lg"
            variant="secondary"
            className="flex-1"
            onClick={() => router.push("/upload")}
          >
            <RefreshCcw className="h-4 w-4" /> Upload another
          </GlassButton>
        </div>
        <p className="mt-2 flex items-center justify-center gap-1.5 text-xs text-foreground/50">
          <ArrowDownToLine className="h-3.5 w-3.5" />
          Save the file from WhatsApp to your device for permanent HD quality
        </p>
      </motion.div>
    </div>
  );
}
