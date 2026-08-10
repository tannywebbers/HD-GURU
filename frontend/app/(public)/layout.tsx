import type { Metadata } from "next";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { AnalyticsTracker } from "@/components/ads/AnalyticsTracker";
import { AdPlacement } from "@/components/ads/AdPlacement";
import { BrandingApplier } from "@/hooks/useBranding";

export const metadata: Metadata = {
  robots: {
    index: true,
    follow: true,
  },
};

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <BrandingApplier />
      <AnalyticsTracker />
      <Navbar />
      {children}
      <AdPlacement name="footer" />
      <Footer />
    </>
  );
}
