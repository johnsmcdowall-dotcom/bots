import type { BusinessSettings } from "./types";

export interface WaitRange {
  lowMinutes: number;
  highMinutes: number;
  /** "~15 min" when the kitchen isn't backed up, "15-25 min" once currentWaitMinutes adds a real buffer. */
  label: string;
}

/**
 * Turns the two prep-time settings into an honest customer-facing estimate.
 * minPrepMinutes is the floor — the fastest a fresh order can realistically
 * come out of the oven. currentWaitMinutes is today's extra kitchen backlog
 * on top of that floor — the exact number the admin Orders board's quick
 * -5/+5 stepper adjusts, and the same `current_wait_minutes` column Settings
 * edits. Showing it as a range rather than one falsely-precise number is
 * more honest about the estimate, and it visibly moves as staff nudge the
 * stepper: push currentWaitMinutes up during a rush and the top of the
 * range grows; bring it back to 0 and the range collapses to a single
 * "~15 min" (there's no meaningful spread to advertise when the kitchen
 * isn't backed up).
 */
export function estimatedWaitRange(business: Pick<BusinessSettings, "minPrepMinutes" | "currentWaitMinutes">): WaitRange {
  const lowMinutes = Math.max(0, business.minPrepMinutes);
  const highMinutes = Math.max(lowMinutes, lowMinutes + business.currentWaitMinutes);
  const label = highMinutes > lowMinutes ? `${lowMinutes}-${highMinutes} min` : `~${lowMinutes} min`;
  return { lowMinutes, highMinutes, label };
}
