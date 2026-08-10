import type { Metadata } from "next";
import { LegalSection } from "@/components/ui/LegalSection";
import { PageTransition } from "@/components/ui/PageTransition";
import { APP_NAME } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "How HD Guru handles your data. We process files in memory, never store your media, and auto-delete everything after delivery.",
};

export default function PrivacyPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-4xl px-4 pt-32 pb-24 sm:px-6">
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-5xl">
            <span className="text-gradient">Privacy Policy</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-sm text-foreground/60">
            Last updated: August 2026. Your privacy is the foundation of {APP_NAME}.
          </p>
        </div>

        <div className="space-y-5">
          <LegalSection title="1. A short summary">
            <p>
              {APP_NAME} is designed so your photos and videos never become
              data for us. Files are processed only in your browser and on our
              ephemeral processing servers, and are automatically deleted
              shortly after delivery.
            </p>
          </LegalSection>

          <LegalSection title="2. What we do NOT collect">
            <p>
              We do not require an account. We do not scan, analyze, or store
              the content of your uploaded photos or videos. We do not sell,
              rent, or share your media with third parties. We do not use your
              media to train AI models.
            </p>
          </LegalSection>

          <LegalSection title="3. What we do collect">
            <p>
              To operate and improve the service, we collect minimal technical
              data such as browser type, device type, and aggregated usage
              statistics. We never combine this with your actual media files.
            </p>
          </LegalSection>

          <LegalSection title="4. File handling & retention">
            <p>
              Uploaded files are transferred over encrypted connections, held
              in memory for processing, and permanently deleted after delivery.
              Your enhanced file is delivered to you directly via WhatsApp; we
              do not keep a copy.
            </p>
          </LegalSection>

          <LegalSection title="5. WhatsApp">
            <p>
              We generate a delivery link that opens WhatsApp so you can
              download your file. We do not read, store, or monitor your
              WhatsApp chats or contacts.
            </p>
          </LegalSection>

          <LegalSection title="6. Cookies & local storage">
            <p>
              We use local storage only for your app preferences (such as theme
              choice) and your active session files, all of which stay on your
              device and never leave it. No advertising cookies are used.
            </p>
          </LegalSection>

          <LegalSection title="7. Children's privacy">
            <p>
              {APP_NAME} is not directed to children under 13, and we do not
              knowingly collect personal information from children.
            </p>
          </LegalSection>

          <LegalSection title="8. Changes to this policy">
            <p>
            We may update this policy from time to time. Material changes
            will be reflected here with an updated &ldquo;last updated&rdquo; date.
            </p>
          </LegalSection>

          <LegalSection title="9. Contact">
            <p>
              Questions about this policy? Reach us any time via our{" "}
              <a href="/contact" className="text-primary-500 underline underline-offset-4">
                contact page
              </a>
              .
            </p>
          </LegalSection>
        </div>
      </section>
    </PageTransition>
  );
}
