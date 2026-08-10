"use client";

import Link from "next/link";
import { Instagram, MessageCircle, Youtube } from "lucide-react";
import { Logo } from "@/components/ui/Logo";
import { useBranding } from "@/hooks/useBranding";
import { WHATSAPP_URL } from "@/lib/constants";

const footerLinks = [
  { href: "/about", label: "About" },
  { href: "/faq", label: "FAQ" },
  { href: "/contact", label: "Contact" },
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/terms", label: "Terms of Service" },
];

const socials = [
  { href: WHATSAPP_URL, label: "WhatsApp", icon: MessageCircle },
  { href: "https://instagram.com", label: "Instagram", icon: Instagram },
  { href: "https://youtube.com", label: "YouTube", icon: Youtube },
];

export function Footer() {
  const branding = useBranding();
  const appName = branding.app_name;
  return (
    <footer className="relative z-10 border-t border-white/10">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="flex flex-col gap-10 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm space-y-4">
            <Logo />
            <p className="text-sm text-foreground/60">
              {branding.app_description ||
                "Transform your photos and videos into stunning HD quality. Delivered straight to your WhatsApp — free and private."}
            </p>
            <div className="flex gap-3">
              {socials.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={social.label}
                  className="glass flex h-10 w-10 items-center justify-center rounded-full transition-transform hover:scale-110"
                >
                  <social.icon className="h-4 w-4" />
                </a>
              ))}
            </div>
          </div>

          <nav className="grid grid-cols-1 gap-x-16 gap-y-2 sm:grid-cols-2">
            {footerLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-foreground/60 transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="mt-10 border-t border-white/10 pt-6 text-center">
          <p className="text-xs text-foreground/40">
            © {new Date().getFullYear()} {appName}. All rights reserved.
            Built with care for creators.
          </p>
        </div>
      </div>
    </footer>
  );
}
