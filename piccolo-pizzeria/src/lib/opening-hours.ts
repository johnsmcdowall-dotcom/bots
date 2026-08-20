import type { BusinessSettings, DayHours, OpeningStatus, SpecialHours, WeeklyHours } from "./types";

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function minutesOfDay(date: Date): number {
  return date.getHours() * 60 + date.getMinutes();
}

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function formatTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const period = h >= 12 ? "pm" : "am";
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return m === 0 ? `${hour12}${period}` : `${hour12}:${String(m).padStart(2, "0")}${period}`;
}

/**
 * Computes whether the business is open right now, given weekly hours,
 * special-date overrides, and a manual ordering pause. This is the single
 * source of truth used by both the customer-facing status badge and the
 * server-side order validation — never trust the client's idea of "open".
 */
export function computeOpeningStatus(
  business: Pick<BusinessSettings, "orderingPaused" | "orderingPausedMessage">,
  weeklyHours: WeeklyHours,
  specialHours: SpecialHours[],
  now: Date = new Date()
): OpeningStatus {
  if (business.orderingPaused) {
    return {
      isOpen: false,
      reason: "manual_pause",
      message: business.orderingPausedMessage || "Ordering paused right now. Check back shortly.",
    };
  }

  const today = isoDate(now);
  const special = specialHours.find((s) => s.date === today);

  let todayHours: DayHours;
  if (special) {
    if (!special.isOpen) {
      return {
        isOpen: false,
        reason: "special_closure",
        message: `Closed today · ${special.label}`,
        nextOpenLabel: findNextOpen(weeklyHours, specialHours, now),
      };
    }
    todayHours = {
      isOpen: true,
      openTime: special.openTime || "00:00",
      closeTime: special.closeTime || "23:59",
    };
  } else {
    todayHours = weeklyHours[now.getDay()];
  }

  if (!todayHours?.isOpen) {
    return {
      isOpen: false,
      reason: "closed_day",
      message: `Closed today · ${findNextOpen(weeklyHours, specialHours, now)}`,
      nextOpenLabel: findNextOpen(weeklyHours, specialHours, now),
      todayHours,
    };
  }

  const nowMins = minutesOfDay(now);
  const openMins = toMinutes(todayHours.openTime);
  const closeMins = toMinutes(todayHours.closeTime);

  if (nowMins < openMins) {
    return {
      isOpen: false,
      reason: "outside_hours",
      message: `Closed · opens today at ${formatTime(todayHours.openTime)}`,
      nextOpenLabel: `Opens today at ${formatTime(todayHours.openTime)}`,
      todayHours,
    };
  }

  if (nowMins >= closeMins) {
    return {
      isOpen: false,
      reason: "outside_hours",
      message: `Closed · ${findNextOpen(weeklyHours, specialHours, now)}`,
      nextOpenLabel: findNextOpen(weeklyHours, specialHours, now),
      todayHours,
    };
  }

  return {
    isOpen: true,
    message: `Open now · orders until ${formatTime(todayHours.closeTime)}`,
    todayHours,
  };
}

function findNextOpen(weeklyHours: WeeklyHours, specialHours: SpecialHours[], from: Date): string {
  for (let i = 1; i <= 7; i++) {
    const d = new Date(from);
    d.setDate(d.getDate() + i);
    const iso = isoDate(d);
    const special = specialHours.find((s) => s.date === iso);
    if (special) {
      if (special.isOpen && special.openTime) {
        return `Opens ${i === 1 ? "tomorrow" : DAY_NAMES[d.getDay()]} at ${formatTime(special.openTime)}`;
      }
      continue;
    }
    const hours = weeklyHours[d.getDay()];
    if (hours?.isOpen) {
      return `Opens ${i === 1 ? "tomorrow" : DAY_NAMES[d.getDay()]} at ${formatTime(hours.openTime)}`;
    }
  }
  return "Check back soon";
}
