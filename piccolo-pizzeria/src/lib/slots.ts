import type { OrderMethod, TimeSlot, WeeklyHours, SpecialHours, BusinessSettings } from "./types";

function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function toHHMM(mins: number): string {
  const h = Math.floor(mins / 60) % 24;
  const m = mins % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function dayHoursFor(dateISO: string, weeklyHours: WeeklyHours, specialHours: SpecialHours[]) {
  const special = specialHours.find((s) => s.date === dateISO);
  if (special) {
    if (!special.isOpen) return null;
    return { openTime: special.openTime || "00:00", closeTime: special.closeTime || "23:59" };
  }
  const [y, m, d] = dateISO.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d, 12));
  const hours = weeklyHours[date.getUTCDay()];
  if (!hours?.isOpen) return null;
  return { openTime: hours.openTime, closeTime: hours.closeTime };
}

/**
 * Every orderable date within the admin-configured advance window, each with
 * a human label ("Today", "Tomorrow", weekday name).
 */
export function getOrderableDates(
  business: Pick<BusinessSettings, "maxAdvanceOrderDays">,
  weeklyHours: WeeklyHours,
  specialHours: SpecialHours[],
  now: Date = new Date()
): { dateISO: string; label: string }[] {
  const out: { dateISO: string; label: string }[] = [];
  for (let i = 0; i <= business.maxAdvanceOrderDays; i++) {
    const d = new Date(now);
    d.setDate(d.getDate() + i);
    const dateISO = isoDate(d);
    if (!dayHoursFor(dateISO, weeklyHours, specialHours)) continue;
    const label =
      i === 0 ? "Today" : i === 1 ? "Tomorrow" : d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
    out.push({ dateISO, label });
  }
  return out;
}

export interface GenerateSlotsParams {
  dateISO: string;
  method: OrderMethod;
  weeklyHours: WeeklyHours;
  specialHours: SpecialHours[];
  business: Pick<
    BusinessSettings,
    "slotIntervalMinutes" | "minPrepMinutes" | "ordersPerSlot" | "deliveryOrdersPerSlot" | "currentWaitMinutes"
  >;
  /** Existing confirmed/pending order counts keyed by "HH:mm" for this date+method. */
  bookedCounts: Record<string, number>;
  now?: Date;
}

/**
 * Builds the list of bookable time slots for a given date. Capacity and
 * "nearly full" thresholds are derived from admin-configured limits; the
 * booked count must come from a trusted source (the database) when used to
 * gate checkout — never accept it from the client.
 */
export function generateSlots(params: GenerateSlotsParams): TimeSlot[] {
  const { dateISO, method, weeklyHours, specialHours, business, bookedCounts, now = new Date() } = params;
  const hours = dayHoursFor(dateISO, weeklyHours, specialHours);
  if (!hours) return [];

  const capacity = method === "delivery" ? business.deliveryOrdersPerSlot : business.ordersPerSlot;
  const interval = business.slotIntervalMinutes;
  const isToday = isoDate(now) === dateISO;
  const earliestMins = isToday
    ? Math.ceil((now.getHours() * 60 + now.getMinutes() + business.minPrepMinutes + business.currentWaitMinutes / 3) / interval) * interval
    : toMinutes(hours.openTime);

  const openMins = toMinutes(hours.openTime);
  const closeMins = toMinutes(hours.closeTime);
  const lastSlotMins = closeMins - interval;

  const slots: TimeSlot[] = [];
  for (let t = openMins; t <= lastSlotMins; t += interval) {
    if (t < earliestMins) continue;
    const time = toHHMM(t);
    const booked = bookedCounts[time] || 0;
    const remaining = Math.max(0, capacity - booked);
    const ratio = remaining / capacity;
    let label: TimeSlot["label"] = "available";
    if (remaining === 0) label = "unavailable";
    else if (ratio <= 0.34) label = "nearly-full";

    slots.push({ time, dateISO, available: remaining > 0, remaining, label });
  }
  return slots;
}

export function isValidAsapWindow(business: Pick<BusinessSettings, "asapOrdersEnabled">): boolean {
  return business.asapOrdersEnabled;
}
