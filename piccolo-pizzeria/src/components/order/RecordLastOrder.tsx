"use client";

import { useEffect } from "react";
import { recordLastOrder } from "@/lib/order-history";

/** Remembers a genuinely completed order on this device so a return visit can offer "Order Again". */
export function RecordLastOrder({ id, orderNumber, createdAt }: { id: string; orderNumber: string; createdAt: string }) {
  useEffect(() => {
    recordLastOrder({ id, orderNumber, createdAt });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
  return null;
}
