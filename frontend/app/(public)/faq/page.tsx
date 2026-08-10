import type { Metadata } from "next";
import { FAQPreview } from "@/components/home/FAQPreview";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { CTA } from "@/components/home/CTA";
import { PageTransition } from "@/components/ui/PageTransition";

export const metadata: Metadata = {
  title: "FAQ",
  description:
    "Answers to the most common questions about HD Guru — pricing, privacy, supported formats, and how WhatsApp delivery works.",
};

export default function FAQPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-6xl px-4 pt-32 pb-16 sm:px-6">
        <SectionHeading
          eyebrow="Help center"
          title={
            <>
              Frequently asked <span className="text-gradient">questions</span>
            </>
          }
          subtitle="Everything you need to know about enhancing your media with HD Guru."
        />
        <FAQPreview limit={100} />
      </section>
      <CTA />
    </PageTransition>
  );
}
