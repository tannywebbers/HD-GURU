"use client";

import { motion } from "framer-motion";
import { features } from "@/services/mockData";
import { FeatureIcon } from "@/components/ui/FeatureIcon";
import { SectionHeading } from "@/components/ui/SectionHeading";

export function FeatureGrid() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <SectionHeading
        eyebrow="Why HD Guru"
        title={
          <>
            Everything you need for{" "}
            <span className="text-gradient">crystal-clear media</span>
          </>
        }
        subtitle="Engineered for quality, built for privacy, and delivered where you already are — WhatsApp."
      />

      <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((feature, i) => (
          <motion.div
            key={feature.id}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
            className="glass group rounded-3xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-glow"
          >
            <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 text-primary-600 transition-transform duration-300 group-hover:scale-110 dark:text-primary-300">
              <FeatureIcon name={feature.icon} className="h-6 w-6" />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-foreground">
              {feature.title}
            </h3>
            <p className="text-sm leading-relaxed text-foreground/60">
              {feature.description}
            </p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
