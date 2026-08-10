import type { Metadata } from "next";
import { ResultFlow } from "@/components/result/ResultFlow";
import { PageTransition } from "@/components/ui/PageTransition";
import { AdPlacement } from "@/components/ads/AdPlacement";

export const metadata: Metadata = {
  title: "Your HD file is ready",
  description:
    "Your enhanced HD photo or video is ready. Open WhatsApp to download it in full quality.",
};

export default function ResultPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-6xl px-4 pt-32 pb-24 sm:px-6">
        <AdPlacement name="result_top" className="mx-auto mb-10 max-w-3xl" />
        <ResultFlow />
        <AdPlacement name="result_bottom" className="mx-auto mt-10 max-w-3xl" />
      </section>
    </PageTransition>
  );
}
