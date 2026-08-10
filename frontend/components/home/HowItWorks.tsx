"use client";

import { motion } from "framer-motion";
import { howItWorksSteps, stats } from "@/services/mockData";
import { SectionHeading } from "@/components/ui/SectionHeading";

export function HowItWorks() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <SectionHeading
        eyebrow="How it works"
        title={
          <>
            HD quality in <span className="text-gradient">three steps</span>
          </>
        }
        subtitle="From blurry to breathtaking in under a minute."
      />

      <div className="relative mt-14 grid gap-6 md:grid-cols-3">
        <div className="absolute top-1/2 left-8 right-8 hidden h-px -translate-y-1/2 bg-gradient-to-r from-transparent via-primary-500/40 to-transparent md:block" />
        {howItWorksSteps.map((step, i) => (
          <motion.div
            key={step.step}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            className="relative text-center"
          >
            <div className="glass-strong relative z-10 mx-auto flex h-16 w-16 items-center justify-center rounded-3xl">
              <span className="text-gradient text-xl font-black">
                {step.step}
              </span>
            </div>
            <h3 className="mt-5 text-lg font-semibold text-foreground">
              {step.title}
            </h3>
            <p className="mx-auto mt-2 max-w-xs text-sm leading-relaxed text-foreground/60">
              {step.description}
            </p>
          </motion.div>
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="glass mt-16 grid grid-cols-2 divide-x divide-white/10 rounded-3xl py-8 sm:grid-cols-4"
      >
        {stats.map((stat) => (
          <div key={stat.label} className="px-4 py-4 text-center">
            <p className="text-gradient text-3xl font-black sm:text-4xl">
              {stat.value}
            </p>
            <p className="mt-1 text-xs font-medium text-foreground/50 sm:text-sm">
              {stat.label}
            </p>
          </div>
        ))}
      </motion.div>
    </section>
  );
}
