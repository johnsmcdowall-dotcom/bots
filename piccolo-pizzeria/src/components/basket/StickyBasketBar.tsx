"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShoppingBag } from "lucide-react";
import { useBasketStore } from "@/store/basket-store";
import { useHasMounted } from "@/hooks/useHasMounted";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Persistent mobile ordering bar — always reachable without hunting for the
 * basket, per the mobile-first requirement. Hidden on desktop (the header's
 * basket icon covers that) and hidden until there's something to show.
 */
export function StickyBasketBar() {
  const mounted = useHasMounted();
  const itemCount = useBasketStore((s) => s.itemCount());
  const subtotal = useBasketStore((s) => s.subtotalMinor());
  const pathname = usePathname();

  const hiddenOnThisPage = pathname === "/order" || pathname.startsWith("/checkout");
  if (!mounted || itemCount === 0 || hiddenOnThisPage) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 px-3 pb-3 safe-bottom md:hidden">
      <Link
        href="/order"
        className={cn(
          "flex w-full items-center justify-between rounded-2xl bg-char-900 px-5 py-4 text-cream-50 shadow-2xl shadow-char-900/30",
          "transition-transform active:scale-[0.98]"
        )}
      >
        <span className="flex items-center gap-2.5 font-semibold">
          <ShoppingBag className="h-5 w-5" />
          <span>
            View Basket <span className="text-cream-100/60">·</span> {itemCount} {itemCount === 1 ? "item" : "items"}
          </span>
        </span>
        <span className="font-display text-lg">{formatMoney(subtotal)}</span>
      </Link>
    </div>
  );
}
