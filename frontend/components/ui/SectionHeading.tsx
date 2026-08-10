"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { fadeUp } from "@/animations/variants";

interface SectionHeadingProps {
  eyebrow?: string;
  title: ReactNode;
  subtitle?: ReactNode;
  align?: "center" | "left";
  className?: string;
}

export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = "center",
  className,
}: SectionHeadingProps) {
  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      className={`flex flex-col gap-4 ${
        align === "center" ? "items-center text-center" : "items-start"
      } ${className ?? ""}`}
    >
      {eyebrow && (
        <span className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold tracking-wide text-primary-600 uppercase dark:text-primary-300">
          {eyebrow}
        </span>
      )}
      <h2 className="max-w-2xl text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
        {title}
      </h2>
      {subtitle && (
        <p className="max-w-xl text-base text-foreground/60 sm:text-lg">
          {subtitle}
        </p>
      )}
    </motion.div>
  );
}
