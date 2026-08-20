"use client";

import { useEffect, useMemo, useState } from "react";
import { Zap, CalendarClock } from "lucide-react";
import { getOrderableDates } from "@/lib/slots";
import { estimatedWaitRange } from "@/lib/prep-time";
import { cn } from "@/lib/utils";
import type { BusinessSettings, OrderMethod, OrderTiming, SpecialHours, TimeSlot, WeeklyHours } from "@/lib/types";

export function TimeSlotPicker({
  business,
  weeklyHours,
  specialHours,
  method,
  timing,
  onTimingChange,
  scheduledDate,
  scheduledTime,
  onScheduleChange,
  asapAvailable,
}: {
  business: Pick<
    BusinessSettings,
    "asapOrdersEnabled" | "scheduledOrdersEnabled" | "maxAdvanceOrderDays" | "slotIntervalMinutes" | "minPrepMinutes" | "ordersPerSlot" | "deliveryOrdersPerSlot" | "currentWaitMinutes"
  >;
  weeklyHours: WeeklyHours;
  specialHours: SpecialHours[];
  method: OrderMethod;
  timing: OrderTiming;
  onTimingChange: (timing: OrderTiming) => void;
  scheduledDate: string | null;
  scheduledTime: string | null;
  onScheduleChange: (date: string | null, time: string | null) => void;
  /** Whether the business is open right now — ASAP can't be fulfilled otherwise. */
  asapAvailable: boolean;
}) {
  const dates = useMemo(() => getOrderableDates(business, weeklyHours, specialHours), [business, weeklyHours, specialHours]);
  const [activeDate, setActiveDate] = useState(scheduledDate || dates[0]?.dateISO);
  const [slots, setSlots] = useState<TimeSlot[] | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetches server-validated slot availability whenever the date/method
  // changes — capacity is never trusted client-side (see lib/slots.ts).
  useEffect(() => {
    if (timing !== "scheduled" || !activeDate) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading flag for the fetch kicked off right below
    setLoading(true);
    fetch(`/api/slots?date=${activeDate}&method=${method}`, { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => setSlots(data.slots ?? []))
      .catch(() => setSlots([]))
      .finally(() => setLoading(false));
  }, [activeDate, method, timing]);

  if (!business.asapOrdersEnabled && !business.scheduledOrdersEnabled) {
    return <p className="text-sm text-char-500">Online ordering isn&apos;t available right now. Please call us.</p>;
  }

  return (
    <div>
      <div className="grid grid-cols-2 gap-3">
        {business.asapOrdersEnabled && (
          <button
            type="button"
            disabled={!asapAvailable}
            onClick={() => asapAvailable && onTimingChange("asap")}
            title={asapAvailable ? undefined : "We're closed right now"}
            className={cn(
              "flex flex-col items-center gap-2 rounded-2xl border-2 px-4 py-4 transition-[background-color,border-color,transform] duration-150 active:enabled:scale-[0.98]",
              !asapAvailable && "cursor-not-allowed border-char-100 opacity-40",
              asapAvailable && timing === "asap" && "border-fire-500 bg-fire-500/5",
              asapAvailable && timing !== "asap" && "border-char-200 hover:bg-char-900/[0.02]"
            )}
          >
            <Zap className={cn("h-5 w-5", asapAvailable && timing === "asap" ? "text-fire-600" : "text-char-400")} />
            <span className="text-sm font-semibold text-char-900">ASAP</span>
            <span className="text-[11px] text-char-400">
              {asapAvailable ? estimatedWaitRange(business).label : "Not available"}
            </span>
          </button>
        )}
        {business.scheduledOrdersEnabled && (
          <button
            type="button"
            onClick={() => {
              onTimingChange("scheduled");
              if (!activeDate) setActiveDate(dates[0]?.dateISO);
            }}
            className={cn(
              "flex flex-col items-center gap-2 rounded-2xl border-2 px-4 py-4 transition-[background-color,border-color,transform] duration-150 active:scale-[0.98]",
              timing === "scheduled" ? "border-fire-500 bg-fire-500/5" : "border-char-200 hover:bg-char-900/[0.02]"
            )}
          >
            <CalendarClock className={cn("h-5 w-5", timing === "scheduled" ? "text-fire-600" : "text-char-400")} />
            <span className="text-sm font-semibold text-char-900">Choose a Time</span>
          </button>
        )}
      </div>

      {timing === "scheduled" && (
        <div className="mt-5">
          <div className="no-scrollbar scroll-fade-x flex gap-2 overflow-x-auto pb-1">
            {dates.map((d) => (
              <button
                key={d.dateISO}
                onClick={() => {
                  setActiveDate(d.dateISO);
                  onScheduleChange(d.dateISO, null);
                }}
                className={cn(
                  "shrink-0 rounded-full px-4 py-3 text-sm font-semibold transition-[background-color,color,transform] duration-150 active:scale-95",
                  activeDate === d.dateISO ? "bg-char-900 text-cream-50" : "bg-char-900/[0.05] text-char-600"
                )}
              >
                {d.label}
              </button>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-4">
            {loading &&
              Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-11 animate-pulse rounded-xl bg-char-900/[0.05]" />)}
            {!loading && slots?.length === 0 && (
              <p className="col-span-full text-sm text-char-500">No times available on this date.</p>
            )}
            {!loading &&
              slots?.map((slot) => {
                const isSelected = scheduledDate === activeDate && scheduledTime === slot.time;
                return (
                  <button
                    key={slot.time}
                    disabled={!slot.available}
                    onClick={() => onScheduleChange(activeDate ?? null, slot.time)}
                    className={cn(
                      "flex h-11 flex-col items-center justify-center rounded-xl border text-sm font-semibold transition-[background-color,color,border-color,transform] duration-150 active:enabled:scale-95",
                      !slot.available && "cursor-not-allowed border-char-100 bg-char-100 text-char-300 line-through",
                      slot.available && slot.label === "nearly-full" && !isSelected && "border-ember-400/60 bg-ember-400/10 text-ember-500",
                      slot.available && slot.label === "available" && !isSelected && "border-char-200 text-char-800 hover:bg-char-900/[0.03]",
                      isSelected && "border-fire-500 bg-fire-500 text-cream-50"
                    )}
                  >
                    {slot.time}
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
