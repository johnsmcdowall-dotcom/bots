"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { CartLine, OrderMethod, OrderTiming } from "@/lib/types";

interface BasketState {
  lines: CartLine[];
  method: OrderMethod;
  timing: OrderTiming;
  scheduledDate: string | null; // "YYYY-MM-DD"
  scheduledTime: string | null; // "HH:mm"
  promoCode: string;
  // Stable id for the current checkout attempt, sent to the server as an
  // idempotency key. Lazily generated (not on every page load — only once
  // checkout actually starts) and persisted alongside the rest of the
  // basket via zustand's localStorage middleware, so it survives a page
  // refresh mid-checkout — the whole point is that a refresh-and-resubmit
  // reuses the SAME key rather than looking like a brand new order. Cleared
  // by clear(), which only runs once an order has actually completed (see
  // ClearBasketOnMount), so a genuinely new order later gets a fresh key.
  checkoutAttemptId: string | null;
  addLine: (line: Omit<CartLine, "lineId">) => void;
  removeLine: (lineId: string) => void;
  updateQuantity: (lineId: string, quantity: number) => void;
  clear: () => void;
  setMethod: (method: OrderMethod) => void;
  setTiming: (timing: OrderTiming) => void;
  setSchedule: (date: string | null, time: string | null) => void;
  setPromoCode: (code: string) => void;
  ensureCheckoutAttemptId: () => string;
  itemCount: () => number;
  subtotalMinor: () => number;
}

function lineTotal(line: CartLine): number {
  const modTotal = line.modifiers.reduce((sum, m) => sum + m.priceMinor, 0);
  return (line.basePriceMinor + modTotal) * line.quantity;
}

export const useBasketStore = create<BasketState>()(
  persist(
    (set, get) => ({
      lines: [],
      method: "collection",
      timing: "asap",
      scheduledDate: null,
      scheduledTime: null,
      promoCode: "",
      checkoutAttemptId: null,
      addLine: (line) =>
        set((state) => ({
          lines: [...state.lines, { ...line, lineId: crypto.randomUUID() }],
        })),
      removeLine: (lineId) => set((state) => ({ lines: state.lines.filter((l) => l.lineId !== lineId) })),
      updateQuantity: (lineId, quantity) =>
        set((state) => ({
          lines:
            quantity <= 0
              ? state.lines.filter((l) => l.lineId !== lineId)
              : state.lines.map((l) => (l.lineId === lineId ? { ...l, quantity } : l)),
        })),
      clear: () =>
        set({ lines: [], promoCode: "", scheduledDate: null, scheduledTime: null, timing: "asap", checkoutAttemptId: null }),
      setMethod: (method) => set({ method }),
      setTiming: (timing) => set({ timing, ...(timing === "asap" ? { scheduledDate: null, scheduledTime: null } : {}) }),
      setSchedule: (scheduledDate, scheduledTime) => set({ scheduledDate, scheduledTime }),
      setPromoCode: (promoCode) => set({ promoCode }),
      ensureCheckoutAttemptId: () => {
        const existing = get().checkoutAttemptId;
        if (existing) return existing;
        const id = crypto.randomUUID();
        set({ checkoutAttemptId: id });
        return id;
      },
      itemCount: () => get().lines.reduce((sum, l) => sum + l.quantity, 0),
      subtotalMinor: () => get().lines.reduce((sum, l) => sum + lineTotal(l), 0),
    }),
    { name: "piccolo-basket" }
  )
);

export { lineTotal };
