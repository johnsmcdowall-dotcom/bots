"use client";

import { useEffect, useState } from "react";
import { computeOpeningStatus } from "@/lib/opening-hours";
import type { BusinessSettings, OpeningStatus, SpecialHours, WeeklyHours } from "@/lib/types";

export function useOpeningStatus(
  business: Pick<BusinessSettings, "orderingPaused" | "orderingPausedMessage">,
  weeklyHours: WeeklyHours,
  specialHours: SpecialHours[]
): OpeningStatus | null {
  const [status, setStatus] = useState<OpeningStatus | null>(null);

  useEffect(() => {
    const update = () => setStatus(computeOpeningStatus(business, weeklyHours, specialHours));
    update();
    const id = setInterval(update, 60_000);
    return () => clearInterval(id);
  }, [business, weeklyHours, specialHours]);

  return status;
}
