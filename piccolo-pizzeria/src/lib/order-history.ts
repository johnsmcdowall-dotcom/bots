// Remembers the customer's last completed order on this device, entirely
// client-side (no account/login exists in this app). Deliberately a
// separate localStorage key from the basket ("piccolo-basket") — this is
// order *history* for offering "Order Again" on a later visit, not part of
// the live basket a customer is currently building.
const STORAGE_KEY = "piccolo-last-order";

export interface LastOrderEntry {
  id: string;
  orderNumber: string;
  createdAt: string;
}

export function recordLastOrder(entry: LastOrderEntry): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entry));
  } catch {
    // Private browsing / storage disabled — Order Again on a return visit
    // just won't be offered, nothing else depends on this succeeding.
  }
}

export function getLastOrder(): LastOrderEntry | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.id !== "string" || typeof parsed?.orderNumber !== "string") return null;
    return parsed as LastOrderEntry;
  } catch {
    return null;
  }
}
