"use client";

import {
  BadgeCheck,
  CheckCircle2,
  FileDown,
  Loader2,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Wand2,
  type LucideIcon,
} from "lucide-react";
import type { ProcessingStageId } from "@/types";

const iconMap: Record<ProcessingStageId, LucideIcon> = {
  uploading: UploadCloud,
  preparing: ScanSearch,
  enhancing: Sparkles,
  watermark: ShieldCheck,
  compressing: BadgeCheck,
  saving: FileDown,
  generating: Wand2,
  ready: CheckCircle2,
};

interface StageIconProps {
  stage: ProcessingStageId;
  state: "done" | "active" | "pending";
  className?: string;
}

export function StageIcon({ stage, state, className }: StageIconProps) {
  const Icon = iconMap[stage];
  if (state === "active") {
    return <Loader2 className={`animate-spin ${className ?? ""}`} />;
  }
  return <Icon className={className} />;
}
