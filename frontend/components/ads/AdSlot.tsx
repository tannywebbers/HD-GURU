"use client";

import { useEffect, useRef } from "react";
import type { CSSProperties } from "react";
import type { AdSlotConfig } from "@/services/ads";
import { cn } from "@/lib/cn";

// Mount provider HTML and re-append <script> nodes so inline/external scripts
// actually execute (React's innerHTML assignment alone never runs them).
function mountHtml(container: HTMLElement, html: string): void {
  container.innerHTML = html;
  container.querySelectorAll("script").forEach((script) => {
    const clone = document.createElement("script");
    for (const attr of Array.from(script.attributes)) {
      clone.setAttribute(attr.name, attr.value);
    }
    clone.text = script.textContent ?? "";
    script.replaceWith(clone);
  });
}

export function AdSlot({
  slot,
  className,
}: {
  slot: AdSlotConfig;
  className?: string;
}) {
  const scriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (slot.render.kind === "script" || slot.render.kind === "html") {
      const el = scriptRef.current;
      if (el) mountHtml(el, slot.render.content ?? "");
    }
  }, [slot]);

  const frameStyle: CSSProperties = {
    width: slot.width ?? "100%",
    height: slot.height ?? 250,
  };

  if (slot.render.kind === "custom") {
    // Explicit trusted-admin path: isolated in a sandboxed frame.
    return (
      <iframe
        title={slot.name}
        srcDoc={slot.render.content}
        sandbox="allow-scripts"
        loading="lazy"
        className={cn("border-0", className)}
        style={frameStyle}
      />
    );
  }

  if (slot.render.kind === "iframe") {
    return (
      <iframe
        title={slot.name}
        src={slot.render.src}
        sandbox="allow-scripts allow-same-origin allow-popups"
        loading="lazy"
        className={cn("border-0", className)}
        style={frameStyle}
      />
    );
  }

  return (
    <div
      ref={scriptRef}
      className={cn("overflow-hidden", className)}
      style={{
        width: slot.width ?? undefined,
        height: slot.height ?? undefined,
      }}
    />
  );
}
