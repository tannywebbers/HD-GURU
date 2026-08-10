import type { Metadata } from "next";
import { UploadZone } from "@/components/upload/UploadZone";
import { PageTransition } from "@/components/ui/PageTransition";
import { AdPlacement } from "@/components/ads/AdPlacement";

export const metadata: Metadata = {
  title: "Upload",
  description:
    "Upload up to 5 photos or videos to enhance to HD quality. Images and videos up to 100MB supported.",
};

export default function UploadPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-6xl px-4 pt-32 pb-24 sm:px-6">
        <div className="mb-10 text-center">
          <span className="glass mb-4 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold tracking-wide text-primary-600 uppercase dark:text-primary-300">
            Step 1 of 4 · Upload
          </span>
          <h1 className="mt-4 text-3xl font-bold tracking-tight text-balance sm:text-5xl">
            Choose your media
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-sm text-foreground/60 sm:text-base">
            Upload up to 5 photos or videos. We&apos;ll enhance them to stunning
            HD and send them straight to your WhatsApp.
          </p>
        </div>
        <UploadZone />
        <AdPlacement name="upload_bottom" className="mx-auto mt-10 max-w-3xl" />
      </section>
    </PageTransition>
  );
}
