"use client";

import { Clock } from "lucide-react";
import { useOpeningStatus } from "@/hooks/useOpeningStatus";
import type { BusinessSettings, SpecialHours, WeeklyHours } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  business: Pick<BusinessSettings, "orderingPaused" | "orderingPausedMessage">;
  weeklyHours: WeeklyHours;
  specialHours: SpecialHours[];
  className?: string;
  compact?: boolean;
}

/**
 * Computes open/closed status in the browser (recalculated every minute) so
 * it's never stale from a cached server render. This is display-only — the
 * server independently re-validates opening status at checkout.
 */
export function OpeningStatusBadge({ business, weeklyHours, specialHours, className, compact }: Props) {
  const status = useOpeningStatus(business, weeklyHours, specialHours);

  if (!status) {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-sm text-char-400", className)}>
        <span className="h-2 w-2 rounded-full bg-char-300" />
        Checking hours…
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wide",
        status.isOpen ? "bg-basil-500/15 text-basil-600" : "bg-fire-500/10 text-fire-600",
        className
      )}
    >
      <span className={cn("h-2 w-2 rounded-full", status.isOpen ? "bg-basil-500 animate-pulse" : "bg-fire-500")} />
      {compact ? (
        status.isOpen ? "Open Now" : "Closed"
      ) : (
        <>
          <Clock className="h-3.5 w-3.5" aria-hidden />
          {status.message}
        </>
      )}
    </span>
  );
}
