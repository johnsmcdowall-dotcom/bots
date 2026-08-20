"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

/**
 * Belt-and-braces fix for a Next.js 16 + browser scroll-anchoring
 * interaction: client-side navigation to a shorter page can leave the
 * viewport scrolled partway down (landing in the footer, for example)
 * instead of at the top, even with overflow-anchor disabled. Forces a
 * hard reset on every real route change; skips the first render so it
 * doesn't fight the browser's own scroll-position restore on refresh.
 */
export function ScrollToTopOnNavigate() {
  const pathname = usePathname();
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    // A single scrollTo can still be undone by a layout shift that lands in
    // the same tick (e.g. a late client-only measurement). Two rAFs push
    // the reset past the browser's next layout/paint, after which nothing
    // in this app changes document height on mount.
    window.scrollTo(0, 0);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => window.scrollTo(0, 0));
    });
  }, [pathname]);

  return null;
}
