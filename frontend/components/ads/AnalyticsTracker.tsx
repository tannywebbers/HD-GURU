"use client";

import { useEffect } from "react";
import { trackEvent } from "@/services/ads";

// Mounted once per page navigation in the public layout to record an anonymous
// page view. Fire-and-forget; never blocks rendering or navigation.
export function AnalyticsTracker() {
  useEffect(() => {
    trackEvent("page_view");
  }, []);

  return null;
}
