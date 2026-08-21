import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { checkoutRequestSchema } from "@/lib/validations/checkout";
import { getBusinessSettings, getDeliveryZones, getOpeningStatus, getSpecialHours, getWeeklyHours } from "@/lib/data/business";
import { getMenu, getPromoCodes } from "@/lib/data/menu";
import { getBookedCounts, createPendingOrder, getOrderByIdempotencyKey } from "@/lib/data/orders";
import { calculateOrder, PricingError } from "@/lib/pricing";
import { generateSlots } from "@/lib/slots";
import { getStripeClient } from "@/lib/stripe";
import { resolveCheckoutPayment } from "@/lib/checkout";
import { londonWallTimeToUTC } from "@/lib/timezone";

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  const parsed = checkoutRequestSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: z.prettifyError(parsed.error) }, { status: 400 });
  }
  const input = parsed.data;

  // Fast path: this exact checkout attempt (same client-generated
  // idempotency key) has already been handled, or is being handled right
  // now by another request. Skip straight to resolving a response from the
  // order that already exists — never re-validate hours/slots or recompute
  // pricing for a retry/duplicate, since that could legitimately produce a
  // different number the second time around (a promo's usage limit hit in
  // between, say) and Stripe would then reject a mismatched replay.
  const existingByKey = await getOrderByIdempotencyKey(input.idempotencyKey);
  if (existingByKey) {
    return NextResponse.json(await resolveCheckoutPayment(existingByKey, false, getStripeClient()));
  }

  const [business, weeklyHours, specialHours, openingStatus] = await Promise.all([
    getBusinessSettings(),
    getWeeklyHours(),
    getSpecialHours(),
    getOpeningStatus(),
  ]);

  if (business.orderingPaused) {
    return NextResponse.json({ error: business.orderingPausedMessage || "Ordering is currently paused." }, { status: 409 });
  }

  let requestedTime: Date;
  if (input.timing === "asap") {
    if (!business.asapOrdersEnabled) {
      return NextResponse.json({ error: "ASAP orders aren't available right now — please choose a time." }, { status: 409 });
    }
    if (!openingStatus.isOpen) {
      return NextResponse.json({ error: "We're closed right now. Please choose a scheduled time." }, { status: 409 });
    }
    requestedTime = new Date(Date.now() + (business.minPrepMinutes + business.currentWaitMinutes) * 60_000);
  } else {
    if (!business.scheduledOrdersEnabled) {
      return NextResponse.json({ error: "Scheduled orders aren't available right now." }, { status: 409 });
    }
    const dateISO = input.scheduledDate!;
    const time = input.scheduledTime!;
    // The slot picker's "18:00" always means 6pm in the business's own
    // timezone (Europe/London) — never the server's. A plain `new Date(...)`
    // on a string with no offset is parsed in the server's local time,
    // which is wrong by an hour whenever BST is in effect on a UTC host.
    requestedTime = londonWallTimeToUTC(dateISO, time);

    const bookedCounts = await getBookedCounts(dateISO, input.method);
    const slots = generateSlots({ dateISO, method: input.method, weeklyHours, specialHours, business, bookedCounts });
    const slot = slots.find((s) => s.time === time);
    if (!slot || !slot.available) {
      return NextResponse.json({ error: "That time slot is no longer available. Please choose another." }, { status: 409 });
    }
  }

  const [{ products, modifierGroups }, deliveryZones, promoCodes] = await Promise.all([
    getMenu(),
    getDeliveryZones(),
    getPromoCodes(),
  ]);

  let priced;
  try {
    priced = calculateOrder(
      {
        lines: input.lines,
        method: input.method,
        postcode: input.address?.postcode,
        promoCode: input.promoCode,
      },
      { products, modifierGroups, deliveryZones, promoCodes }
    );
  } catch (err) {
    if (err instanceof PricingError) {
      return NextResponse.json({ error: err.message, code: err.code }, { status: 409 });
    }
    throw err;
  }

  // createPendingOrder is the real concurrency-safety boundary: if a
  // second request with this same idempotency key raced us here and won,
  // isNew comes back false and `order` is THAT request's order, not a new
  // one — see the migration/function comments for how the claim is atomic
  // in both the database and in-memory branches.
  const { order, isNew } = await createPendingOrder({
    method: input.method,
    timing: input.timing,
    requestedTime: requestedTime.toISOString(),
    customer: input.customer,
    address: input.address,
    notes: input.notes,
    items: priced.items,
    subtotalMinor: priced.subtotalMinor,
    deliveryFeeMinor: priced.deliveryFeeMinor,
    discountMinor: priced.discountMinor,
    totalMinor: priced.totalMinor,
    promoCode: priced.promoCode,
    idempotencyKey: input.idempotencyKey,
  });

  return NextResponse.json(await resolveCheckoutPayment(order, isNew, getStripeClient()));
}
