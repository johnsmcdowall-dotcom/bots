import { describe, expect, it } from "vitest";
import { createPendingOrder, getOrderById, markOrderPaid, markOrderPaymentFailed } from "./orders";

// These tests exercise the in-memory fallback store (the same code path
// used whenever Supabase isn't configured, e.g. local dev/demo mode) since
// that's what's available without a live database in this environment. The
// Supabase-backed branches mirror the same logic against real tables and
// are covered by manual verification against a live project.

describe("createPendingOrder", () => {
  it("persists the real product id on each order item (Stage 1 fix)", async () => {
    const order = await createPendingOrder({
      method: "collection",
      timing: "asap",
      requestedTime: new Date().toISOString(),
      customer: { firstName: "Jane", lastName: "Doe", phone: "07700900111", email: "jane@example.com" },
      items: [
        {
          productId: "p-margherita",
          name: "Margherita",
          unitPriceMinor: 1000,
          quantity: 1,
          lineTotalMinor: 1000,
          modifiers: [],
        },
      ],
      subtotalMinor: 1000,
      deliveryFeeMinor: 0,
      discountMinor: 0,
      totalMinor: 1000,
    });

    expect(order.items[0].productId).toBe("p-margherita");

    const fetched = await getOrderById(order.id);
    expect(fetched?.items[0].productId).toBe("p-margherita");
  });
});

describe("payment status idempotency", () => {
  async function makeOrder() {
    return createPendingOrder({
      method: "collection",
      timing: "asap",
      requestedTime: new Date().toISOString(),
      customer: { firstName: "Jane", lastName: "Doe", phone: "07700900111", email: "jane@example.com" },
      items: [{ productId: "p-margherita", name: "Margherita", unitPriceMinor: 1000, quantity: 1, lineTotalMinor: 1000, modifiers: [] }],
      subtotalMinor: 1000,
      deliveryFeeMinor: 0,
      discountMinor: 0,
      totalMinor: 1000,
    });
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
});
