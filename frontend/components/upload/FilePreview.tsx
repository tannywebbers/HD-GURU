"use client";

import { motion } from "framer-motion";
import { Film, Image as ImageIcon, X } from "lucide-react";
import type { MediaFile } from "@/types";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/cn";

interface FilePreviewProps {
  file: MediaFile;
  onRemove: (id: string) => void;
}

export function FilePreview({ file, onRemove }: FilePreviewProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      className="glass group relative overflow-hidden rounded-2xl p-2"
    >
      <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-foreground/5">
        {file.previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={file.previewUrl}
            alt={file.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            {file.kind === "video" ? (
              <Film className="h-10 w-10 text-foreground/30" />
            ) : (
              <ImageIcon className="h-10 w-10 text-foreground/30" />
            )}
          </div>
        )}
        <span
          className={cn(
            "absolute top-2 left-2 inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-bold text-white uppercase backdrop-blur-md",
            file.kind === "video" ? "bg-accent-600/80" : "bg-primary-600/80",
          )}
        >
          {file.kind}
        </span>
        <button
          type="button"
          onClick={() => onRemove(file.id)}
          aria-label={`Remove ${file.name}`}
          className="absolute top-2 right-2 flex h-7 w-7 cursor-pointer items-center justify-center rounded-full bg-black/50 text-white opacity-0 backdrop-blur-md transition-opacity group-hover:opacity-100"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="px-2 py-2">
        <p className="truncate text-xs font-semibold text-foreground">
          {file.name}
        </p>
        <p className="text-[11px] text-foreground/50">
          {formatBytes(file.size)}
        </p>
      </div>
    </motion.div>
  );
}
