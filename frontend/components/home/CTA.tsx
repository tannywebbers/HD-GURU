"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { GlassButton } from "@/components/ui/GlassButton";

export function CTA() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="glass-strong relative overflow-hidden rounded-[2.5rem] px-6 py-16 text-center sm:px-12"
      >
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary-600/20 via-accent-600/15 to-rose-500/20" />
        <div className="relative">
          <h2 className="mx-auto max-w-2xl text-3xl font-bold tracking-tight text-balance sm:text-5xl">
            Your photos deserve to be <span className="text-gradient">seen in HD</span>
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-sm text-foreground/60 sm:text-base">
            Join millions who&apos;ve upgraded their media quality — free, fast, and
            delivered to WhatsApp.
          </p>
          <div className="mt-8 flex justify-center">
            <GlassButton href="/upload" size="lg">
              Start enhancing <ArrowRight className="h-5 w-5" />
            </GlassButton>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
