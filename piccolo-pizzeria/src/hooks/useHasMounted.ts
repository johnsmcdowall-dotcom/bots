"use client";

import { useEffect, useState } from "react";

/**
 * True only after the first client render. Used to defer rendering
 * localStorage-backed state (the zustand basket) until after hydration, so
 * the server-rendered markup (always "empty basket") matches the client's
 * first paint exactly before the persisted value loads in.
 */
export function useHasMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: this *is* the hydration-safe "mounted" flag pattern.
  useEffect(() => setMounted(true), []);
  return mounted;
}
