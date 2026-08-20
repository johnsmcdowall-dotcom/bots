"use client";

import { useEffect } from "react";
import { useBasketStore } from "@/store/basket-store";

/** Reaching a paid confirmation page always means checkout succeeded — clear the local basket. */
export function ClearBasketOnMount() {
  const clear = useBasketStore((s) => s.clear);
  useEffect(() => {
    clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
}
