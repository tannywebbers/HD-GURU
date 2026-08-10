"use client";

import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

export type GlassButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: GlassButtonVariant;
  href?: string;
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children: ReactNode;
  onClick?: () => void;
}

const sizeClasses: Record<NonNullable<GlassButtonProps["size"]>, string> = {
  sm: "px-4 py-2 text-sm rounded-xl",
  md: "px-6 py-3 text-sm rounded-2xl",
  lg: "px-8 py-4 text-base rounded-2xl",
};

const variantClasses: Record<GlassButtonVariant, string> = {
  primary:
    "bg-gradient-to-r from-primary-600 via-accent-600 to-rose-500 bg-[length:200%_auto] text-white shadow-[0_8px_32px_rgb(99_102_241/0.4)] hover:bg-[position:right_center] hover:shadow-[0_8px_40px_rgb(168_85_247/0.5)] active:scale-[0.98]",
  secondary:
    "glass text-foreground hover:bg-white/80 dark:hover:bg-white/10 active:scale-[0.98]",
  ghost:
    "text-foreground/80 hover:bg-foreground/5 hover:text-foreground active:scale-[0.98]",
  danger:
    "bg-rose-500/90 text-white hover:bg-rose-500 active:scale-[0.98] shadow-[0_8px_24px_rgb(244_63_94/0.35)]",
};

export function GlassButton({
  variant = "primary",
  size = "md",
  href,
  loading = false,
  className,
  children,
  disabled,
  onClick,
  ...props
}: GlassButtonProps) {
  const classes = cn(
    "inline-flex cursor-pointer items-center justify-center gap-2 font-semibold transition-all duration-300 select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 disabled:cursor-not-allowed disabled:opacity-60",
    sizeClasses[size],
    variantClasses[variant],
    className,
  );

  const content = (
    <>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </>
  );

  if (href) {
    return (
      <Link href={href} onClick={onClick} className={classes}>
        {content}
      </Link>
    );
  }

  return (
    <button
      className={classes}
      disabled={disabled || loading}
      onClick={onClick}
      {...props}
    >
      {content}
    </button>
  );
}
