import { describe, expect, it, vi } from "vitest";
import { createPendingOrder, getOrderById, markOrderPaid, markOrderPaymentFailed, updateOrderStatus } from "./orders";

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

describe("updateOrderStatus ready-email dedup (Stage 4)", () => {
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
