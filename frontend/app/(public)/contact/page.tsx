import type { Metadata } from "next";
import { ContactForm } from "@/components/contact/ContactForm";
import { PageTransition } from "@/components/ui/PageTransition";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Get in touch with the HD Guru team. Questions, feedback or support — we'd love to hear from you.",
};

export default function ContactPage() {
  return (
    <PageTransition>
      <section className="mx-auto max-w-6xl px-4 pt-32 pb-24 sm:px-6">
        <div className="mb-10 text-center">
          <span className="glass mb-4 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold tracking-wide text-primary-600 uppercase dark:text-primary-300">
            Contact us
          </span>
          <h1 className="mt-4 text-3xl font-bold tracking-tight text-balance sm:text-5xl">
            We&apos;d love to <span className="text-gradient">hear from you</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-sm text-foreground/60 sm:text-base">
            Questions, feedback or feature ideas? Send us a message and
            we&apos;ll get back to you within 24 hours.
          </p>
        </div>
        <ContactForm />
      </section>
    </PageTransition>
  );
}
