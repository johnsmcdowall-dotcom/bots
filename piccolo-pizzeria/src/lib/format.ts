export function formatMoney(minor: number): string {
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(minor / 100);
}

// Explicit timeZone below is deliberate, not decorative: this app's server
// (and some viewers' browsers) may not run in the UK, but every order time
// is always meant in the business's own local time — Europe/London.
// Omitting it would render an hour wrong for roughly seven months of the
// year, whenever British Summer Time is in effect.
export function formatOrderTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "numeric", minute: "2-digit", timeZone: "Europe/London" });
}

export function formatOrderDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Europe/London",
  });
}

export const DAY_LABELS_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
export const DAY_LABELS_FULL = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** Formats a "HH:mm" opening-hours time as a compact 12h string, e.g. "5pm" / "5:30pm". */
export function formatHours(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const period = h >= 12 ? "pm" : "am";
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return m === 0 ? `${hour12}${period}` : `${hour12}:${String(m).padStart(2, "0")}${period}`;
}

/**
 * Free base-choice selections (e.g. "Classic Woodfired Base") are the
 * default on every pizza, so listing them in the basket/checkout/
 * confirmation reads like a repetitive, generic description rather than
 * useful information. The full modifier — including the base — is still
 * sent to the server and shown on the admin order board for the kitchen;
 * this only trims what's surfaced in the compact customer-facing summary.
 */
export function summaryModifiers<T extends { groupName: string; priceMinor: number }>(modifiers: T[]): T[] {
  return modifiers.filter((m) => !(m.groupName === "Choose Your Base" && m.priceMinor === 0));
}
