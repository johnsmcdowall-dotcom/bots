"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShoppingBag } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import { PaymentSection } from "@/components/checkout/PaymentSection";
import { OrderSummary } from "@/components/order/OrderSummary";
import { useBasketStore } from "@/store/basket-store";
import { useHasMounted } from "@/hooks/useHasMounted";
import { formatOrderDateTime } from "@/lib/format";
import type { CheckoutFormValues } from "@/lib/validations/checkout";

interface CheckoutResult {
  demoMode: boolean;
  clientSecret?: string;
  orderId: string;
  orderNumber: string;
  totalMinor: number;
}

export function CheckoutFlow() {
  const mounted = useHasMounted();
  const router = useRouter();
  const lines = useBasketStore((s) => s.lines);
  const subtotal = useBasketStore((s) => s.subtotalMinor());
  const method = useBasketStore((s) => s.method);
  const timing = useBasketStore((s) => s.timing);
  const scheduledDate = useBasketStore((s) => s.scheduledDate);
  const scheduledTime = useBasketStore((s) => s.scheduledTime);
  const promoCode = useBasketStore((s) => s.promoCode);
  const clear = useBasketStore((s) => s.clear);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CheckoutResult | null>(null);

  useEffect(() => {
    if (mounted && lines.length === 0 && !result) {
      router.replace("/order");
    }
  }, [mounted, lines.length, result, router]);

  useEffect(() => {
    if (result?.demoMode) {
      clear();
      router.push(`/order-confirmation/${result.orderId}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  if (result?.demoMode) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <p className="text-char-500">Confirming your order…</p>
      </div>
    );
  }

  if (!mounted || (lines.length === 0 && !result)) return null;

  async function handleSubmit(values: CheckoutFormValues) {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/checkout/create-intent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lines: lines.map((l) => ({
            productId: l.productId,
            quantity: l.quantity,
            modifierOptionIds: l.modifiers.map((m) => m.optionId),
            notes: l.notes,
          })),
          method,
          timing,
          scheduledDate: scheduledDate ?? undefined,
          scheduledTime: scheduledTime ?? undefined,
          promoCode: promoCode || undefined,
          customer: {
            firstName: values.firstName,
            lastName: values.lastName,
            phone: values.phone,
            email: values.email,
          },
          address:
            method === "delivery"
              ? { line1: values.addressLine1, line2: values.addressLine2, postcode: values.addressPostcode }
              : undefined,
          notes: values.notes,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Something went wrong. Please try again.");
        setSubmitting(false);
        return;
      }
      setResult(data);
    } catch {
      setError("Network error — please check your connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const requestedLabel =
    timing === "asap" ? "As soon as possible" : scheduledDate && scheduledTime ? formatOrderDateTime(`${scheduledDate}T${scheduledTime}:00`) : "";

  return (
    <div className="mx-auto grid max-w-5xl gap-10 px-4 py-8 sm:px-6 sm:py-12 lg:grid-cols-[1fr_360px] lg:px-8">
      <div>
        <h1 className="font-display text-4xl uppercase tracking-tight text-char-900 sm:text-5xl">Checkout</h1>
        <p className="mt-1 text-char-500">
          {method === "delivery" ? "Delivery" : "Collection"} · {requestedLabel}
        </p>

        <div className="mt-8">
          {!result ? (
            <CheckoutForm method={method} submitting={submitting} serverError={error} onSubmit={handleSubmit} />
          ) : (
            <div>
              <p className="mb-4 text-sm font-semibold text-char-700">
                Order #{result.orderNumber} — complete payment to confirm
              </p>
              {result.clientSecret && (
                <PaymentSection clientSecret={result.clientSecret} orderId={result.orderId} totalMinor={result.totalMinor} />
              )}
            </div>
          )}
        </div>
      </div>

      <aside className="h-fit rounded-2xl border border-char-200 bg-cream-50 p-5 lg:sticky lg:top-28">
        <h2 className="flex items-center gap-2 font-display text-lg text-char-900">
          <ShoppingBag className="h-4 w-4" /> Order Summary
        </h2>
        <ul className="mt-4 space-y-2 text-sm text-char-600">
          {lines.map((line) => (
            <li key={line.lineId} className="flex justify-between gap-2">
              <span>
                {line.quantity}× {line.name}
              </span>
            </li>
          ))}
        </ul>
        <Separator className="my-4" />
        <OrderSummary
          subtotalMinor={subtotal}
          totalMinor={result?.totalMinor}
          deliveryNote={!result && method === "delivery" ? "Calculated at payment" : undefined}
        />
        <Link href="/order" className="mt-4 inline-block text-xs font-semibold text-fire-600 hover:underline">
          Edit order
        </Link>
      </aside>
    </div>
  );
}
