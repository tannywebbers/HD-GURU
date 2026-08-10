import type { MetadataRoute } from "next";
import { APP_DESCRIPTION, APP_NAME, APP_URL } from "@/lib/constants";

// The manifest is generated at request time so Admin → Settings branding
// (app.name / app.description / app.theme_color) is reflected in the PWA
// install prompt. Results are cached in-memory for a short window so the
// backend is not hit on every manifest request, and any failure falls back to
// the compiled-in defaults.

interface Branding {
  app_name: string;
  app_description: string;
  app_logo_url: string | null;
  app_theme_color: string | null;
  app_primary_color: string | null;
}

const TTL_MS = 5 * 60 * 1000;
const FETCH_TIMEOUT_MS = 4000;

let cached: { at: number; data: Branding } | null = null;

async function runtimeBranding(): Promise<Branding> {
  if (cached && Date.now() - cached.at < TTL_MS) return cached.data;

  const base = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
  if (base) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
      const res = await fetch(`${base}/api/v1/settings/public`, {
        signal: controller.signal,
        next: { revalidate: 300 },
      });
      clearTimeout(timer);
      if (res.ok) {
        const data = (await res.json()) as Branding;
        cached = { at: Date.now(), data };
        return data;
      }
    } catch {
      // backend unreachable — fall through to defaults
    }
  }

  return {
    app_name: APP_NAME,
    app_description: APP_DESCRIPTION,
    app_logo_url: null,
    app_theme_color: null,
    app_primary_color: null,
  };
}

export default async function manifest(): Promise<MetadataRoute.Manifest> {
  const branding = await runtimeBranding();
  return {
    name: branding.app_name,
    short_name: branding.app_name,
    description: branding.app_description,
    id: "/",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#05050a",
    theme_color: branding.app_theme_color ?? "#05050a",
    categories: ["photo", "video", "utilities", "productivity"],
    lang: "en",
    dir: "ltr",
    icons: [
      {
        src: `${APP_URL}/icon-192.png`,
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: `${APP_URL}/icon-512.png`,
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: `${APP_URL}/icon-512.png`,
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: `${APP_URL}/apple-touch-icon.png`,
        sizes: "180x180",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
