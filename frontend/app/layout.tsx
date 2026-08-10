import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Providers } from "@/components/Providers";
import { AnimatedBackground } from "@/components/ui/AnimatedBackground";
import { APP_DESCRIPTION, APP_NAME, APP_URL } from "@/lib/constants";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(APP_URL),
  title: {
    default: `${APP_NAME} — Free AI HD Photo & Video Enhancer`,
    template: `%s | ${APP_NAME}`,
  },
  description: APP_DESCRIPTION,
  keywords: [
    "HD photo enhancer",
    "HD video upscaler",
    "AI image quality",
    "WhatsApp HD",
    "free photo enhancer",
    "video quality booster",
  ],
  authors: [{ name: APP_NAME }],
  openGraph: {
    type: "website",
    url: APP_URL,
    siteName: APP_NAME,
    title: `${APP_NAME} — Free AI HD Photo & Video Enhancer`,
    description: APP_DESCRIPTION,
    images: [{ url: `${APP_URL}/icon-512.png`, width: 512, height: 512 }],
  },
  twitter: {
    card: "summary_large_image",
    title: `${APP_NAME} — Free AI HD Photo & Video Enhancer`,
    description: APP_DESCRIPTION,
    images: [`${APP_URL}/icon-512.png`],
  },
  robots: {
    index: true,
    follow: true,
  },
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: APP_NAME,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f5fb" },
    { media: "(prefers-color-scheme: dark)", color: "#05050a" },
  ],
};

const themeScript = `
try {
  var stored = localStorage.getItem("hdguru-theme");
  var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  var theme = stored === "light" || stored === "dark" ? stored : (prefersDark ? "dark" : "light");
  var root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  root.style.colorScheme = theme;
} catch (e) {}
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="flex min-h-full flex-col">
        <Providers>
          <AnimatedBackground />
          {children}
        </Providers>
      </body>
    </html>
  );
}
