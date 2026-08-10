"use client";

import Link from "next/link";
import { useBranding } from "@/hooks/useBranding";
import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/cn";

interface LogoProps {
  className?: string;
  showWordmark?: boolean;
}

export function Logo({ className, showWordmark = true }: LogoProps) {
  const branding = useBranding();
  const name = branding.app_name || APP_NAME;
  const isDefault = name === APP_NAME;
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const firstPart = parts.slice(0, -1).join(" ");
  const lastPart = parts.length > 1 ? parts[parts.length - 1] : "";
  const badge = isDefault
    ? "HD"
    : parts.length > 1
      ? `${firstPart[0]}${lastPart[0]}`.toUpperCase()
      : name.slice(0, 2).toUpperCase();

  return (
    <Link
      href="/"
      className={cn(
        "group inline-flex items-center gap-3 select-none",
        className,
      )}
      aria-label={`${name} home`}
    >
      {branding.app_logo_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={branding.app_logo_url}
          alt={name}
          className="h-10 w-10 rounded-2xl object-cover"
        />
      ) : (
        <span className="relative flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500 via-accent-500 to-rose-500 text-white shadow-[0_8px_24px_rgb(99_102_241/0.4)] transition-transform duration-300 group-hover:scale-105">
          <span className="text-sm font-black tracking-tight">{badge}</span>
          <span className="absolute inset-0 rounded-2xl bg-white/20 opacity-0 transition-opacity group-hover:opacity-100" />
        </span>
      )}
      {showWordmark && (
        <span className="text-xl font-bold tracking-tight text-foreground">
          {firstPart && <span>{firstPart} </span>}
          <span className="text-gradient">{lastPart || name}</span>
        </span>
      )}
    </Link>
  );
}
