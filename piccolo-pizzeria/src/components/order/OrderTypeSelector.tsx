"use client";

import { ShoppingBag, Bike } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OrderMethod } from "@/lib/types";

export function OrderTypeSelector({
  value,
  onChange,
  deliveryEnabled,
}: {
  value: OrderMethod;
  onChange: (method: OrderMethod) => void;
  deliveryEnabled: boolean;
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <button
        type="button"
        onClick={() => onChange("collection")}
        className={cn(
          "flex flex-col items-center gap-2 rounded-2xl border-2 px-4 py-4 transition-[background-color,border-color,transform] duration-150 active:enabled:scale-[0.98]",
          value === "collection" ? "border-fire-500 bg-fire-500/5" : "border-char-200 hover:bg-char-900/[0.02]"
        )}
      >
        <ShoppingBag className={cn("h-5 w-5", value === "collection" ? "text-fire-600" : "text-char-400")} />
        <span className="text-sm font-semibold text-char-900">Collection</span>
      </button>

      <button
        type="button"
        onClick={() => deliveryEnabled && onChange("delivery")}
        disabled={!deliveryEnabled}
        title={deliveryEnabled ? undefined : "Delivery isn't available right now"}
        className={cn(
          "flex flex-col items-center gap-2 rounded-2xl border-2 px-4 py-4 transition-[background-color,border-color,transform] duration-150 active:enabled:scale-[0.98]",
          value === "delivery" ? "border-fire-500 bg-fire-500/5" : "border-char-200 hover:bg-char-900/[0.02]",
          !deliveryEnabled && "cursor-not-allowed opacity-40"
        )}
      >
        <Bike className={cn("h-5 w-5", value === "delivery" ? "text-fire-600" : "text-char-400")} />
        <span className="text-sm font-semibold text-char-900">Delivery</span>
        {!deliveryEnabled && <span className="text-[11px] text-char-400">Not available</span>}
      </button>
    </div>
  );
}
