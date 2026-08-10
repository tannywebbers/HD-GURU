import withPWA from "next-pwa";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL(".", import.meta.url));

const withPWAConfig = withPWA({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  runtimeCaching: [
    {
      urlPattern: /^https?.*\/_next\/static\/.*/i,
      handler: "StaleWhileRevalidate",
      options: {
        cacheName: "static-assets",
        expiration: { maxEntries: 64, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
    {
      urlPattern: /^https?.*\/icons\/.*/i,
      handler: "CacheFirst",
      options: {
        cacheName: "app-icons",
        expiration: { maxEntries: 32, maxAgeSeconds: 365 * 24 * 60 * 60 },
      },
    },
    {
      urlPattern: /^https?.*\.(?:png|jpg|jpeg|svg|gif|webp|avif)$/i,
      handler: "CacheFirst",
      options: {
        cacheName: "images",
        expiration: { maxEntries: 64, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
    {
      urlPattern: /^https?.*\.(?:woff|woff2|ttf|otf|eot)$/i,
      handler: "CacheFirst",
      options: {
        cacheName: "fonts",
        expiration: { maxEntries: 16, maxAgeSeconds: 365 * 24 * 60 * 60 },
      },
    },
  ],
  cleanupOutdatedCaches: true,
  navigateFallback: "/offline",
  navigateFallbackDenylist: [
    /\/_next\/data\//,
    /\/api\//,
    /\/[^/]+\.[^/]+$/,
  ],
});

/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  compress: true,
  poweredByHeader: false,
  outputFileTracingRoot: path.resolve(projectRoot),
  images: {
    formats: ["image/avif", "image/webp"],
  },
};

export default withPWAConfig(nextConfig);
