"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import Lottie from "lottie-react";
import { Check, Film, Image as ImageIcon } from "lucide-react";
import { StageIcon } from "@/components/processing/StageIcon";
import { PROCESSING_STAGES } from "@/lib/constants";
import { STAGE_DURATION_MS } from "@/services/api";
import { loadFiles } from "@/lib/fileStore";
import { formatBytes } from "@/lib/format";
import { trackEvent } from "@/services/ads";
import type { StoredMediaFile } from "@/types";
import { cn } from "@/lib/cn";
import loaderAnimation from "@/public/lottie/loader.json";

const FINISH_HOLD_MS = 1200;

export function ProcessingFlow() {
  const router = useRouter();
  const [files, setFiles] = useState<StoredMediaFile[]>([]);
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const stored = loadFiles();
    if (stored.length === 0) {
      router.replace("/upload");
      return;
    }
    setFiles(stored);
  }, [router]);

  const activeStage = PROCESSING_STAGES[stageIndex];

  useEffect(() => {
    const stage = PROCESSING_STAGES[stageIndex];
    if (!stage) return;

    if (stage.id === "ready") {
      trackEvent("processing_completed");
      const timeout = window.setTimeout(() => {
        router.push("/countdown");
      }, FINISH_HOLD_MS);
      return () => window.clearTimeout(timeout);
    }

    const timeout = window.setTimeout(() => {
      setStageIndex((prev) => Math.min(prev + 1, PROCESSING_STAGES.length - 1));
    }, STAGE_DURATION_MS[stage.id]);

    return () => window.clearTimeout(timeout);
  }, [stageIndex, router]);

  const totalSize = useMemo(
    () => files.reduce((sum, f) => sum + f.size, 0),
    [files],
  );

  return (
    <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1fr_20rem]">
      <div className="glass rounded-[2rem] p-6 sm:p-10">
        <div className="flex flex-col items-center text-center">
          <div className="relative h-28 w-28">
            <Lottie
              animationData={loaderAnimation}
              loop
              className="h-full w-full"
            />
            <span className="absolute inset-0 flex items-center justify-center">
              <SparklesPulse />
            </span>
          </div>
          <h1 className="mt-6 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Enhancing your media
          </h1>
          <p className="mt-2 max-w-md text-sm text-foreground/60">
            {activeStage.description}. This usually takes about 10 seconds —
            hang tight.
          </p>
          <p className="mt-4 text-xs font-medium text-foreground/50">
            Step {stageIndex + 1} of {PROCESSING_STAGES.length} ·{" "}
            {activeStage.label}
          </p>
        </div>

        <ol className="mt-10 space-y-2">
          {PROCESSING_STAGES.map((stage, i) => {
            const state =
              i < stageIndex ? "done" : i === stageIndex ? "active" : "pending";
            return (
              <motion.li
                key={stage.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={cn(
                  "flex items-center gap-4 rounded-2xl px-4 py-3 transition-all duration-300",
                  state === "active" && "bg-primary-500/10 shadow-glow",
                )}
              >
                <span
                  className={cn(
                    "relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors duration-300",
                    state === "done" &&
                      "bg-emerald-500/15 text-emerald-500",
                    state === "active" &&
                      "bg-gradient-to-br from-primary-500 to-accent-500 text-white",
                    state === "pending" &&
                      "bg-foreground/5 text-foreground/30",
                  )}
                >
                  {state === "done" ? (
                    <Check className="h-5 w-5" />
                  ) : (
                    <StageIcon stage={stage.id} state={state} className="h-5 w-5" />
                  )}
                </span>
                <div className="flex-1">
                  <p
                    className={cn(
                      "text-sm font-semibold transition-colors",
                      state === "pending"
                        ? "text-foreground/40"
                        : "text-foreground",
                    )}
                  >
                    {stage.label}
                  </p>
                  <AnimatePresence>
                    {state === "active" && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="text-xs text-foreground/50"
                      >
                        {stage.description}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>
                {state === "active" && (
                  <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-accent-500" />
                )}
              </motion.li>
            );
          })}
        </ol>
      </div>

      <aside className="glass h-fit rounded-[2rem] p-6">
        <h2 className="text-sm font-bold tracking-wide text-foreground uppercase">
          Your files
        </h2>
        <p className="mt-1 text-xs text-foreground/50">
          {files.length} {files.length === 1 ? "file" : "files"} ·{" "}
          {formatBytes(totalSize)}
        </p>
        <ul className="mt-4 space-y-3">
          {files.map((file) => (
            <li key={file.id} className="flex items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-foreground/5">
                {file.thumbnailUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={file.thumbnailUrl}
                    alt={file.name}
                    className="h-full w-full object-cover"
                  />
                ) : file.kind === "video" ? (
                  <Film className="h-5 w-5 text-foreground/40" />
                ) : (
                  <ImageIcon className="h-5 w-5 text-foreground/40" />
                )}
              </span>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-foreground">
                  {file.name}
                </p>
                <p className="text-[11px] text-foreground/50">
                  {formatBytes(file.size)} · {file.kind}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}

function SparklesPulse() {
  return (
    <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500/25 to-accent-500/25">
      <span className="h-6 w-6 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 blur-[2px] animate-pulse-glow" />
    </span>
  );
}
