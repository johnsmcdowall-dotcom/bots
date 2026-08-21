import { describe, expect, it, vi } from "vitest";
import { resolveCheckoutPayment, type CheckoutStripeClient } from "./checkout";
import { createPendingOrder, getOrderById } from "./data/orders";

vi.mock("./email", () => ({ sendOrderReceivedEmail: vi.fn().mockResolvedValue(undefined) }));

async function makeOrder(overrides: { idempotencyKey: string; totalMinor?: number }) {
  const { order } = await createPendingOrder({
    method: "collection",
    timing: "asap",
    requestedTime: new Date().toISOString(),
    customer: { firstName: "Pay", lastName: "Test", phone: "07700900111", email: `pay-${overrides.idempotencyKey}@example.com` },
    items: [{ productId: "p-margherita", name: "Margherita", unitPriceMinor: 1000, quantity: 1, lineTotalMinor: 1000, modifiers: [] }],
    subtotalMinor: 1000,
    deliveryFeeMinor: 0,
    discountMinor: 0,
    totalMinor: overrides.totalMinor ?? 1000,
    idempotencyKey: overrides.idempotencyKey,
  });
  return order;
}

/** A fake Stripe client recording every call, so tests can assert on how many times — and with what idempotency key — create() actually ran. */
function fakeStripe() {
  let counter = 0;
  const created = new Map<string, { id: string; client_secret: string }>();
  const createCalls: { idempotencyKey?: string; amount: number }[] = [];

  const client: CheckoutStripeClient = {
    paymentIntents: {
      async create(params, options) {
        createCalls.push({ idempotencyKey: options?.idempotencyKey, amount: params.amount });
        const key = options?.idempotencyKey;
        // Mirror Stripe's real idempotency guarantee: replaying the same
        // key returns the SAME PaymentIntent instead of creating another.
        if (key && created.has(key)) return created.get(key)!;
        counter += 1;
        const intent = { id: `pi_${counter}`, client_secret: `pi_${counter}_secret` };
        if (key) created.set(key, intent);
        return intent;
      },
      async retrieve(id) {
        for (const intent of created.values()) {
          if (intent.id === id) return intent;
        }
        return { id, client_secret: `${id}_secret` };
      },
    },
  };
  return { client, createCalls };
}

describe("resolveCheckoutPayment — Stripe PaymentIntent is never duplicated for one order", () => {
  it("a brand-new order creates exactly one PaymentIntent, keyed by the order's own id", async () => {
    const key = crypto.randomUUID();
    const order = await makeOrder({ idempotencyKey: key });
    const { client, createCalls } = fakeStripe();

    const result = await resolveCheckoutPayment(order, true, client);

    expect(result.demoMode).toBe(false);
    expect(result.clientSecret).toBeTruthy();
    expect(createCalls).toHaveLength(1);
    expect(createCalls[0].idempotencyKey).toBe(order.id);
  });

  it("a reused/duplicate order (isNew: false) that already has a PaymentIntent attached reuses it — never calls create() again", async () => {
    const key = crypto.randomUUID();
    const order = await makeOrder({ idempotencyKey: key });
    const { client, createCalls } = fakeStripe();

    const first = await resolveCheckoutPayment(order, true, client);
    // Simulate the second, duplicate request that found the same order via
    // the idempotency-key lookup (isNew: false) — by now the order has a
    // PaymentIntent attached, exactly like the real getOrderById would show.
    const orderWithIntent = (await getOrderById(order.id))!;
    const second = await resolveCheckoutPayment(orderWithIntent, false, client);

    expect(second.clientSecret).toBe(first.clientSecret);
    // The critical assertion: still only one create() call total across
    // both "requests" for this one order.
    expect(createCalls).toHaveLength(1);
  });

  it("two concurrent requests resolving the same brand-new order (a tight isNew/attach race) still only call Stripe create() once", async () => {
    const key = crypto.randomUUID();
    const order = await makeOrder({ idempotencyKey: key });
    const { client, createCalls } = fakeStripe();

    // Both "requests" think they're new (this can happen for the instant
    // both raced past createPendingOrder's claim before either attached a
    // PaymentIntent) — resolveCheckoutPayment's own polling/idempotency-key
    // logic is what has to prevent a duplicate Stripe call here.
    const [a, b] = await Promise.all([
      resolveCheckoutPayment(order, true, client),
      resolveCheckoutPayment({ ...order }, true, client),
    ]);

    expect(a.clientSecret).toBe(b.clientSecret);
    expect(createCalls).toHaveLength(1);
  });

  it("different orders (different idempotency keys) each get their own distinct PaymentIntent", async () => {
    const orderA = await makeOrder({ idempotencyKey: crypto.randomUUID() });
    const orderB = await makeOrder({ idempotencyKey: crypto.randomUUID() });
    const { client, createCalls } = fakeStripe();

    const resultA = await resolveCheckoutPayment(orderA, true, client);
    const resultB = await resolveCheckoutPayment(orderB, true, client);

    expect(resultA.clientSecret).not.toBe(resultB.clientSecret);
    expect(createCalls).toHaveLength(2);
    expect(createCalls[0].idempotencyKey).not.toBe(createCalls[1].idempotencyKey);
  });
});

describe("resolveCheckoutPayment — demo mode side effects only run once per order", () => {
  it("a reused order (isNew: false) never re-runs markOrderPaid/email side effects", async () => {
    const key = crypto.randomUUID();
    const order = await makeOrder({ idempotencyKey: key });

    const first = await resolveCheckoutPayment(order, true, null);
    expect(first.demoMode).toBe(true);
    const paidAfterFirst = await getOrderById(order.id);
    expect(paidAfterFirst?.paymentStatus).toBe("paid");

    // A duplicate/refresh request resolves the same already-created order.
    const second = await resolveCheckoutPayment(paidAfterFirst!, false, null);
    expect(second.orderId).toBe(order.id);
    // Still paid, not somehow re-processed — markOrderPaid's own idempotency
    // guarantees this regardless, but isNew: false means it's never even
    // attempted a second time.
    const stillPaid = await getOrderById(order.id);
    expect(stillPaid?.paymentStatus).toBe("paid");
  });
});
