"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { AdSlot } from "@/components/ads/AdSlot";
import {
  fetchAdConfig,
  getCachedAdConfig,
  getPlacementConfig,
  trackAdEvent,
  type AdConfig,
  type AdSlotConfig,
} from "@/services/ads";
import { cn } from "@/lib/cn";

const INTERVAL_MS = 60 * 60 * 1000;

function frequencyKey(slot: AdSlotConfig): string {
  return `hdguru-ad:${slot.provider_id}:${slot.frequency ?? "every_page"}`;
}

function slotAllowed(slot: AdSlotConfig): boolean {
  const frequency = slot.frequency ?? "every_page";
  if (frequency === "every_page") return true;
  try {
    const stored = window.sessionStorage.getItem(frequencyKey(slot));
    if (frequency === "every_session" || frequency === "once_per_session") {
      return stored !== "shown";
    }
    if (frequency === "interval") {
      const last = stored ? Number(stored) : 0;
      return Date.now() - last > INTERVAL_MS;
    }
  } catch {
    /* storage unavailable */
  }
  return true;
}

function markShown(slot: AdSlotConfig): void {
  const frequency = slot.frequency ?? "every_page";
  if (frequency === "every_page") return;
  try {
    window.sessionStorage.setItem(
      frequencyKey(slot),
      frequency === "interval" ? String(Date.now()) : "shown",
    );
  } catch {
    /* storage unavailable */
  }
}

export function AdPlacement({
  name,
  className,
  slotIndex = 0,
}: {
  name: string;
  className?: string;
  slotIndex?: number;
}) {
  const [config, setConfig] = useState<AdConfig | null>(null);
  const [visible, setVisible] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const trackedRef = useRef(false);

  useEffect(() => {
    const cached = getCachedAdConfig();
    if (cached) setConfig(cached);
    void fetchAdConfig().then((fresh) => {
      if (fresh) setConfig(fresh);
    });
  }, []);

  const placement = useMemo(
    () => (config ? getPlacementConfig(config, name) : null),
    [config, name],
  );
  const slot = placement?.slots[slotIndex] ?? null;
  const allowed = slot ? slotAllowed(slot) : false;

  useEffect(() => {
    if (!placement || !slot || !allowed) return;
    if (placement.behavior === "eager") {
      setVisible(true);
      return;
    }
    const el = wrapperRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "300px 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [placement, slot, allowed]);

  useEffect(() => {
    if (visible && slot && allowed && !trackedRef.current) {
      trackedRef.current = true;
      markShown(slot);
      trackAdEvent("impression", name, { providerId: slot.provider_id });
    }
  }, [visible, slot, allowed, name]);

  if (!placement || !slot || !allowed) return null;

  const style: CSSProperties = {};
  if (!visible) {
    if (placement.width) style.width = placement.width;
    if (placement.height) style.height = placement.height;
    if (placement.responsive) style.minHeight = 60;
  }

  const handleClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement;
    if (target.closest("a[href]")) {
      trackAdEvent("click", name, { providerId: slot.provider_id });
    }
  };

  return (
    <div
      ref={wrapperRef}
      onClick={handleClick}
      className={cn("ad-placement w-full", className)}
      style={style}
    >
      {visible ? <AdSlot slot={slot} /> : null}
    </div>
  );
}
