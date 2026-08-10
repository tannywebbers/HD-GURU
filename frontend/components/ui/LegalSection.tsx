import type { ReactNode } from "react";

interface LegalSectionProps {
  title: string;
  children: ReactNode;
}

export function LegalSection({ title, children }: LegalSectionProps) {
  return (
    <section className="glass rounded-3xl p-6 sm:p-8">
      <h2 className="text-lg font-bold text-foreground sm:text-xl">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-foreground/60 sm:text-base">
        {children}
      </div>
    </section>
  );
}
