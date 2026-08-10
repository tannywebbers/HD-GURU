const THUMB_MAX = 320;

async function fileToDataUrl(file: File): Promise<string | undefined> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => resolve(undefined);
    reader.readAsDataURL(file);
  });
}

function canvasToDataUrl(
  canvas: HTMLCanvasElement,
  w: number,
  h: number,
): string | undefined {
  canvas.width = w;
  canvas.height = h;
  try {
    return canvas.toDataURL("image/jpeg", 0.72);
  } catch {
    return undefined;
  }
}

export async function generateImageThumbnail(
  file: File,
): Promise<string | undefined> {
  const dataUrl = await fileToDataUrl(file);
  if (!dataUrl) return undefined;
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, THUMB_MAX / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      resolve(canvasToDataUrl(canvas, img.width * scale, img.height * scale));
    };
    img.onerror = () => resolve(dataUrl);
    img.src = dataUrl;
  });
}

export async function generateVideoThumbnail(
  file: File,
): Promise<string | undefined> {
  const url = URL.createObjectURL(file);
  return new Promise((resolve) => {
    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.preload = "metadata";
    const timeout = window.setTimeout(() => {
      URL.revokeObjectURL(url);
      resolve(undefined);
    }, 6000);

    const cleanup = () => {
      window.clearTimeout(timeout);
      URL.revokeObjectURL(url);
    };

    video.onloadeddata = () => {
      try {
        video.currentTime = Math.min(0.2, video.duration || 0.2);
      } catch {
        /* noop */
      }
    };
    video.onseeked = () => {
      const scale = Math.min(
        1,
        THUMB_MAX / Math.max(video.videoWidth, video.videoHeight),
      );
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth * scale;
      canvas.height = video.videoHeight * scale;
      canvas
        .getContext("2d")
        ?.drawImage(video, 0, 0, canvas.width, canvas.height);
      cleanup();
      resolve(canvasToDataUrl(canvas, canvas.width, canvas.height));
    };
    video.onerror = () => {
      cleanup();
      resolve(undefined);
    };
    video.src = url;
  });
}

export function generateThumbnail(file: File, kind: "image" | "video") {
  if (kind === "image") return generateImageThumbnail(file);
  return generateVideoThumbnail(file);
}
