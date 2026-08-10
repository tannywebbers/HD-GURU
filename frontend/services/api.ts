import {
  ACCEPTED_IMAGE_TYPES,
  ACCEPTED_VIDEO_TYPES,
  MAX_FILE_SIZE_MB,
  PROCESSING_STAGES,
  WHATSAPP_URL,
} from "@/lib/constants";
import { generateId, isImageType } from "@/lib/format";
import type {
  ApiResponse,
  ContactApiResponse,
  ContactMessagePayload,
  HDResult,
  MediaFile,
  MediaKind,
  ProcessingJob,
  ProcessingStageId,
} from "@/types";

export const STAGE_DURATION_MS: Record<ProcessingStageId, number> = {
  uploading: 1400,
  preparing: 1000,
  enhancing: 2200,
  watermark: 1000,
  compressing: 1600,
  saving: 1100,
  generating: 1800,
  ready: 0,
};

const STAGE_ORDER: ProcessingStageId[] = [
  "uploading",
  "preparing",
  "enhancing",
  "watermark",
  "compressing",
  "saving",
  "generating",
  "ready",
];

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(
  /\/+$/,
  "",
);

export const isBackendEnabled = API_BASE_URL.length > 0;

const STATUS_ENDPOINT = "/api/v1/uploads";

const BACKEND_TO_STAGE: Record<string, ProcessingStageId> = {
  queued: "uploading",
  analyzing: "preparing",
  enhancing: "enhancing",
  watermarking: "watermark",
  compressing: "compressing",
  storing: "saving",
  completed: "ready",
  failed: "ready",
  expired: "ready",
};

const WAIT_INTERVAL_MS = 1200;
const WAIT_ATTEMPTS = 50;

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function apiErrorMessage(payload: unknown): string {
  const body = payload as { error?: { message?: string } };
  return (
    body?.error?.message ??
    (typeof payload === "object" && payload !== null && "detail" in payload
      ? "The server rejected the request."
      : "Could not reach the server. Please try again.")
  );
}

function resolveUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (/^https?:\/\//.test(url)) return url;
  return `${API_BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}

function uploadWithProgress(
  form: FormData,
  url: string,
  onProgress?: (percent: number) => void,
): Promise<Response> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.min(99, Math.round((event.loaded / event.total) * 100)));
      }
    };
    xhr.onload = () => {
      onProgress?.(100);
      const contentType =
        xhr.getResponseHeader("content-type") ?? "application/json";
      resolve(
        new Response(xhr.responseText, {
          status: xhr.status,
          statusText: xhr.statusText,
          headers: { "content-type": contentType },
        }),
      );
    };
    xhr.onerror = () => reject(new Error("Network error during upload."));
    xhr.send(form);
  });
}

async function fetchStatus(publicId: string): Promise<string> {
  try {
    const res = await fetch(
      `${API_BASE_URL}${STATUS_ENDPOINT}/${publicId}/status`,
    );
    if (!res.ok) return "failed";
    const body = (await res.json()) as { status?: string };
    return body.status ?? "failed";
  } catch {
    return "failed";
  }
}

function stageForStatus(status: string): ProcessingStageId {
  return BACKEND_TO_STAGE[status] ?? "preparing";
}

function latestInProgressStage(statuses: string[]): ProcessingStageId {
  let current: ProcessingStageId = STAGE_ORDER[0];
  for (const status of statuses) {
    const stage = stageForStatus(status);
    if (STAGE_ORDER.indexOf(stage) > STAGE_ORDER.indexOf(current)) {
      current = stage;
    }
  }
  return current;
}

export interface UploadResult {
  uploadId: string;
  files: MediaFile[];
}

function mediaKindFor(file: File): MediaKind {
  return isImageType(file.type) ? "image" : "video";
}

function toMediaFiles(files: File[], ids: string[]): MediaFile[] {
  return files.map((file, index) => ({
    id: ids[index] ?? generateId("file"),
    file,
    kind: mediaKindFor(file),
    name: file.name,
    size: file.size,
    type: file.type,
    previewUrl: file.type.startsWith("image/")
      ? URL.createObjectURL(file)
      : undefined,
    duration: file.type.startsWith("video/")
      ? 6 + (index % 3) * 2
      : undefined,
  }));
}

export async function uploadFiles(
  files: File[],
  onProgress?: (percent: number) => void,
): Promise<ApiResponse<UploadResult>> {
  for (const file of files) {
    const sizeMb = file.size / (1024 * 1024);
    const kind = mediaKindFor(file);
    const validType =
      kind === "image"
        ? ACCEPTED_IMAGE_TYPES.includes(file.type)
        : ACCEPTED_VIDEO_TYPES.includes(file.type);

    if (sizeMb > MAX_FILE_SIZE_MB) {
      return {
        ok: false,
        error: `"${file.name}" exceeds the ${MAX_FILE_SIZE_MB}MB limit.`,
      };
    }
    if (!validType) {
      return {
        ok: false,
        error: `"${file.name}" is not a supported image or video format.`,
      };
    }
  }

  if (!isBackendEnabled) {
    const steps = 20;
    for (let i = 1; i <= steps; i++) {
      await delay(90);
      onProgress?.((i / steps) * 100);
    }
    return {
      ok: true,
      data: {
        uploadId: generateId("upload"),
        files: toMediaFiles(files, []),
      },
    };
  }

  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  let response: Response;
  try {
    response = await uploadWithProgress(
      form,
      `${API_BASE_URL}${STATUS_ENDPOINT}`,
      onProgress,
    );
  } catch {
    return { ok: false, error: "Network error during upload." };
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // non-JSON response handled below
  }

  if (!response.ok) {
    return { ok: false, error: apiErrorMessage(payload) };
  }

  const data = payload as { jobs?: { id?: string; status?: string }[] };
  const jobs = Array.isArray(data?.jobs) ? data.jobs : [];
  if (jobs.length === 0) {
    return { ok: false, error: "No files were accepted." };
  }

  const ids = jobs.map((job) => job.id ?? "");
  const mediaFiles = toMediaFiles(files, ids);
  return {
    ok: true,
    data: { uploadId: ids[0] || mediaFiles[0].id, files: mediaFiles },
  };
}

export async function startProcessing(
  uploadId: string,
): Promise<ApiResponse<ProcessingJob>> {
  if (isBackendEnabled) {
    return {
      ok: true,
      data: {
        jobId: uploadId,
        status: "processing",
        currentStage: "uploading",
        stages: PROCESSING_STAGES,
        files: [],
        createdAt: new Date().toISOString(),
      },
    };
  }
  await delay(300);
  return {
    ok: true,
    data: {
      jobId: `${uploadId}-${generateId("job")}`,
      status: "processing",
      currentStage: "uploading",
      stages: PROCESSING_STAGES,
      files: [],
      createdAt: new Date().toISOString(),
    },
  };
}

export async function getJobStatus(
  job: ProcessingJob,
): Promise<ApiResponse<ProcessingJob>> {
  if (isBackendEnabled) {
    const ids = job.files.map((file) => file.id).filter(Boolean);
    if (ids.length === 0) {
      return { ok: true, data: { ...job, currentStage: "uploading" } };
    }
    const statuses = await Promise.all(ids.map((id) => fetchStatus(id)));
    if (statuses.some((status) => status === "failed" || status === "expired")) {
      return {
        ok: true,
        data: { ...job, status: "failed", currentStage: "ready" },
      };
    }
    if (statuses.every((status) => status === "completed")) {
      return {
        ok: true,
        data: { ...job, status: "completed", currentStage: "ready" },
      };
    }
    return {
      ok: true,
      data: {
        ...job,
        status: "processing",
        currentStage: latestInProgressStage(statuses),
      },
    };
  }

  const started = new Date(job.createdAt).getTime();
  const elapsed = Date.now() - started;

  let currentStage: ProcessingStageId = "uploading";
  let acc = 0;
  for (const stage of STAGE_ORDER) {
    if (elapsed < acc + STAGE_DURATION_MS[stage]) {
      currentStage = stage;
      break;
    }
    acc += STAGE_DURATION_MS[stage];
  }

  const done = elapsed >= acc;
  return {
    ok: true,
    data: {
      ...job,
      currentStage: done ? "ready" : currentStage,
      status: done ? "completed" : "processing",
    },
  };
}

interface MediaInfo {
  public_id?: string;
  status?: string;
  media_type?: string;
  original_filename?: string;
  file_size?: number;
  duration?: number;
  thumbnail_url?: string | null;
  download_url?: string | null;
  whatsapp_url?: string | null;
  completed_at?: string | null;
}

async function waitForMedia(publicId: string): Promise<MediaInfo | null> {
  for (let attempt = 0; attempt < WAIT_ATTEMPTS; attempt++) {
    try {
      const res = await fetch(
        `${API_BASE_URL}${STATUS_ENDPOINT}/${publicId}`,
      );
      if (res.ok) {
        const info = (await res.json()) as MediaInfo;
        if (info.status === "completed") return info;
        if (info.status === "failed" || info.status === "expired") return null;
      }
    } catch {
      // transient network issue; keep polling
    }
    await delay(WAIT_INTERVAL_MS);
  }
  return null;
}

export async function getResult(
  jobId: string,
): Promise<ApiResponse<HDResult>> {
  if (isBackendEnabled) {
    const info = await waitForMedia(jobId);
    if (!info) {
      return {
        ok: false,
        error: "Your file is not ready yet. Please try again.",
      };
    }
    const kind: MediaKind = info.media_type === "video" ? "video" : "image";
    const fileName = info.original_filename || "hd-guru-enhanced";
    return {
      ok: true,
      data: {
        id: info.public_id ?? jobId,
        title: info.original_filename || "Your HD File",
        fileName,
        kind,
        thumbnailUrl: resolveUrl(info.thumbnail_url),
        downloadUrl: resolveUrl(info.download_url),
        whatsappUrl:
          info.whatsapp_url ??
          `${WHATSAPP_URL}?text=${encodeURIComponent(
            "Send HD for " + (info.public_id ?? jobId),
          )}`,
        originalSize: 0,
        outputSize: info.file_size ?? 0,
        duration: info.duration ?? undefined,
        createdBy: "HD Guru",
        createdAt: info.completed_at ?? new Date().toISOString(),
      },
    };
  }

  await delay(400);
  const seed = jobId;
  return {
    ok: true,
    data: {
      id: generateId("result"),
      title: "Your HD File",
      fileName: "hd-guru-enhanced.mp4",
      kind: "video",
      thumbnailUrl: `https://picsum.photos/seed/${seed}/640/360`,
      downloadUrl: `https://picsum.photos/seed/${seed}/1920/1080`,
      whatsappUrl: `${WHATSAPP_URL}?text=${encodeURIComponent(
        "Send HD for " + jobId,
      )}`,
      originalSize: 48.2 * 1024 * 1024,
      outputSize: 9.8 * 1024 * 1024,
      duration: 14,
      createdBy: "HD Guru",
      createdAt: new Date().toISOString(),
    },
  };
}

export async function sendContactMessage(
  payload: ContactMessagePayload,
): Promise<ContactApiResponse> {
  await delay(900);
  const valid =
    payload.name.trim().length > 0 &&
    payload.email.includes("@") &&
    payload.message.trim().length > 5;

  if (!valid) {
    return { ok: false, error: "Please fill in all fields correctly." };
  }

  return {
    ok: true,
    data: { ticketId: generateId("ticket").toUpperCase() },
  };
}
