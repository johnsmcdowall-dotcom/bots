import { describe, expect, it, vi } from "vitest";
import {
  createPendingOrder,
  getBookedCounts,
  getOrderByIdempotencyKey,
  getOrderById,
  markOrderPaid,
  markOrderPaymentFailed,
  updateOrderStatus,
} from "./orders";
import { memoryOrders } from "./memory-store";
import { londonDateISO, londonWallTimeToUTC } from "@/lib/timezone";

// These tests exercise the in-memory fallback store (the same code path
// used whenever Supabase isn't configured, e.g. local dev/demo mode) since
// that's what's available without a live database in this environment. The
// Supabase-backed branches mirror the same logic against real tables and
// are covered by manual verification against a live project.

function orderInput(overrides: { customer?: { firstName: string; lastName: string; phone: string; email: string }; idempotencyKey: string }) {
  return {
    method: "collection" as const,
    timing: "asap" as const,
    requestedTime: new Date().toISOString(),
    customer: overrides.customer ?? { firstName: "Jane", lastName: "Doe", phone: "07700900111", email: "jane@example.com" },
    items: [{ productId: "p-margherita", name: "Margherita", unitPriceMinor: 1000, quantity: 1, lineTotalMinor: 1000, modifiers: [] }],
    subtotalMinor: 1000,
    deliveryFeeMinor: 0,
    discountMinor: 0,
    totalMinor: 1000,
    idempotencyKey: overrides.idempotencyKey,
  };
}

describe("createPendingOrder", () => {
  it("persists the real product id on each order item (Stage 1 fix)", async () => {
    const { order } = await createPendingOrder(orderInput({ idempotencyKey: crypto.randomUUID() }));

    expect(order.items[0].productId).toBe("p-margherita");

    const fetched = await getOrderById(order.id);
    expect(fetched?.items[0].productId).toBe("p-margherita");
  });
});

describe("checkout idempotency (production audit fix: refresh/double-submit must not duplicate orders)", () => {
  it("double click: two sequential calls with the same key return isNew true then false, same order", async () => {
    const key = crypto.randomUUID();
    const customer = { firstName: "Double", lastName: "Click", phone: "07700900101", email: `double-click-${key}@example.com` };
    const first = await createPendingOrder(orderInput({ customer, idempotencyKey: key }));
    expect(first.isNew).toBe(true);

    const second = await createPendingOrder(orderInput({ customer, idempotencyKey: key }));
    expect(second.isNew).toBe(false);
    expect(second.order.id).toBe(first.order.id);

    // Exactly one order actually exists in the store for this attempt.
    const allWithThatEmail = [...memoryOrders.values()].filter((o) => o.customer.email === customer.email);
    expect(allWithThatEmail).toHaveLength(1);
  });

  it("request retry: a client retry after a dropped response reuses the key and never creates a second order", async () => {
    const key = crypto.randomUUID();
    const original = await createPendingOrder(orderInput({ idempotencyKey: key }));
    // Simulate the client never seeing the response and retrying the exact
    // same POST body (same idempotencyKey) a moment later.
    const retry = await createPendingOrder(orderInput({ idempotencyKey: key }));

    expect(retry.isNew).toBe(false);
    expect(retry.order.id).toBe(original.order.id);
  });

  it("page refresh/retry: the same key looked up independently resolves to the already-created order", async () => {
    const key = crypto.randomUUID();
    const { order } = await createPendingOrder(orderInput({ idempotencyKey: key }));

    // A refreshed page doesn't have the in-memory order — it only has the
    // persisted idempotency key — so this is the exact lookup the route's
    // fast path performs before doing any new work.
    const found = await getOrderByIdempotencyKey(key);
    expect(found?.id).toBe(order.id);
  });

  it("two simultaneous checkout requests with the same key resolve to exactly ONE logical order (genuine concurrency, not sequential calls)", async () => {
    const key = crypto.randomUUID();
    // Promise.all starts both calls before either awaits anything, so both
    // reach createPendingOrder's claim logic back-to-back on the same event
    // loop tick — this is a real race between two in-flight requests, not
    // two sequential calls pretending to be concurrent.
    const [a, b] = await Promise.all([
      createPendingOrder(orderInput({ idempotencyKey: key })),
      createPendingOrder(orderInput({ idempotencyKey: key })),
    ]);

    // Exactly one of the two claimed isNew: true; the other lost the race.
    const newCount = [a.isNew, b.isNew].filter(Boolean).length;
    expect(newCount).toBe(1);
    // Both resolve to the identical order — never two different ones.
    expect(a.order.id).toBe(b.order.id);
  });

  it("same idempotency key used concurrently by five requests still yields exactly one new order", async () => {
    const key = crypto.randomUUID();
    const results = await Promise.all(Array.from({ length: 5 }, () => createPendingOrder(orderInput({ idempotencyKey: key }))));

    const newCount = results.filter((r) => r.isNew).length;
    expect(newCount).toBe(1);
    const distinctOrderIds = new Set(results.map((r) => r.order.id));
    expect(distinctOrderIds.size).toBe(1);
  });

  it("a different, legitimate checkout attempt (different key) creates a genuinely new order, even with identical basket contents", async () => {
    const customer = { firstName: "Repeat", lastName: "Customer", phone: "07700900199", email: "repeat@example.com" };
    const firstAttempt = await createPendingOrder(orderInput({ customer, idempotencyKey: crypto.randomUUID() }));
    // Same customer, same basket — but a genuinely separate attempt (e.g.
    // they finished one order, then came back and ordered the same thing
    // again). Requirement: this must NOT be treated as a duplicate.
    const secondAttempt = await createPendingOrder(orderInput({ customer, idempotencyKey: crypto.randomUUID() }));

    expect(firstAttempt.isNew).toBe(true);
    expect(secondAttempt.isNew).toBe(true);
    expect(secondAttempt.order.id).not.toBe(firstAttempt.order.id);
  });

  it("paid order cannot be duplicated: marking the winner paid, then replaying the same key, never creates a second paid order", async () => {
    const key = crypto.randomUUID();
    const customer = { firstName: "Paid", lastName: "Once", phone: "07700900102", email: `paid-once-${key}@example.com` };
    const { order: winner } = await createPendingOrder(orderInput({ customer, idempotencyKey: key }));
    await markOrderPaid(winner.id);

    // A late duplicate/retry of the exact same checkout attempt arrives
    // after payment already completed.
    const replay = await createPendingOrder(orderInput({ idempotencyKey: key }));
    expect(replay.isNew).toBe(false);
    expect(replay.order.id).toBe(winner.id);

    const paidOrders = [...memoryOrders.values()].filter(
      (o) => o.customer.email === winner.customer.email && o.paymentStatus === "paid"
    );
    expect(paidOrders).toHaveLength(1);
  });
});

describe("payment status idempotency", () => {
  async function makeOrder() {
    return createPendingOrder(orderInput({ idempotencyKey: crypto.randomUUID() })).then((r) => r.order);
  }

  it("markOrderPaid is idempotent and markOrderPaid then markOrderPaymentFailed doesn't downgrade a paid order", async () => {
    const order = await makeOrder();
    await markOrderPaid(order.id);
    const paid = await getOrderById(order.id);
    expect(paid?.paymentStatus).toBe("paid");
    expect(paid?.status).toBe("received");

    // A late/duplicate "succeeded" webhook must not change anything further.
    await markOrderPaid(order.id);
    const stillPaid = await getOrderById(order.id);
    expect(stillPaid?.paymentStatus).toBe("paid");

    // An out-of-order "failed" event arriving after "succeeded" must never
    // downgrade an already-paid order.
    await markOrderPaymentFailed(order.id);
    const stillPaidAfterFailed = await getOrderById(order.id);
    expect(stillPaidAfterFailed?.paymentStatus).toBe("paid");
  });

  it("markOrderPaymentFailed does mark a still-pending order as failed", async () => {
    const order = await makeOrder();
    await markOrderPaymentFailed(order.id);
    const failed = await getOrderById(order.id);
    expect(failed?.paymentStatus).toBe("failed");
  });

  it("webhook retry remains idempotent: many concurrent 'payment succeeded' deliveries for the same order still leave it paid exactly once", async () => {
    const order = await makeOrder();

    // Stripe explicitly does not guarantee exactly-once or ordered webhook
    // delivery — simulate several concurrent retries of the same event.
    const results = await Promise.all(Array.from({ length: 6 }, () => markOrderPaid(order.id)));
    const trueCount = results.filter(Boolean).length;
    expect(trueCount).toBe(1);

    const paid = await getOrderById(order.id);
    expect(paid?.paymentStatus).toBe("paid");
    expect(paid?.status).toBe("received");
  });
});

describe("getBookedCounts excludes abandoned pending orders (production audit fix)", () => {
  it("stops counting a pending_payment order toward slot capacity once it's stale, but still counts a fresh one", async () => {
    const dateISO = londonDateISO();
    const time = "13:37";

    const { order: stale } = await createPendingOrder({
      method: "collection",
      timing: "scheduled",
      requestedTime: londonWallTimeToUTC(dateISO, time).toISOString(),
      customer: { firstName: "Stale", lastName: "Order", phone: "07700900111", email: "stale@example.com" },
      items: [{ productId: "p-margherita", name: "Margherita", unitPriceMinor: 1000, quantity: 1, lineTotalMinor: 1000, modifiers: [] }],
      subtotalMinor: 1000,
      deliveryFeeMinor: 0,
      discountMinor: 0,
      totalMinor: 1000,
      idempotencyKey: crypto.randomUUID(),
    });
    // Backdate it past the abandonment window, as if the customer walked
    // away mid-checkout half an hour ago and never came back.
    const staleRecord = memoryOrders.get(stale.id)!;
    staleRecord.createdAt = new Date(Date.now() - 30 * 60_000).toISOString();

    const { order: fresh } = await createPendingOrder({
      method: "collection",
      timing: "scheduled",
      requestedTime: londonWallTimeToUTC(dateISO, time).toISOString(),
      customer: { firstName: "Fresh", lastName: "Order", phone: "07700900112", email: "fresh@example.com" },
      items: [{ productId: "p-margherita", name: "Margherita", unitPriceMinor: 1000, quantity: 1, lineTotalMinor: 1000, modifiers: [] }],
      subtotalMinor: 1000,
      deliveryFeeMinor: 0,
      discountMinor: 0,
      totalMinor: 1000,
      idempotencyKey: crypto.randomUUID(),
    });

    const counts = await getBookedCounts(dateISO, "collection");
    // Only the fresh, still-might-be-paying-any-second order holds the
    // slot; the abandoned one from half an hour ago must not.
    expect(counts[time]).toBe(1);

    memoryOrders.delete(stale.id);
    memoryOrders.delete(fresh.id);
  });
});

describe("updateOrderStatus ready-email dedup (Stage 4)", () => {
  async function makeOrder() {
    return createPendingOrder(orderInput({ idempotencyKey: crypto.randomUUID() })).then((r) => r.order);
  }

  it("sends the ready email once on the transition into ready, not again on a retried/re-saved status", async () => {
    const order = await makeOrder();
    const infoSpy = vi.spyOn(console, "info").mockImplementation(() => {});

    await updateOrderStatus(order.id, "accepted");
    await updateOrderStatus(order.id, "preparing");
    await updateOrderStatus(order.id, "ready");
    const readyEmailCalls = () => infoSpy.mock.calls.filter((c) => String(c[0]).includes("is ready")).length;
    expect(readyEmailCalls()).toBe(1);

    // Retrying/re-saving the same "ready" status (e.g. a duplicate admin
    // click) must not send a second email.
    await updateOrderStatus(order.id, "ready");
    expect(readyEmailCalls()).toBe(1);

    // Leaving and genuinely re-entering ready is a real transition again.
    await updateOrderStatus(order.id, "preparing");
    await updateOrderStatus(order.id, "ready");
    expect(readyEmailCalls()).toBe(2);

    infoSpy.mockRestore();
  });
});
