"use client";

import { useEffect, useState } from "react";
import { RotateCcw } from "lucide-react";
import { ReorderButton } from "@/components/order/ReorderSheet";
import { getLastOrder, type LastOrderEntry } from "@/lib/order-history";

/** Offers a one-tap reorder on a return visit. Renders nothing when there's no remembered order — no layout to disrupt. */
export function ReorderBanner() {
  const [lastOrder, setLastOrder] = useState<LastOrderEntry | null>(null);

  useEffect(() => {
    // localStorage only exists client-side, so this can't be derived during render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLastOrder(getLastOrder());
  }, []);

  if (!lastOrder) return null;

  return (
    <div className="mx-auto max-w-3xl px-4 pt-8 sm:px-6">
      <div className="flex flex-col items-start justify-between gap-3 rounded-2xl border border-char-200 bg-cream-50 p-4 sm:flex-row sm:items-center sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-fire-500/10 text-fire-600">
            <RotateCcw className="h-4 w-4" />
          </div>
          <div>
            <p className="font-display text-base text-char-900">Order again?</p>
            <p className="text-sm text-char-500">Pick up where order #{lastOrder.orderNumber} left off.</p>
          </div>
        </div>
        <ReorderButton orderId={lastOrder.id} variant="outline" size="sm" className="w-full sm:w-auto" />
      </div>
    </div>
  );
}
