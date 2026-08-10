"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  CloudUpload,
  Image as ImageIcon,
  X,
} from "lucide-react";
import { FilePreview } from "@/components/upload/FilePreview";
import { GlassButton } from "@/components/ui/GlassButton";
import { useToast } from "@/components/ToastProvider";
import { uploadFiles } from "@/services/api";
import {
  ACCEPTED_IMAGE_TYPES,
  ACCEPTED_VIDEO_TYPES,
  MAX_FILES,
  MAX_FILE_SIZE_MB,
} from "@/lib/constants";
import { generateThumbnail } from "@/lib/thumbnail";
import { formatBytes, generateId } from "@/lib/format";
import { saveFiles } from "@/lib/fileStore";
import { trackEvent } from "@/services/ads";
import type { MediaFile, MediaKind, StoredMediaFile } from "@/types";
import { cn } from "@/lib/cn";

export function UploadZone() {
  const router = useRouter();
  const { showToast } = useToast();
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const processingRef = useRef(false);

  const acceptedTypes = useMemo(
    () => [...ACCEPTED_IMAGE_TYPES, ...ACCEPTED_VIDEO_TYPES],
    [],
  );

  const validateFile = useCallback((file: File): string | null => {
    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > MAX_FILE_SIZE_MB) {
      return `"${file.name}" is over the ${MAX_FILE_SIZE_MB}MB limit.`;
    }
    if (!acceptedTypes.includes(file.type)) {
      return `"${file.name}" isn't a supported image or video format.`;
    }
    return null;
  }, [acceptedTypes]);

  const addFiles = useCallback(
    async (incoming: File[]) => {
      const newErrors: string[] = [];
      const additions: MediaFile[] = [];

      for (const file of incoming) {
        if (files.length + additions.length >= MAX_FILES) {
          newErrors.push(`You can upload up to ${MAX_FILES} files at once.`);
          break;
        }
        const duplicate = [...files, ...additions].some(
          (f) => f.name === file.name && f.size === file.size,
        );
        if (duplicate) continue;

        const validationError = validateFile(file);
        if (validationError) {
          newErrors.push(validationError);
          continue;
        }

        const kind: MediaKind = file.type.startsWith("image/")
          ? "image"
          : "video";
        const media: MediaFile = {
          id: generateId("file"),
          file,
          kind,
          name: file.name,
          size: file.size,
          type: file.type,
        };
        additions.push(media);
      }

      if (additions.length > 0) {
        setFiles((prev) => [...prev, ...additions]);
        additions.forEach((media) => {
          generateThumbnail(media.file, media.kind)
            .then((thumb) => {
              if (!thumb) return;
              setFiles((prev) =>
                prev.map((f) =>
                  f.id === media.id ? { ...f, previewUrl: thumb } : f,
                ),
              );
            })
            .catch(() => undefined);
        });
      }

      setErrors(newErrors);
      if (newErrors.length > 0) {
        showToast(newErrors[0], "error");
      }
    },
    [files, showToast, validateFile],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "image/*": [], "video/*": [] },
    multiple: true,
    noClick: uploading,
    noKeyboard: uploading,
    onDrop: (accepted, rejected) => {
      void addFiles(accepted);
      if (rejected.length > 0) {
        void addFiles(rejected.map((r) => r.file));
      }
    },
  });

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const totalSize = useMemo(
    () => files.reduce((sum, f) => sum + f.size, 0),
    [files],
  );

  const handleEnhance = async () => {
    if (files.length === 0 || uploading || processingRef.current) return;
    processingRef.current = true;
    setUploading(true);
    setProgress(0);

    trackEvent("upload_started", { props: { files: files.length } });
    const res = await uploadFiles(
      files.map((f) => f.file),
      (p) => setProgress(p),
    );

    if (!res.ok || !res.data) {
      trackEvent("upload_failed", { props: { reason: res.error ?? "unknown" } });
      showToast(res.error ?? "Upload failed. Please try again.", "error");
      setUploading(false);
      processingRef.current = false;
      return;
    }

    trackEvent("upload_completed", { props: { files: res.data.files.length } });

    const stored: StoredMediaFile[] = res.data.files.map((f) => ({
      id: f.id,
      name: f.name,
      size: f.size,
      type: f.type,
      kind: f.kind,
      thumbnailUrl: f.previewUrl,
      duration: f.duration,
    }));
    saveFiles(stored);
    router.push("/processing");
  };

  return (
    <div className="mx-auto max-w-4xl">
      <div
        {...getRootProps()}
        role="button"
        aria-label="Upload photos or videos"
        className={cn(
          "glass relative cursor-pointer overflow-hidden rounded-[2rem] p-8 text-center transition-all duration-300 sm:p-12",
          isDragActive
            ? "scale-[1.02] ring-2 ring-primary-500/60 shadow-glow"
            : "hover:shadow-glow",
          uploading && "pointer-events-none opacity-70",
        )}
      >
        <input {...getInputProps()} />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary-600/10 via-transparent to-accent-600/10" />

        <motion.div
          animate={isDragActive ? { y: [0, -8, 0] } : undefined}
          transition={{ duration: 1.2, repeat: Infinity }}
          className="relative mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-primary-500 to-accent-500 text-white shadow-glow"
        >
          {isDragActive ? (
            <CloudUpload className="h-9 w-9" />
          ) : (
            <ImageIcon className="h-9 w-9" />
          )}
        </motion.div>

        <h2 className="relative mt-6 text-xl font-bold text-foreground sm:text-2xl">
          {isDragActive
            ? "Drop your files here"
            : "Drag & drop your photos or videos"}
        </h2>
        <p className="relative mt-2 text-sm text-foreground/60">
          or{" "}
          <span className="font-semibold text-primary-600 underline decoration-primary-500/40 underline-offset-4 dark:text-primary-300">
            browse files
          </span>{" "}
          from your device
        </p>
        <p className="relative mt-4 text-xs text-foreground/50">
          {MAX_FILES} files max · {MAX_FILE_SIZE_MB}MB each · JPG, PNG, WebP,
          HEIC, MP4, WebM, MOV
        </p>
      </div>

      {files.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">
              {files.length} {files.length === 1 ? "file" : "files"} ·{" "}
              {formatBytes(totalSize)}
            </p>
            <button
              type="button"
              onClick={() => setFiles([])}
              className="flex cursor-pointer items-center gap-1 text-xs font-medium text-foreground/50 transition-colors hover:text-rose-500"
            >
              <X className="h-3.5 w-3.5" /> Clear all
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            <AnimatePresence>
              {files.map((file) => (
                <FilePreview
                  key={file.id}
                  file={file}
                  onRemove={removeFile}
                />
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 flex items-start gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3"
        >
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
          <ul className="space-y-1 text-sm text-rose-600 dark:text-rose-400">
            {errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </motion.div>
      )}

      {uploading && (
        <div className="glass mt-6 rounded-2xl px-5 py-4">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-semibold text-foreground">
              Uploading securely…
            </span>
            <span className="text-foreground/60">{Math.round(progress)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-foreground/10">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-primary-500 via-accent-500 to-rose-500"
              animate={{ width: `${progress}%` }}
              transition={{ ease: "linear" }}
            />
          </div>
        </div>
      )}

      <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
        <GlassButton
          size="lg"
          loading={uploading}
          disabled={files.length === 0}
          onClick={handleEnhance}
        >
          {uploading ? "Uploading…" : "Enhance my files"}
        </GlassButton>
        <p className="text-xs text-foreground/50">
          Free forever · Your files auto-delete after delivery
        </p>
      </div>
    </div>
  );
}
