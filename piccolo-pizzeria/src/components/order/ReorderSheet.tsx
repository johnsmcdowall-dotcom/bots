"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button, type ButtonProps } from "@/components/ui/button";
import { previewReorderAction } from "@/lib/actions/reorder";
import { useBasketStore } from "@/store/basket-store";
import { formatMoney } from "@/lib/format";
import type { ReorderPreview } from "@/lib/reorder";

/** Reconstructs a past order against the live menu and lets the customer confirm before it touches their basket. */
export function ReorderButton({
  orderId,
  label = "Order Again",
  variant,
  size,
  className,
}: {
  orderId: string;
  label?: string;
  variant?: ButtonProps["variant"];
  size?: ButtonProps["size"];
  className?: string;
}) {
  const router = useRouter();
  const addLine = useBasketStore((s) => s.addLine);
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<ReorderPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleOpen() {
    setOpen(true);
    setError(null);
    setPreview(null);
    startTransition(async () => {
      const result = await previewReorderAction(orderId);
      if ("error" in result) {
        setError(result.error);
      } else {
        setPreview(result.preview);
      }
    });
  }

  function handleConfirm() {
    if (!preview) return;
    for (const line of preview.lines) {
      if (!line.available) continue;
      addLine({
        productId: line.productId,
        name: line.name,
        imageUrl: line.imageUrl,
        basePriceMinor: line.unitPriceMinor - line.modifiers.reduce((sum, m) => sum + m.priceMinor, 0),
        quantity: line.quantity,
        modifiers: line.modifiers,
        notes: line.notes,
      });
    }
    toast.success("Added your order to the basket");
    setOpen(false);
    router.push("/order");
  }

  return (
    <>
      <Button variant={variant} size={size} className={className} onClick={handleOpen}>
        {label}
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="sm:max-w-lg">
          <div className="flex-1 overflow-y-auto">
            <SheetHeader>
              <SheetTitle>Order Again</SheetTitle>
              <SheetDescription>
                {preview ? `Order #${preview.orderNumber}, updated with today's menu.` : "Checking today's menu and prices…"}
              </SheetDescription>
            </SheetHeader>

            <div className="px-5 sm:px-6">
              {isPending && (
                <div className="flex items-center justify-center gap-2 py-10 text-char-500">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>Checking availability…</span>
                </div>
              )}

              {error && (
                <div className="flex items-start gap-2 rounded-xl bg-fire-500/10 p-4 text-sm text-fire-700">
                  <AlertTriangle className="h-4 w-4 shrink-0 translate-y-0.5" />
                  <p>{error}</p>
                </div>
              )}

              {preview && (
                <ul className="space-y-4 py-4">
                  {preview.lines.map((line, idx) => (
                    <li key={idx} className={line.available ? "border-b border-char-200 pb-4 last:border-0" : "rounded-xl bg-char-900/[0.03] p-3"}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className={line.available ? "font-medium text-char-800" : "font-medium text-char-400 line-through"}>
                            {line.quantity > 0 ? `${line.quantity}× ` : ""}
                            {line.name}
                          </p>
                          {line.modifiers.length > 0 && (
                            <p className="text-sm text-char-400">{line.modifiers.map((m) => m.optionName).join(", ")}</p>
                          )}
                        </div>
                        {line.available && (
                          <span className="shrink-0 text-sm text-char-600">{formatMoney(line.unitPriceMinor * line.quantity)}</span>
                        )}
                      </div>
                      {line.changeNotes.length > 0 && (
                        <ul className="mt-1.5 space-y-0.5">
                          {line.changeNotes.map((note, noteIdx) => (
                            <li key={noteIdx} className="flex items-start gap-1.5 text-xs text-ember-600">
                              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                              <span>{note}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {preview && (
            <div className="border-t border-char-200 bg-cream-50 p-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:px-6">
              <Button
                size="lg"
                variant="accent"
                className="w-full"
                disabled={!preview.anyAvailable}
                onClick={handleConfirm}
              >
                Add to Basket
              </Button>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
