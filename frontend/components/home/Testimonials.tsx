"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { GlassButton } from "@/components/ui/GlassButton";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { testimonials } from "@/services/mockData";

export function Testimonials() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <SectionHeading
        eyebrow="Loved by creators"
        title={
          <>
            Trusted by <span className="text-gradient">millions</span>
          </>
        }
        subtitle="Real people, real photos, real HD transformations."
      />

      <div className="mt-12 grid gap-5 md:grid-cols-2">
        {testimonials.map((t, i) => (
          <motion.figure
            key={t.name}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            className="glass rounded-3xl p-8"
          >
            <div className="mb-4 flex gap-1 text-amber-400" aria-label="5 star rating">
              {Array.from({ length: 5 }).map((_, j) => (
                <span key={j}>★</span>
              ))}
            </div>
            <blockquote className="text-base leading-relaxed text-foreground/80">
              &ldquo;{t.quote}&rdquo;
            </blockquote>
            <figcaption className="mt-6 flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-primary-500 to-accent-500 text-sm font-bold text-white">
                {t.name.charAt(0)}
              </span>
              <div>
                <p className="text-sm font-semibold text-foreground">
                  {t.name}
                </p>
                <p className="text-xs text-foreground/50">{t.role}</p>
              </div>
            </figcaption>
          </motion.figure>
        ))}
      </div>

      <div className="mt-12 text-center">
        <GlassButton href="/faq" variant="secondary">
          Read the FAQ <ArrowRight className="h-4 w-4" />
        </GlassButton>
      </div>
    </section>
  );
}
