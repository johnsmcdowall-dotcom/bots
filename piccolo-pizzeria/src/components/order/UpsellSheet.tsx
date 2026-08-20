"use client";

import { useEffect, useState } from "react";
import { Plus, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ProductImage } from "@/components/media/ProductImage";
import { useBasketStore } from "@/store/basket-store";
import { formatMoney } from "@/lib/format";
import type { Product } from "@/lib/types";

const SESSION_KEY = "piccolo-upsell-shown";

/** Rule-based "you might also like" — shown at most once per browser session, never blocking checkout. */
export function UpsellSheet({ suggestions }: { suggestions: Product[] }) {
  const addLine = useBasketStore((s) => s.addLine);
  const lines = useBasketStore((s) => s.lines);
  const [open, setOpen] = useState(false);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());

  const inBasketIds = new Set(lines.map((l) => l.productId));
  const visible = suggestions.filter((p) => !addedIds.has(p.id) && !inBasketIds.has(p.id));

  useEffect(() => {
    if (suggestions.length === 0) return;
    let shown = false;
    try {
      shown = sessionStorage.getItem(SESSION_KEY) === "true";
    } catch {
      // Storage unavailable (private mode) — treat as not-yet-shown for this load only.
    }
    if (shown) return;

    const timer = setTimeout(() => {
      setOpen(true);
      try {
        sessionStorage.setItem(SESSION_KEY, "true");
      } catch {
        // Best-effort — worst case it can show again next time in this session.
      }
    }, 700);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (suggestions.length === 0) return null;

  function handleAdd(product: Product) {
    addLine({ productId: product.id, name: product.name, imageUrl: product.imageUrl, basePriceMinor: product.priceMinor, quantity: 1, modifiers: [] });
    setAddedIds((prev) => new Set(prev).add(product.id));
    toast.success(`Added ${product.name} to your basket`);
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent className="sm:max-w-lg">
        <div className="flex-1 overflow-y-auto">
          <SheetHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-fire-500" />
              <SheetTitle>You might also like</SheetTitle>
            </div>
            <SheetDescription>A few things that go well with your order.</SheetDescription>
          </SheetHeader>

          <div className="space-y-3 px-5 pb-6 sm:px-6">
            {visible.length === 0 && <p className="py-6 text-center text-sm text-char-400">Nice — you&apos;ve got it all.</p>}
            {visible.map((product) => (
              <div key={product.id} className="flex items-center gap-3 rounded-xl border border-char-200 p-3">
                <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-char-900">
                  <ProductImage imageUrl={product.imageUrl} alt={product.name} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-char-800">{product.name}</p>
                  <p className="text-sm text-char-500">{formatMoney(product.priceMinor)}</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => handleAdd(product)}>
                  <Plus className="h-3.5 w-3.5" /> Add
                </Button>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-char-200 bg-cream-50 p-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:px-6">
          <Button size="lg" variant="ghost" className="w-full" onClick={() => setOpen(false)}>
            No thanks, continue with my order
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
