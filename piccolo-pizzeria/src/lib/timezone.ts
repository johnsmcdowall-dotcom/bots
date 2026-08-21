/**
 * All customer-facing scheduling (opening hours, time slots, order
 * confirmations) is defined in the business's own local time — Europe/London
 * — regardless of what timezone the server process itself runs in (Vercel
 * and most serverless hosts default to UTC). Using Date's local
 * getHours()/getDay()/toISOString() directly is silently wrong for roughly
 * seven months of the year, whenever British Summer Time (BST, UTC+1) is in
 * effect. These helpers go through Intl's IANA timezone database instead,
 * which already knows the exact BST/GMT transition dates.
 */
const LONDON_TIME_ZONE = "Europe/London";

const WEEKDAY_INDEX: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

function londonParts(date: Date): Record<string, string> {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: LONDON_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    weekday: "short",
  }).formatToParts(date);
  const map: Record<string, string> = {};
  for (const p of parts) map[p.type] = p.value;
  return map;
}

/** "YYYY-MM-DD" for `date`, as a calendar date in Europe/London. */
export function londonDateISO(date: Date = new Date()): string {
  const p = londonParts(date);
  return `${p.year}-${p.month}-${p.day}`;
}

/** Minutes since midnight, wall-clock, in Europe/London. */
export function londonMinutesOfDay(date: Date = new Date()): number {
  const p = londonParts(date);
  return Number(p.hour) * 60 + Number(p.minute);
}

/** "HH:mm", wall-clock, in Europe/London. */
export function londonHHMM(date: Date = new Date()): string {
  const mins = londonMinutesOfDay(date);
  return `${String(Math.floor(mins / 60)).padStart(2, "0")}:${String(mins % 60).padStart(2, "0")}`;
}

/** 0 = Sunday ... 6 = Saturday, matching Date#getDay()'s convention, but read in Europe/London. */
export function londonDayOfWeek(date: Date = new Date()): number {
  const p = londonParts(date);
  return WEEKDAY_INDEX[p.weekday];
}

/** Adds `days` calendar days to a "YYYY-MM-DD" string — pure date arithmetic, anchored at noon UTC so it can never land on the wrong side of a DST transition. */
export function addDaysToISODate(dateISO: string, days: number): string {
  const [y, m, d] = dateISO.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days, 12)).toISOString().slice(0, 10);
}

/** Day-of-week for a "YYYY-MM-DD" string, matching Date#getDay()'s convention — anchored at noon UTC, so safe from any timezone the server happens to run in. */
export function dayOfWeekForISODate(dateISO: string): number {
  const [y, m, d] = dateISO.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12)).getUTCDay();
}

/** "Sat, 22 Aug" style label for a "YYYY-MM-DD" string, independent of server timezone. */
export function formatShortDateLabel(dateISO: string): string {
  const [y, m, d] = dateISO.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12)).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

/**
 * Converts a wall-clock "HH:mm" on a given "YYYY-MM-DD", meant as
 * Europe/London local time (i.e. what a customer picked from the time-slot
 * list), into the correct UTC instant — accounting for BST/GMT regardless
 * of the server's own timezone. Standard technique with no date library:
 * guess the instant assuming the wall-clock numbers were already UTC, see
 * what Europe/London wall-clock time that guess actually lands on, then
 * shift the guess by however far off that turned out to be.
 */
export function londonWallTimeToUTC(dateISO: string, hhmm: string): Date {
  const [y, m, d] = dateISO.split("-").map(Number);
  const [hh, mm] = hhmm.split(":").map(Number);
  const wantedWallMs = Date.UTC(y, m - 1, d, hh, mm);

  const naiveGuess = new Date(wantedWallMs);
  const p = londonParts(naiveGuess);
  const asLondonWallMs = Date.UTC(Number(p.year), Number(p.month) - 1, Number(p.day), Number(p.hour), Number(p.minute));

  const driftMs = asLondonWallMs - wantedWallMs;
  return new Date(naiveGuess.getTime() - driftMs);
}
