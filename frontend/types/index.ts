export type MediaKind = "image" | "video";

export type JobStatus = "uploading" | "processing" | "completed" | "failed";

export type ThemeMode = "light" | "dark" | "system";

export type ToastVariant = "success" | "error" | "info";

export interface MediaFile {
  id: string;
  file: File;
  kind: MediaKind;
  name: string;
  size: number;
  type: string;
  previewUrl?: string;
  duration?: number;
}

export interface StoredMediaFile {
  id: string;
  name: string;
  size: number;
  type: string;
  kind: MediaKind;
  thumbnailUrl?: string;
  duration?: number;
}

export type ProcessingStageId =
  | "uploading"
  | "preparing"
  | "enhancing"
  | "watermark"
  | "compressing"
  | "saving"
  | "generating"
  | "ready";

export interface ProcessingStage {
  id: ProcessingStageId;
  label: string;
  description: string;
}

export interface ProcessingJob {
  jobId: string;
  status: JobStatus;
  currentStage: ProcessingStageId;
  stages: ProcessingStage[];
  files: MediaFile[];
  createdAt: string;
}

export interface HDResult {
  id: string;
  title: string;
  fileName: string;
  kind: MediaKind;
  thumbnailUrl: string;
  downloadUrl: string;
  whatsappUrl: string;
  originalSize: number;
  outputSize: number;
  duration?: number;
  createdBy: string;
  createdAt: string;
}

export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
}

export interface ContactMessagePayload {
  name: string;
  email: string;
  subject: string;
  message: string;
}

export type ContactApiResponse = ApiResponse<{ ticketId: string }>;

export interface FAQItem {
  question: string;
  answer: string;
}

export interface FeatureItem {
  id: string;
  icon: string;
  title: string;
  description: string;
}
