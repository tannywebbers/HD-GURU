"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { faqItems } from "@/services/mockData";
import { cn } from "@/lib/cn";

export function FAQPreview({ limit = 4 }: { limit?: number }) {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const items = faqItems.slice(0, limit);

  return (
    <div className="mx-auto mt-10 max-w-3xl space-y-3">
      {items.map((item, i) => {
        const open = openIndex === i;
        return (
          <div
            key={item.question}
            className={cn(
              "glass overflow-hidden rounded-3xl transition-all duration-300",
              open && "shadow-glow",
            )}
          >
            <button
              type="button"
              onClick={() => setOpenIndex(open ? null : i)}
              aria-expanded={open}
              className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
            >
              <span className="text-sm font-semibold text-foreground sm:text-base">
                {item.question}
              </span>
              <span
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500/10 text-primary-600 transition-transform duration-300 dark:text-primary-300",
                  open && "rotate-180",
                )}
              >
                <ChevronDown className="h-4 w-4" />
              </span>
            </button>
            <AnimatePresence initial={false}>
              {open && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3, ease: "easeInOut" }}
                  className="overflow-hidden"
                >
                  <p className="px-6 pb-5 text-sm leading-relaxed text-foreground/60">
                    {item.answer}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
