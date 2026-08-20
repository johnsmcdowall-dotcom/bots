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
  addLine: (line: Omit<CartLine, "lineId">) => void;
  removeLine: (lineId: string) => void;
  updateQuantity: (lineId: string, quantity: number) => void;
  clear: () => void;
  setMethod: (method: OrderMethod) => void;
  setTiming: (timing: OrderTiming) => void;
  setSchedule: (date: string | null, time: string | null) => void;
  setPromoCode: (code: string) => void;
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
      clear: () => set({ lines: [], promoCode: "", scheduledDate: null, scheduledTime: null, timing: "asap" }),
      setMethod: (method) => set({ method }),
      setTiming: (timing) => set({ timing, ...(timing === "asap" ? { scheduledDate: null, scheduledTime: null } : {}) }),
      setSchedule: (scheduledDate, scheduledTime) => set({ scheduledDate, scheduledTime }),
      setPromoCode: (promoCode) => set({ promoCode }),
      itemCount: () => get().lines.reduce((sum, l) => sum + l.quantity, 0),
      subtotalMinor: () => get().lines.reduce((sum, l) => sum + lineTotal(l), 0),
    }),
    { name: "piccolo-basket" }
  )
);

export { lineTotal };
