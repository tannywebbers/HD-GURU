"use client";

import {
  Lock,
  Shield,
  Sparkles,
  Zap,
  type LucideIcon,
} from "lucide-react";

const iconMap: Record<string, LucideIcon> = {
  sparkles: Sparkles,
  shield: Shield,
  zap: Zap,
  lock: Lock,
};

interface FeatureIconProps {
  name: string;
  className?: string;
}

export function FeatureIcon({ name, className }: FeatureIconProps) {
  const Icon = iconMap[name] ?? Sparkles;
  return <Icon className={className} />;
}
