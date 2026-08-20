"use client";

import { Minus, Plus, X } from "lucide-react";
import { ProductImage } from "@/components/media/ProductImage";
import { useBasketStore, lineTotal } from "@/store/basket-store";
import { formatMoney, summaryModifiers } from "@/lib/format";
import type { CartLine } from "@/lib/types";

export function BasketItem({ line }: { line: CartLine }) {
  const updateQuantity = useBasketStore((s) => s.updateQuantity);
  const removeLine = useBasketStore((s) => s.removeLine);
  const shownModifiers = summaryModifiers(line.modifiers);

  return (
    <div className="flex gap-4 py-4">
      <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-char-800">
        <ProductImage imageUrl={line.imageUrl} alt={line.name} sizes="80px" />
      </div>

      <div className="flex flex-1 flex-col">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-display text-base text-char-900">{line.name}</h3>
          <span className="shrink-0 font-semibold text-char-900">{formatMoney(lineTotal(line))}</span>
        </div>
        {shownModifiers.length > 0 && (
          <p className="mt-0.5 text-sm text-char-500">{shownModifiers.map((m) => m.optionName).join(", ")}</p>
        )}
        {line.notes && <p className="mt-0.5 text-xs italic text-char-400">&ldquo;{line.notes}&rdquo;</p>}

        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center rounded-full border border-char-300">
            <button
              type="button"
              onClick={() => updateQuantity(line.lineId, line.quantity - 1)}
              className="flex h-11 w-11 items-center justify-center text-char-700 transition-transform active:scale-90"
              aria-label="Decrease quantity"
            >
              <Minus className="h-3.5 w-3.5" />
            </button>
            <span className="w-5 text-center text-sm font-semibold tabular-nums">{line.quantity}</span>
            <button
              type="button"
              onClick={() => updateQuantity(line.lineId, line.quantity + 1)}
              className="flex h-11 w-11 items-center justify-center text-char-700 transition-transform active:scale-90"
              aria-label="Increase quantity"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
          <button
            type="button"
            onClick={() => removeLine(line.lineId)}
            className="flex min-h-11 items-center gap-1 text-xs font-semibold text-char-400 hover:text-fire-600"
          >
            <X className="h-3.5 w-3.5" /> Remove
          </button>
        </div>
      </div>
    </div>
  );
}
