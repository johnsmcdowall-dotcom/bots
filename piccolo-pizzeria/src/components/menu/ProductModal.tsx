"use client";

import { useEffect, useMemo, useState } from "react";
import { Minus, Plus } from "lucide-react";
import { toast } from "sonner";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { ModifierSelector } from "@/components/menu/ModifierSelector";
import { ProductImage } from "@/components/media/ProductImage";
import { useBasketStore } from "@/store/basket-store";
import { formatMoney } from "@/lib/format";
import type { ModifierGroup, Product } from "@/lib/types";

export function ProductModal({
  product,
  modifierGroups,
  onClose,
}: {
  product: Product | null;
  modifierGroups: ModifierGroup[];
  onClose: () => void;
}) {
  const addLine = useBasketStore((s) => s.addLine);
  const groups = useMemo(
    () => (product ? modifierGroups.filter((g) => product.modifierGroupIds.includes(g.id)) : []),
    [product, modifierGroups]
  );

  const [selections, setSelections] = useState<Record<string, string[]>>({});
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");

  // Resets the form whenever a different product is opened. The sheet stays
  // mounted across open/close (product -> null) so Radix can play the close
  // animation, which rules out resetting via a `key` remount instead.
  useEffect(() => {
    if (!product) return;
    const defaults: Record<string, string[]> = {};
    for (const group of groups) {
      const defaultOpt = group.options.find((o) => o.isDefault && !o.soldOut);
      defaults[group.id] = defaultOpt ? [defaultOpt.id] : [];
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelections(defaults);
    setQuantity(1);
    setNotes("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id]);

  if (!product) return null;

  const modifierTotal = groups.reduce((sum, group) => {
    const selectedIds = selections[group.id] ?? [];
    return sum + selectedIds.reduce((s, id) => s + (group.options.find((o) => o.id === id)?.priceMinor ?? 0), 0);
  }, 0);
  const unitPrice = product.priceMinor + modifierTotal;
  const total = unitPrice * quantity;

  const unmetRequired = groups.filter((g) => g.required && (selections[g.id]?.length ?? 0) < Math.max(1, g.minSelect));
  const canAdd = !product.soldOut && unmetRequired.length === 0;

  function handleAdd() {
    if (!product || !canAdd) return;
    const modifiers = groups.flatMap((group) =>
      (selections[group.id] ?? []).map((optionId) => {
        const opt = group.options.find((o) => o.id === optionId)!;
        return { groupId: group.id, groupName: group.name, optionId: opt.id, optionName: opt.name, priceMinor: opt.priceMinor };
      })
    );
    addLine({
      productId: product.id,
      name: product.name,
      imageUrl: product.imageUrl,
      basePriceMinor: product.priceMinor,
      quantity,
      modifiers,
      notes: notes.trim() || undefined,
    });
    toast.success(`Added ${product.name} to your basket`);
    onClose();
  }

  return (
    <Sheet open={Boolean(product)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="sm:max-w-lg">
        <div className="relative h-56 w-full shrink-0 overflow-hidden rounded-t-3xl bg-char-800 sm:h-64 sm:rounded-t-none">
          <ProductImage imageUrl={product.imageUrl} alt={product.name} priority />
          {product.soldOut && (
            <div className="absolute inset-0 flex items-center justify-center bg-char-900/60">
              <Badge variant="soldout" className="text-sm">Sold Out</Badge>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          <SheetHeader>
            <SheetTitle>{product.name}</SheetTitle>
            {product.description && <SheetDescription className="mt-1">{product.description}</SheetDescription>}
            <p className="mt-2 font-display text-xl text-fire-600">{formatMoney(product.priceMinor)}</p>
          </SheetHeader>

          <div className="px-5 sm:px-6">
            {groups.map((group) => (
              <ModifierSelector
                key={group.id}
                group={group}
                selected={selections[group.id] ?? []}
                onChange={(ids) => setSelections((s) => ({ ...s, [group.id]: ids }))}
              />
            ))}

            <div className="border-t border-char-200 py-5">
              <label htmlFor="notes" className="font-display text-base text-char-900">
                Special Instructions
              </label>
              <Textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value.slice(0, 280))}
                placeholder="E.g. no basil, extra crispy..."
                className="mt-2"
                rows={2}
              />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 border-t border-char-200 bg-cream-50 p-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:px-6">
          <div className="flex items-center rounded-full border border-char-300">
            <button
              type="button"
              onClick={() => setQuantity((q) => Math.max(1, q - 1))}
              className="flex h-11 w-11 items-center justify-center text-char-700 disabled:opacity-30"
              disabled={quantity <= 1}
              aria-label="Decrease quantity"
            >
              <Minus className="h-4 w-4" />
            </button>
            <span className="w-6 text-center font-semibold tabular-nums">{quantity}</span>
            <button
              type="button"
              onClick={() => setQuantity((q) => Math.min(20, q + 1))}
              className="flex h-11 w-11 items-center justify-center text-char-700"
              aria-label="Increase quantity"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
          <Button size="lg" className="flex-1" disabled={!canAdd} onClick={handleAdd}>
            {product.soldOut ? "Sold Out" : `Add to Order · ${formatMoney(total)}`}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
