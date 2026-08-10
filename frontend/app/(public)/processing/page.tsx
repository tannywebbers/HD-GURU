import type { Metadata } from "next";
import { ProcessingFlow } from "@/components/processing/ProcessingFlow";
import { PageTransition } from "@/components/ui/PageTransition";
import { AdPlacement } from "@/components/ads/AdPlacement";

export const metadata: Metadata = {
  title: "Processing",
  description:
    "Your media is being enhanced to HD quality. We're upscaling resolution, improving detail and preparing your file for WhatsApp.",
};

export default function ProcessingPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-6xl px-4 pt-32 pb-24 sm:px-6">
        <ProcessingFlow />
        <AdPlacement name="processing_bottom" className="mx-auto mt-10 max-w-3xl" />
      </section>
    </PageTransition>
  );
}
