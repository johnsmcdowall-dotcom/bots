import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { getStripeClient } from "@/lib/stripe";
import { getOrderById, hasProcessedWebhookEvent, markOrderPaid, markOrderPaymentFailed, recordWebhookEvent } from "@/lib/data/orders";
import { sendOrderReceivedEmail } from "@/lib/email";

/**
 * Stripe webhook — the authoritative source of truth for payment status.
 * Verifies the signature, de-duplicates by event id (Stripe retries and can
 * send the same event more than once), and only then mutates the order.
 */
export async function POST(request: NextRequest) {
  const stripe = getStripeClient();
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!stripe || !webhookSecret) {
    return NextResponse.json({ error: "Stripe is not configured" }, { status: 501 });
  }

  const signature = request.headers.get("stripe-signature");
  if (!signature) {
    return NextResponse.json({ error: "Missing signature" }, { status: 400 });
  }

  const rawBody = await request.text();

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Invalid signature";
    return NextResponse.json({ error: `Webhook signature verification failed: ${message}` }, { status: 400 });
  }

  if (await hasProcessedWebhookEvent(event.id)) {
    return NextResponse.json({ received: true, duplicate: true });
  }

  switch (event.type) {
    case "payment_intent.succeeded": {
      const intent = event.data.object as Stripe.PaymentIntent;
      const orderId = intent.metadata?.orderId;
      if (orderId) {
        await markOrderPaid(orderId);
        const order = await getOrderById(orderId);
        if (order) await sendOrderReceivedEmail(order);
      }
      break;
    }
    case "payment_intent.payment_failed": {
      const intent = event.data.object as Stripe.PaymentIntent;
      const orderId = intent.metadata?.orderId;
      if (orderId) await markOrderPaymentFailed(orderId);
      break;
    }
    default:
      break;
  }

  await recordWebhookEvent(event.id, event.type);

  return NextResponse.json({ received: true });
}
