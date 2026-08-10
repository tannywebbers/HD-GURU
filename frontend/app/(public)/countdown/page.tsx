import type { Metadata } from "next";
import { CountdownFlow } from "@/components/countdown/CountdownFlow";
import { PageTransition } from "@/components/ui/PageTransition";
import { AdPlacement } from "@/components/ads/AdPlacement";

export const metadata: Metadata = {
  title: "Getting your HD file",
  description:
    "Your enhanced HD file is being prepared for WhatsApp delivery. Grab it in a few seconds.",
};

export default function CountdownPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-6xl px-4 pt-32 pb-24 sm:px-6">
        <CountdownFlow />
        <AdPlacement name="countdown_bottom" className="mx-auto mt-10 max-w-3xl" />
      </section>
    </PageTransition>
  );
}
