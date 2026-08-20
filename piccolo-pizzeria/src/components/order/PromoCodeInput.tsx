"use client";

import { useState } from "react";
import { Tag, Check, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useBasketStore } from "@/store/basket-store";

/**
 * Captures a promo code for checkout to validate server-side (discount
 * amount, minimum basket, expiry and usage limit are never trusted from the
 * client — see lib/pricing.ts). Applying here is just carrying the code
 * forward; the authoritative check happens on submit.
 */
export function PromoCodeInput() {
  const applied = useBasketStore((s) => s.promoCode);
  const setPromoCode = useBasketStore((s) => s.setPromoCode);
  const [value, setValue] = useState("");

  if (applied) {
    return (
      <div className="mt-3 flex items-center justify-between rounded-xl border border-basil-500/30 bg-basil-500/10 px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-basil-600">
          <Check className="h-4 w-4" /> {applied} applied
        </span>
        <button onClick={() => setPromoCode("")} className="text-basil-600 hover:text-basil-700" aria-label="Remove promo code">
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="mt-3 flex gap-2">
      <div className="relative flex-1">
        <Tag className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-char-400" />
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
          placeholder="Enter code"
          className="pl-10 uppercase"
        />
      </div>
      <Button
        variant="outline"
        disabled={!value.trim()}
        onClick={() => {
          setPromoCode(value.trim());
          setValue("");
        }}
      >
        Apply
      </Button>
    </div>
  );
}
