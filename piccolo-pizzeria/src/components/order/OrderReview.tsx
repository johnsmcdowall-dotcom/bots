"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShoppingBag, ArrowRight, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { BasketItem } from "@/components/basket/BasketItem";
import { OrderTypeSelector } from "@/components/order/OrderTypeSelector";
import { TimeSlotPicker } from "@/components/order/TimeSlotPicker";
import { OrderSummary } from "@/components/order/OrderSummary";
import { PromoCodeInput } from "@/components/order/PromoCodeInput";
import { useBasketStore } from "@/store/basket-store";
import { useOpeningStatus } from "@/hooks/useOpeningStatus";
import { useHasMounted } from "@/hooks/useHasMounted";
import type { BusinessSettings, SpecialHours, WeeklyHours } from "@/lib/types";

export function OrderReview({
  business,
  weeklyHours,
  specialHours,
}: {
  business: BusinessSettings;
  weeklyHours: WeeklyHours;
  specialHours: SpecialHours[];
}) {
  const mounted = useHasMounted();
  const router = useRouter();
  const lines = useBasketStore((s) => s.lines);
  const subtotal = useBasketStore((s) => s.subtotalMinor());
  const method = useBasketStore((s) => s.method);
  const setMethod = useBasketStore((s) => s.setMethod);
  const timing = useBasketStore((s) => s.timing);
  const setTiming = useBasketStore((s) => s.setTiming);
  const scheduledDate = useBasketStore((s) => s.scheduledDate);
  const scheduledTime = useBasketStore((s) => s.scheduledTime);
  const setSchedule = useBasketStore((s) => s.setSchedule);

  const status = useOpeningStatus(business, weeklyHours, specialHours);

  if (!mounted) return null;

  if (lines.length === 0) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center px-4 py-24 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-char-900/5">
          <ShoppingBag className="h-7 w-7 text-char-400" />
        </div>
        <h1 className="mt-6 font-display text-2xl uppercase tracking-tight text-char-900">Your basket is empty</h1>
        <p className="mt-2 text-char-500">Add something delicious from the menu to get started.</p>
        <Button asChild size="lg" className="mt-8">
          <Link href="/menu">Browse Menu</Link>
        </Button>
      </div>
    );
  }

  const asapBlocked = timing === "asap" && status && !status.isOpen;
  const scheduleIncomplete = timing === "scheduled" && (!scheduledDate || !scheduledTime);
  const canContinue = !asapBlocked && !scheduleIncomplete && !business.orderingPaused;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <h1 className="font-display text-4xl uppercase tracking-tight text-char-900 sm:text-5xl">Your Order</h1>

      {business.orderingPaused && (
        <div className="mt-6 flex items-start gap-3 rounded-2xl bg-fire-500/10 p-4 text-sm text-fire-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{business.orderingPausedMessage || "Ordering paused right now. Check back shortly."}</p>
        </div>
      )}

      <div className="mt-6 divide-y divide-char-200 rounded-2xl border border-char-200 bg-cream-50 px-5">
        {lines.map((line) => (
          <BasketItem key={line.lineId} line={line} />
        ))}
      </div>
      <Link href="/menu" className="mt-3 inline-block text-sm font-semibold text-fire-600 hover:underline">
        + Add more items
      </Link>

      <section className="mt-8">
        <h2 className="font-display text-xl text-char-900">How would you like it?</h2>
        <div className="mt-3">
          <OrderTypeSelector value={method} onChange={setMethod} deliveryEnabled={business.deliveryEnabled} />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="font-display text-xl text-char-900">When?</h2>
        {asapBlocked && (
          <p className="mt-2 flex items-center gap-1.5 text-sm text-fire-600">
            <AlertTriangle className="h-3.5 w-3.5" /> We&apos;re closed right now. Choose a time below{business.scheduledOrdersEnabled ? "" : " or check back later"}.
          </p>
        )}
        <div className="mt-3">
          <TimeSlotPicker
            business={business}
            weeklyHours={weeklyHours}
            specialHours={specialHours}
            method={method}
            timing={timing}
            onTimingChange={setTiming}
            scheduledDate={scheduledDate}
            scheduledTime={scheduledTime}
            onScheduleChange={setSchedule}
          />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="font-display text-xl text-char-900">Promo Code</h2>
        <PromoCodeInput />
      </section>

      <Separator className="my-8" />

      <OrderSummary subtotalMinor={subtotal} deliveryNote={method === "delivery" ? "Calculated at checkout" : undefined} />

      <Button size="xl" className="mt-6 w-full" disabled={!canContinue} onClick={() => router.push("/checkout")}>
        Continue to Checkout <ArrowRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
