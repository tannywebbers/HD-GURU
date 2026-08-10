import type { FAQItem, FeatureItem } from "@/types";

export const features: FeatureItem[] = [
  {
    id: "hd-quality",
    icon: "sparkles",
    title: "True HD Quality",
    description:
      "AI-powered upscaling brings every photo and video to stunning HD clarity — sharper edges, richer detail, vivid colors.",
  },
  {
    id: "zero-compression",
    icon: "shield",
    title: "Zero Compression",
    description:
      "Your HD files are sent to WhatsApp as original documents, so the quality you see is the quality you keep.",
  },
  {
    id: "lightning-fast",
    icon: "zap",
    title: "Lightning Fast",
    description:
      "No downloads, no apps, no sign-up. Your enhanced media is delivered to WhatsApp in under a minute.",
  },
  {
    id: "privacy-first",
    icon: "lock",
    title: "Private by Design",
    description:
      "Files are processed securely and deleted automatically after delivery. We never store or share your media.",
  },
];

export const faqItems: FAQItem[] = [
  {
    question: "What is HD Guru?",
    answer:
      "HD Guru is a free tool that upscales your photos and videos to HD quality and delivers them straight to your WhatsApp. No app install, no account, no watermark on your files.",
  },
  {
    question: "Is HD Guru really free?",
    answer:
      "Yes. Enhancements, HD generation and WhatsApp delivery are completely free with no hidden charges. Your files are never sold or shared.",
  },
  {
    question: "What file types and sizes are supported?",
    answer:
      "We support common image formats (JPG, PNG, WebP, HEIC, GIF) and video formats (MP4, WebM, MOV). Each file can be up to 100MB and you can upload up to 5 files at once.",
  },
  {
    question: "How do I receive my HD file?",
    answer:
      "Once processing finishes, your countdown completes and you tap the \"Get HD\" button. It opens a WhatsApp chat with your enhanced file ready to download — sent as a document to keep full quality.",
  },
  {
    question: "Is my media private?",
    answer:
      "Your privacy is our priority. Files are processed in memory and automatically deleted shortly after delivery. We never store your photos or videos on our servers.",
  },
  {
    question: "Why do I have to wait 15 seconds?",
    answer:
      "The short countdown gives our servers a moment to finalize the HD render and hand off your file to WhatsApp. Your files are usually ready before it even finishes.",
  },
];

export const stats = [
  { value: "2M+", label: "HD files delivered" },
  { value: "4.9★", label: "Average rating" },
  { value: "99.9%", label: "Success rate" },
  { value: "180+", label: "Countries served" },
];

export const howItWorksSteps = [
  {
    step: "01",
    title: "Upload",
    description:
      "Drop in up to 5 photos or videos. We accept images and video in all common formats.",
  },
  {
    step: "02",
    title: "We enhance",
    description:
      "Our AI upscales resolution, sharpens detail and improves colors automatically.",
  },
  {
    step: "03",
    title: "Get it on WhatsApp",
    description:
      "Tap the button after the countdown and download your HD file from WhatsApp — no compression.",
  },
];

export const testimonials = [
  {
    quote:
      "Sent a blurry old family photo and got back a crisp HD version in seconds. Unbelievable for something free.",
    name: "Amara O.",
    role: "Photography enthusiast",
  },
  {
    quote:
      "Finally a tool that doesn't wreck video quality. HD Guru delivered my clip to WhatsApp perfectly.",
    name: "Daniel K.",
    role: "Content creator",
  },
];
