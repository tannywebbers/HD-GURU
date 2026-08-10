"use client";

import { useEffect, useState } from "react";
import {
  applyBrandingToDocument,
  defaultBranding,
  fetchBranding,
  getCachedBranding,
  type Branding,
} from "@/services/branding";

export function useBranding(): Branding {
  const [branding, setBranding] = useState<Branding>(
    () => getCachedBranding() ?? defaultBranding(),
  );

  useEffect(() => {
    let active = true;
    void fetchBranding().then((next) => {
      if (active) setBranding(next);
    });
    return () => {
      active = false;
    };
  }, []);

  return branding;
}

export function BrandingApplier() {
  const branding = useBranding();

  useEffect(() => {
    applyBrandingToDocument(branding);
  }, [branding]);

  return null;
}
