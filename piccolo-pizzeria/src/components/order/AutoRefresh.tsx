"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

/** Polls the server (via router.refresh) while a condition holds — used to pick up webhook-driven status changes. */
export function AutoRefresh({ active, intervalMs = 3000, maxAttempts = 15 }: { active: boolean; intervalMs?: number; maxAttempts?: number }) {
  const router = useRouter();
  const attempts = useRef(0);

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => {
      attempts.current += 1;
      if (attempts.current > maxAttempts) {
        clearInterval(id);
        return;
      }
      router.refresh();
    }, intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs, maxAttempts, router]);

  return null;
}
