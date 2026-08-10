import type { Metadata } from "next";
import { Heart, ShieldCheck, Sparkles, Zap } from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { CTA } from "@/components/home/CTA";
import { PageTransition } from "@/components/ui/PageTransition";

export const metadata: Metadata = {
  title: "About",
  description:
    "HD Guru makes pro-level HD enhancement free and effortless for everyone. Learn about our mission, values and how we keep your media private.",
};

const values = [
  {
    icon: Sparkles,
    title: "Quality first",
    description:
      "Every pixel matters. We obsess over sharpness, color and clarity so your media looks its absolute best.",
  },
  {
    icon: ShieldCheck,
    title: "Privacy by default",
    description:
      "Your files belong to you. We process them in memory, never store them, and auto-delete everything after delivery.",
  },
  {
    icon: Zap,
    title: "Speed that respects you",
    description:
      "No bloated apps, no accounts, no waiting. Upload, enhance, and get your HD file on WhatsApp in under a minute.",
  },
  {
    icon: Heart,
    title: "Free, forever",
    description:
      "Great quality shouldn't be paywalled. HD Guru stays free for everyone, everywhere.",
  },
];

export default function AboutPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-6xl px-4 pt-32 pb-16 sm:px-6">
        <SectionHeading
          eyebrow="Our story"
          title={
            <>
              Making <span className="text-gradient">HD effortless</span> for
              everyone
            </>
          }
          subtitle="We believe everyone deserves to share memories in the best possible quality — without paying for it."
        />

        <div className="mt-14 grid gap-5 sm:grid-cols-2">
          {values.map((value) => (
            <div
              key={value.title}
              className="glass rounded-3xl p-8 transition-all duration-300 hover:-translate-y-1 hover:shadow-glow"
            >
              <span className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 text-primary-600 dark:text-primary-300">
                <value.icon className="h-6 w-6" />
              </span>
              <h2 className="mb-2 text-lg font-semibold text-foreground">
                {value.title}
              </h2>
              <p className="text-sm leading-relaxed text-foreground/60">
                {value.description}
              </p>
            </div>
          ))}
        </div>

        <div className="glass-strong mt-10 rounded-[2rem] p-8 sm:p-12">
          <h2 className="text-2xl font-bold text-foreground">
            Born from a blurry photo
          </h2>
          <div className="mt-4 space-y-4 text-sm leading-relaxed text-foreground/60 sm:text-base">
            <p>
              HD Guru started with a simple frustration: a priceless family
              photo that no phone, app or service could restore to the crisp,
              beautiful quality it deserved. Either the tools were expensive,
              clunky, or they shredded quality the moment they touched
              WhatsApp.
            </p>
            <p>
              So we built the tool we wished existed. A fast, free, no-app
              enhancer that upscales photos and videos to true HD and delivers
              them where people already talk and share — WhatsApp — as
              uncompressed documents.
            </p>
            <p>
              Today, millions of creators, families and businesses rely on HD
              Guru to make their media look as good as the moments they
              captured.
            </p>
          </div>
        </div>
      </section>
      <CTA />
    </PageTransition>
  );
}
