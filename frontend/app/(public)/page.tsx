import type { Metadata } from "next";
import { Hero } from "@/components/home/Hero";
import { FeatureGrid } from "@/components/home/FeatureGrid";
import { HowItWorks } from "@/components/home/HowItWorks";
import { Testimonials } from "@/components/home/Testimonials";
import { FAQPreview } from "@/components/home/FAQPreview";
import { CTA } from "@/components/home/CTA";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { GlassButton } from "@/components/ui/GlassButton";
import { PageTransition } from "@/components/ui/PageTransition";
import { AdPlacement } from "@/components/ads/AdPlacement";

export const metadata: Metadata = {
  title: "HD Guru — Free AI HD Photo & Video Enhancer",
  description:
    "Transform your photos and videos into stunning HD quality in seconds. Free, private, and delivered straight to WhatsApp.",
};

export default function HomePage() {
  return (
    <PageTransition>
      <Hero />
      <AdPlacement name="landing_top" className="mx-auto max-w-3xl px-4 py-4 sm:px-6" />
      <FeatureGrid />
      <HowItWorks />
      <Testimonials />
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <SectionHeading
          eyebrow="Questions"
          title={
            <>
              Frequently asked <span className="text-gradient">questions</span>
            </>
          }
          subtitle="Everything you need to know about enhancing your media with HD Guru."
        />
        <FAQPreview limit={4} />
        <div className="mt-8 text-center">
          <GlassButton href="/faq" variant="secondary">
            View all questions
          </GlassButton>
        </div>
      </section>
      <AdPlacement name="landing_bottom" className="mx-auto max-w-3xl px-4 py-4 sm:px-6" />
      <CTA />
    </PageTransition>
  );
}
