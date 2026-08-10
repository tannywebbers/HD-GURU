"use client";

import { motion } from "framer-motion";
import { Home, Search } from "lucide-react";
import { GlassButton } from "@/components/ui/GlassButton";

export default function NotFound() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-1 flex-col items-center justify-center px-4 pt-32 pb-24 text-center"
    >
      <motion.p
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="text-gradient text-8xl font-black sm:text-9xl"
      >
        404
      </motion.p>
      <h1 className="mt-4 text-2xl font-bold tracking-tight text-foreground sm:text-4xl">
        Page not found
      </h1>
      <p className="mx-auto mt-3 max-w-md text-sm text-foreground/60 sm:text-base">
        The page you&apos;re looking for was moved, deleted, or never existed.
        Let&apos;s get you back to sharper photos.
      </p>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <GlassButton href="/" size="lg">
          <Home className="h-4 w-4" /> Back home
        </GlassButton>
        <GlassButton href="/upload" size="lg" variant="secondary">
          <Search className="h-4 w-4" /> Enhance a photo
        </GlassButton>
      </div>
    </motion.section>
  );
}
