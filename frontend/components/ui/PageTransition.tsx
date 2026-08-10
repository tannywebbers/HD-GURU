"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { fadeIn } from "@/animations/variants";

export function PageTransition({ children }: { children: ReactNode }) {
  return (
    <motion.main
      variants={fadeIn}
      initial="hidden"
      animate="visible"
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="flex-1"
    >
      {children}
    </motion.main>
  );
}
