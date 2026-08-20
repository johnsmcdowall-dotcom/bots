import { formatMoney } from "@/lib/format";

export function OrderSummary({
  subtotalMinor,
  deliveryFeeMinor,
  discountMinor,
  totalMinor,
  deliveryNote,
}: {
  subtotalMinor: number;
  deliveryFeeMinor?: number;
  discountMinor?: number;
  totalMinor?: number;
  deliveryNote?: string;
}) {
  const total = totalMinor ?? subtotalMinor + (deliveryFeeMinor ?? 0) - (discountMinor ?? 0);

  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between text-char-600">
        <span>Subtotal</span>
        <span>{formatMoney(subtotalMinor)}</span>
      </div>
      {deliveryFeeMinor !== undefined ? (
        <div className="flex justify-between text-char-600">
          <span>Delivery</span>
          <span>{deliveryFeeMinor === 0 ? "Free" : formatMoney(deliveryFeeMinor)}</span>
        </div>
      ) : deliveryNote ? (
        <div className="flex justify-between text-char-400">
          <span>Delivery</span>
          <span>{deliveryNote}</span>
        </div>
      ) : null}
      {discountMinor !== undefined && discountMinor > 0 && (
        <div className="flex justify-between text-basil-600">
          <span>Discount</span>
          <span>-{formatMoney(discountMinor)}</span>
        </div>
      )}
      <div className="flex justify-between border-t border-char-200 pt-2 font-display text-lg text-char-900">
        <span>Total</span>
        <span>{formatMoney(total)}</span>
      </div>
    </div>
  );
}
