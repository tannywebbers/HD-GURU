import type { ProcessingStage } from "@/types";

export const APP_NAME = "HD Guru";

export const APP_DESCRIPTION =
  "Transform your photos and videos into stunning HD quality in seconds. Free, private, and delivered straight to WhatsApp.";

// Public origin of the deployed frontend. Override per environment with
// NEXT_PUBLIC_APP_URL; falls back to the default Vercel URL. Used for
// metadata, sitemap/robots and PWA manifest icon URLs. Never put secrets here.
export const APP_URL = (
  process.env.NEXT_PUBLIC_APP_URL ?? "https://hdguru.vercel.app"
).replace(/\/+$/, "");

// Generic WhatsApp entry point. The click-to-chat number is always supplied by
// the backend (public config / result payload) so no business number lives in
// the frontend bundle.
export const WHATSAPP_URL = "https://wa.me/";

export const COUNTDOWN_SECONDS = 15;

export const MAX_FILES = 5;

export const MAX_FILE_SIZE_MB = 100;

export const ACCEPTED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
  "image/gif",
];

export const ACCEPTED_VIDEO_TYPES = [
  "video/mp4",
  "video/webm",
  "video/quicktime",
  "video/x-m4v",
];

export const PROCESSING_STAGES: ProcessingStage[] = [
  {
    id: "uploading",
    label: "Uploading",
    description: "Uploading your files securely",
  },
  {
    id: "preparing",
    label: "Preparing",
    description: "Analyzing your media files",
  },
  {
    id: "enhancing",
    label: "Enhancing Quality",
    description: "Upscaling resolution & sharpness",
  },
  {
    id: "watermark",
    label: "Applying Watermark",
    description: "Protecting your HD Guru content",
  },
  {
    id: "compressing",
    label: "Compressing",
    description: "Optimizing size for WhatsApp",
  },
  {
    id: "saving",
    label: "Saving",
    description: "Writing the final HD file",
  },
  {
    id: "generating",
    label: "Generating HD Version",
    description: "Rendering your HD masterpiece",
  },
  {
    id: "ready",
    label: "Ready",
    description: "Your HD file is ready",
  },
];
