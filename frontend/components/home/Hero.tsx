"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, CheckCircle2, ImagePlus, Play, ShieldCheck } from "lucide-react";
import { GlassButton } from "@/components/ui/GlassButton";

export function Hero() {
  const reduceMotion = useReducedMotion();

  return (
    <section className="relative mx-auto flex max-w-6xl flex-col items-center px-4 pt-32 pb-16 text-center sm:px-6 lg:pt-40">
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="glass mb-6 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold text-foreground/70"
      >
        <span className="flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgb(52_211_153/0.9)]" />
        Free · No sign-up · Delivered via WhatsApp
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.05 }}
        className="max-w-4xl text-4xl font-bold tracking-tight text-balance sm:text-6xl lg:text-7xl"
      >
        Turn every photo & video into{" "}
        <span className="text-gradient">stunning HD</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.15 }}
        className="mt-6 max-w-2xl text-base text-foreground/60 sm:text-lg"
      >
        AI-powered upscaling that keeps 100% quality. Upload up to 5 files,
        wait a few seconds, and grab your crisp HD version straight from
        WhatsApp.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.25 }}
        className="mt-8 flex flex-col items-center gap-3 sm:flex-row"
      >
        <GlassButton href="/upload" size="lg">
          Enhance now <ArrowRight className="h-5 w-5" />
        </GlassButton>
        <GlassButton href="/faq" size="lg" variant="secondary">
          How it works
        </GlassButton>
      </motion.div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-foreground/50"
      >
        <span className="inline-flex items-center gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Images + Videos
        </span>
        <span className="inline-flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-primary-400" /> Auto-deleted files
        </span>
        <span className="inline-flex items-center gap-1.5">
          <ImagePlus className="h-3.5 w-3.5 text-accent-400" /> Up to 100MB each
        </span>
      </motion.p>

      <div className="relative mt-16 w-full max-w-3xl">
        <div className="glass-strong relative z-10 overflow-hidden rounded-[2rem] p-2 sm:p-3">
          <div className="relative aspect-video overflow-hidden rounded-3xl bg-gradient-to-br from-primary-600/30 via-accent-600/30 to-rose-500/30">
            <div className="absolute inset-0 bg-mesh" />
            <div className="absolute inset-0 flex items-center justify-center gap-4">
              <div className="flex flex-col items-center gap-3">
                <div className="glass flex h-16 w-16 items-center justify-center rounded-3xl">
                  <Play className="h-7 w-7 text-white" fill="currentColor" />
                </div>
                <span className="glass rounded-full px-4 py-1 text-xs font-semibold">
                  Sample video · watch the HD difference
                </span>
              </div>
            </div>
            <div className="absolute right-4 bottom-4 rounded-2xl bg-black/40 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur-md">
              1080p HD ready
            </div>
          </div>
        </div>

        {!reduceMotion && (
          <>
            <motion.div
              animate={{ y: [0, -14, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
              className="glass absolute -top-6 -left-4 z-20 hidden items-center gap-2 rounded-2xl px-4 py-3 sm:flex"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-500">
                <CheckCircle2 className="h-4 w-4" />
              </span>
              <span className="text-xs font-semibold">
                Quality preserved — zero compression
              </span>
            </motion.div>
            <motion.div
              animate={{ y: [0, 14, 0] }}
              transition={{
                duration: 6,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 1,
              }}
              className="glass absolute -right-4 -bottom-6 z-20 hidden items-center gap-2 rounded-2xl px-4 py-3 sm:flex"
            >
              <span className="text-xs font-semibold">2.1M+ files enhanced</span>
              <span className="text-gradient text-sm font-black">↑ 12%</span>
            </motion.div>
          </>
        )}
      </div>
    </section>
  );
}
