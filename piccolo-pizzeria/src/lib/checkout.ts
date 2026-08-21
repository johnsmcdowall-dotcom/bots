import "server-only";
import { attachPaymentIntent, getOrderById, markOrderPaid } from "@/lib/data/orders";
import { sendOrderReceivedEmail } from "@/lib/email";
import type { OrderRecord } from "@/lib/types";

/**
 * The minimal shape of a Stripe client this module needs — deliberately not
 * `import type Stripe from "stripe"` for the whole client, so a test can
 * pass a plain object literal instead of standing up the real SDK. The real
 * `getStripeClient()` result satisfies this structurally (it has strictly
 * more fields), so production callers pass it straight through.
 */
export interface CheckoutStripeClient {
  paymentIntents: {
    create(
      params: {
        amount: number;
        currency: string;
        automatic_payment_methods?: { enabled: boolean };
        metadata?: Record<string, string>;
        receipt_email?: string;
      },
      options?: { idempotencyKey?: string }
    ): Promise<{ id: string; client_secret: string | null }>;
    retrieve(id: string): Promise<{ id: string; client_secret: string | null }>;
  };
}

export interface CheckoutResult {
  demoMode: boolean;
  clientSecret?: string;
  orderId: string;
  orderNumber: string;
  totalMinor: number;
}

const PAYMENT_INTENT_ATTACH_POLL_ATTEMPTS = 5;
const PAYMENT_INTENT_ATTACH_POLL_DELAY_MS = 250;

/**
 * Given an order that createPendingOrder just resolved — either genuinely
 * new (isNew: true) or an already-existing one found via idempotency-key
 * lookup (isNew: false: a concurrent duplicate request, a page refresh, or
 * a client/network retry) — produces the exact response the client needs,
 * without ever running a one-time side effect (marking paid, emailing,
 * creating a Stripe PaymentIntent) more than once for the same order.
 *
 * This is the single place that decides "does this request get to drive
 * the order forward, or just report back what's already happening." Kept
 * as a plain function (not inlined in the route handler) so it's testable
 * with a fake Stripe client and the real in-memory order store, with no
 * Next.js request/response machinery involved.
 */
export async function resolveCheckoutPayment(
  order: OrderRecord,
  isNew: boolean,
  stripe: CheckoutStripeClient | null
): Promise<CheckoutResult> {
  if (!stripe) {
    // Demo mode (no Stripe keys configured): only the request that actually
    // just created the order drives it to paid. A reused/duplicate request
    // (isNew: false) must not re-run this — markOrderPaid is independently
    // idempotent too, so calling it again would be harmless, but skipping it
    // here keeps this function's contract simple: side effects belong to
    // the winner alone.
    if (isNew) {
      await markOrderPaid(order.id);
      await sendOrderReceivedEmail({ ...order, status: "received", paymentStatus: "paid" });
    }
    return { demoMode: true, orderId: order.id, orderNumber: order.orderNumber, totalMinor: order.totalMinor };
  }

  const clientSecret = await ensureStripePaymentIntent(order, stripe);
  return { demoMode: false, clientSecret, orderId: order.id, orderNumber: order.orderNumber, totalMinor: order.totalMinor };
}

/**
 * Attaches exactly one Stripe PaymentIntent to this order, no matter how
 * many requests are trying to resolve the same idempotency key at once.
 *
 * - If a PaymentIntent is already attached (the common case for a
 *   duplicate/reused request arriving after the original had time to
 *   finish), reuse it — never create a second one for the same order.
 * - If two requests reach this function for the same brand-new order at
 *   nearly the same instant, only one of them actually got isNew: true from
 *   createPendingOrder's atomic claim — but both could still, in principle,
 *   reach this point before the winner has attached its PaymentIntent id.
 *   Rather than have the loser race Stripe with its own create() call, it
 *   polls briefly for the winner to finish attaching.
 * - Only as a last resort (the poll timed out — most likely because the
 *   original attacher crashed before persisting the id, not because it's
 *   merely slow) does this call Stripe itself, and even then it uses the
 *   order's own id as the Stripe idempotency key: stable for the order's
 *   entire lifetime, so if the "crashed" request actually did reach Stripe
 *   before dying, Stripe returns that exact same PaymentIntent instead of
 *   creating a duplicate charge.
 */
async function ensureStripePaymentIntent(order: OrderRecord, stripe: CheckoutStripeClient): Promise<string> {
  let current = order;

  if (!current.stripePaymentIntentId) {
    for (let attempt = 0; attempt < PAYMENT_INTENT_ATTACH_POLL_ATTEMPTS && !current.stripePaymentIntentId; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, PAYMENT_INTENT_ATTACH_POLL_DELAY_MS));
      current = (await getOrderById(order.id)) ?? current;
    }
  }

  if (current.stripePaymentIntentId) {
    const intent = await stripe.paymentIntents.retrieve(current.stripePaymentIntentId);
    if (intent.client_secret) return intent.client_secret;
  }

  const intent = await stripe.paymentIntents.create(
    {
      amount: current.totalMinor,
      currency: "gbp",
      automatic_payment_methods: { enabled: true },
      metadata: { orderId: current.id, orderNumber: current.orderNumber },
      receipt_email: current.customer.email,
    },
    { idempotencyKey: current.id }
  );
  await attachPaymentIntent(current.id, intent.id);
  if (!intent.client_secret) throw new Error(`Stripe PaymentIntent ${intent.id} has no client secret`);
  return intent.client_secret;
}
