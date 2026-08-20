"use client";

import Link from "next/link";
import { ShoppingBag } from "lucide-react";
import { useBasketStore } from "@/store/basket-store";
import { useHasMounted } from "@/hooks/useHasMounted";

export function HeaderBasketButton() {
  const mounted = useHasMounted();
  const itemCount = useBasketStore((s) => s.itemCount());

  return (
    <Link
      href="/order"
      className="relative flex h-11 w-11 items-center justify-center rounded-full text-char-900 hover:bg-char-900/5 md:hidden"
      aria-label={`Basket, ${mounted ? itemCount : 0} items`}
    >
      <ShoppingBag className="h-5 w-5" />
      {mounted && itemCount > 0 && (
        <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-fire-500 text-[10px] font-bold text-cream-50">
          {itemCount}
        </span>
      )}
    </Link>
  );
}
