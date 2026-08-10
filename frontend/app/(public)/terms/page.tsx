import type { Metadata } from "next";
import { LegalSection } from "@/components/ui/LegalSection";
import { PageTransition } from "@/components/ui/PageTransition";
import { APP_NAME } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "The terms that govern your use of HD Guru, the free HD photo and video enhancer.",
};

export default function TermsPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-4xl px-4 pt-32 pb-24 sm:px-6">
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-5xl">
            <span className="text-gradient">Terms of Service</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-sm text-foreground/60">
            Last updated: August 2026. Please read these terms before using {APP_NAME}.
          </p>
        </div>

        <div className="space-y-5">
          <LegalSection title="1. Acceptance of terms">
            <p>
              By accessing or using {APP_NAME} you agree to be bound by these
              Terms of Service and our Privacy Policy. If you do not agree,
              please do not use the service.
            </p>
          </LegalSection>

          <LegalSection title="2. The service">
            <p>
              {APP_NAME} provides a free, web-based tool to enhance photos and
              videos to higher quality and deliver the results via WhatsApp. We
              may update, modify, or discontinue features at any time.
            </p>
          </LegalSection>

          <LegalSection title="3. Acceptable use">
            <p>
              You agree to upload only content you own or have the right to
              use, and not to upload illegal, infringing, or offensive content.
              You may not attempt to disrupt, overload, or reverse-engineer the
              service.
            </p>
          </LegalSection>

          <LegalSection title="4. Intellectual property">
            <p>
              You retain full ownership of your content. {APP_NAME} claims no
              ownership over your uploaded or enhanced files. The HD Guru name,
              logo, and interface are the property of {APP_NAME}.
            </p>
          </LegalSection>

          <LegalSection title="5. Disclaimers">
            <p>
              The service is provided &ldquo;as is&rdquo; without warranties of any kind.
              While we aim for outstanding results, we do not guarantee specific
              output quality, uptime, or uninterrupted availability.
            </p>
          </LegalSection>

          <LegalSection title="6. Limitation of liability">
            <p>
              To the maximum extent permitted by law, {APP_NAME} shall not be
              liable for any indirect, incidental, or consequential damages
              arising from your use of the service.
            </p>
          </LegalSection>

          <LegalSection title="7. Third-party links">
            <p>
              The service links to WhatsApp and other third-party services. We
              are not responsible for the practices or content of third-party
              websites.
            </p>
          </LegalSection>

          <LegalSection title="8. Changes to these terms">
            <p>
              We may revise these terms periodically. Continued use of the
              service after changes constitutes acceptance of the updated
              terms.
            </p>
          </LegalSection>

          <LegalSection title="9. Contact">
            <p>
              Have questions about these terms? Reach us via our{" "}
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
