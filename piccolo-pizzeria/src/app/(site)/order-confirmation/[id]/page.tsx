import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { PartyPopper, MapPin, Phone, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { OrderStatusTracker } from "@/components/order/OrderStatusTracker";
import { AutoRefresh } from "@/components/order/AutoRefresh";
import { ClearBasketOnMount } from "@/components/checkout/ClearBasketOnMount";
import { getOrderById } from "@/lib/data/orders";
import { getBusinessSettings } from "@/lib/data/business";
import { formatMoney, formatOrderDateTime, summaryModifiers } from "@/lib/format";

export const metadata: Metadata = {
  title: "Order Confirmation",
  robots: { index: false },
};

export default async function OrderConfirmationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [order, business] = await Promise.all([getOrderById(id), getBusinessSettings()]);

  if (!order) notFound();

  const isPending = order.paymentStatus === "pending";
  const mapsQuery = encodeURIComponent(`${business.addressLine1}, ${business.city}, ${business.postcode}`);

  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6 sm:py-16">
      <ClearBasketOnMount />
      <AutoRefresh active={isPending} />

      {isPending ? (
        <div className="text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-ember-400/15">
            <Clock className="h-6 w-6 animate-pulse text-ember-500" />
          </div>
          <h1 className="mt-5 font-display text-2xl text-char-900 sm:text-3xl">Confirming your payment…</h1>
          <p className="mt-2 text-char-500">This usually takes a few seconds. This page will update automatically.</p>
        </div>
      ) : (
        <div className="text-center animate-fade-up">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-basil-500/15">
            <PartyPopper className="h-6 w-6 text-basil-600" />
          </div>
          <h1 className="mt-5 text-balance font-display text-3xl uppercase tracking-tight text-char-900 sm:text-4xl">
            Order&apos;s In.
          </h1>
          <p className="mt-1 text-char-600">Thanks, {order.customer.firstName}.</p>
          <p className="mt-2 text-char-500">Order #{order.orderNumber}</p>
        </div>
      )}

      <div className="mt-10 rounded-2xl border border-char-200 bg-cream-50 p-6">
        <OrderStatusTracker status={order.status} />

        <Separator className="my-6" />

        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold uppercase tracking-wide text-char-400">
            {order.method === "delivery" ? "Delivery" : "Collection"}
          </span>
          <span className="font-display text-lg text-char-900">{formatOrderDateTime(order.requestedTime)}</span>
        </div>

        <Separator className="my-6" />

        <ul className="space-y-3">
          {order.items.map((item, idx) => (
            <li key={idx} className="flex justify-between gap-3 text-sm">
              <div>
                <p className="font-medium text-char-800">
                  {item.quantity}× {item.name}
                </p>
                {summaryModifiers(item.modifiers).length > 0 && (
                  <p className="text-char-400">{summaryModifiers(item.modifiers).map((m) => m.optionName).join(", ")}</p>
                )}
              </div>
              <span className="shrink-0 text-char-600">{formatMoney(item.lineTotalMinor)}</span>
            </li>
          ))}
        </ul>

        <Separator className="my-6" />

        <div className="space-y-1.5 text-sm">
          <div className="flex justify-between text-char-600">
            <span>Subtotal</span>
            <span>{formatMoney(order.subtotalMinor)}</span>
          </div>
          {order.deliveryFeeMinor > 0 && (
            <div className="flex justify-between text-char-600">
              <span>Delivery</span>
              <span>{formatMoney(order.deliveryFeeMinor)}</span>
            </div>
          )}
          {order.discountMinor > 0 && (
            <div className="flex justify-between text-basil-600">
              <span>Discount{order.promoCode ? ` (${order.promoCode})` : ""}</span>
              <span>-{formatMoney(order.discountMinor)}</span>
            </div>
          )}
          <div className="flex justify-between pt-2 font-display text-lg text-char-900">
            <span>Total Paid</span>
            <span>{formatMoney(order.totalMinor)}</span>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-3 rounded-2xl border border-char-200 bg-cream-50 p-6 text-sm text-char-600">
        <p className="flex items-center gap-2">
          <MapPin className="h-4 w-4 shrink-0 text-fire-500" />
          {business.addressLine1}, {business.city}, {business.postcode}
        </p>
        <p className="flex items-center gap-2">
          <Phone className="h-4 w-4 shrink-0 text-fire-500" />
          <a href={`tel:${business.phone.replace(/\s+/g, "")}`} className="hover:text-char-900">
            {business.phone}
          </a>
        </p>
      </div>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <Button asChild size="lg" variant="outline" className="flex-1">
          <a href={`https://www.google.com/maps/search/?api=1&query=${mapsQuery}`} target="_blank" rel="noreferrer">
            Get Directions
          </a>
        </Button>
        <Button asChild size="lg" className="flex-1">
          <Link href="/menu">Order Again</Link>
        </Button>
      </div>
    </div>
  );
}
