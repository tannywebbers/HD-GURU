"use client";

import { motion, useReducedMotion } from "framer-motion";

export function AnimatedBackground() {
  const reduceMotion = useReducedMotion();

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-mesh"
    >
      <motion.div
        className="absolute -top-32 -left-32 h-[34rem] w-[34rem] rounded-full bg-primary-500/25 blur-[120px]"
        animate={reduceMotion ? undefined : { x: [0, 60, 0], y: [0, 40, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-1/3 -right-40 h-[30rem] w-[30rem] rounded-full bg-accent-500/20 blur-[120px]"
        animate={reduceMotion ? undefined : { x: [0, -50, 0], y: [0, 50, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -bottom-40 left-1/4 h-[28rem] w-[28rem] rounded-full bg-rose-500/15 blur-[120px]"
        animate={reduceMotion ? undefined : { x: [0, 40, 0], y: [0, -40, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,var(--background)_78%)]" />
    </div>
  );
}
