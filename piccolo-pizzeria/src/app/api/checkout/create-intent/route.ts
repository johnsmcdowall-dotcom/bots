import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { checkoutRequestSchema } from "@/lib/validations/checkout";
import { getBusinessSettings, getDeliveryZones, getOpeningStatus, getSpecialHours, getWeeklyHours } from "@/lib/data/business";
import { getMenu, getPromoCodes } from "@/lib/data/menu";
import { getBookedCounts, createPendingOrder, attachPaymentIntent, markOrderPaid } from "@/lib/data/orders";
import { calculateOrder, PricingError } from "@/lib/pricing";
import { generateSlots } from "@/lib/slots";
import { getStripeClient } from "@/lib/stripe";
import { isStripeConfigured } from "@/lib/config";
import { sendOrderReceivedEmail } from "@/lib/email";

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
    requestedTime = new Date(`${dateISO}T${time}:00`);

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

  const order = await createPendingOrder({
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
  });

  if (!isStripeConfigured) {
    // Demo mode: no Stripe keys configured, so we can't take a real payment.
    // Mark the order paid immediately so the full flow can still be tested.
    await markOrderPaid(order.id);
    await sendOrderReceivedEmail({ ...order, status: "received", paymentStatus: "paid" });
    return NextResponse.json({
      demoMode: true,
      orderId: order.id,
      orderNumber: order.orderNumber,
      totalMinor: priced.totalMinor,
    });
  }

  const stripe = getStripeClient()!;
  const intent = await stripe.paymentIntents.create({
    amount: priced.totalMinor,
    currency: "gbp",
    automatic_payment_methods: { enabled: true },
    metadata: { orderId: order.id, orderNumber: order.orderNumber },
    receipt_email: input.customer.email,
  });
  await attachPaymentIntent(order.id, intent.id);

  return NextResponse.json({
    demoMode: false,
    clientSecret: intent.client_secret,
    orderId: order.id,
    orderNumber: order.orderNumber,
    totalMinor: priced.totalMinor,
  });
}
