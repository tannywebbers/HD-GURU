"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export function useCountdown(durationSeconds: number) {
  const [seconds, setSeconds] = useState(durationSeconds);
  const [isRunning, setIsRunning] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clear = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    clear();
    setSeconds(durationSeconds);
    setIsRunning(true);
  }, [clear, durationSeconds]);

  const stop = useCallback(() => {
    clear();
    setIsRunning(false);
  }, [clear]);

  const reset = useCallback(() => {
    clear();
    setSeconds(durationSeconds);
    setIsRunning(false);
  }, [clear, durationSeconds]);

  useEffect(() => {
    if (!isRunning) return;
    intervalRef.current = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 1) {
          clear();
          setIsRunning(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return clear;
  }, [isRunning, clear]);

  useEffect(() => clear, [clear]);

  const isComplete = isRunning === false && seconds === 0;
  const progress = durationSeconds > 0 ? seconds / durationSeconds : 0;

  return { seconds, isRunning, isComplete, progress, start, stop, reset };
}
