import "server-only";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { getSupabaseAdminClient } from "@/lib/supabase/admin";
import { memoryOrders, memoryWebhookEvents } from "@/lib/data/memory-store";
import { awardLoyaltyPoints } from "@/lib/data/loyalty";
import { sendOrderReadyEmail } from "@/lib/email";
import type {
  OrderItemRecord,
  OrderMethod,
  OrderRecord,
  OrderStatus,
  OrderTiming,
} from "@/lib/types";
import type { OrderItemModifierRow, OrderItemRow, OrderRow } from "@/lib/supabase/database.types";

/**
 * Pushes a tiny, PII-free status ping to anyone watching this order's
 * confirmation page (see OrderStatusListener). Deliberately a Broadcast, not
 * a postgres_changes subscription on `orders` — that table's RLS only grants
 * staff SELECT, and customers have no accounts to grant against, so a direct
 * table subscription from the browser would either see nothing or require
 * opening `orders` up to anonymous reads. Broadcast on an order-scoped topic
 * keeps every other order's data (and this order's own PII) off the wire.
 * Best-effort: a missed broadcast (page not open, socket hiccup) is caught
 * by the page's own slow safety-net poll, so failures here are swallowed.
 */
async function broadcastOrderStatus(supabase: NonNullable<ReturnType<typeof getSupabaseAdminClient>>, orderId: string, status: OrderStatus): Promise<void> {
  try {
    await supabase.channel(`order-status-${orderId}`).send({ type: "broadcast", event: "status", payload: { status } });
  } catch {
    // Swallowed — see comment above.
  }
}

export async function getBookedCounts(dateISO: string, method: OrderMethod): Promise<Record<string, number>> {
  try {
    const supabase = await getSupabaseServerClient();
    if (!supabase) {
      const counts: Record<string, number> = {};
      for (const order of memoryOrders.values()) {
        if (order.method !== method || order.status === "cancelled") continue;
        if (!order.requestedTime.startsWith(dateISO)) continue;
        const time = new Date(order.requestedTime).toISOString().slice(11, 16);
        counts[time] = (counts[time] ?? 0) + 1;
      }
      return counts;
    }

    const start = `${dateISO}T00:00:00.000Z`;
    const end = `${dateISO}T23:59:59.999Z`;
    const { data, error } = await supabase
      .from("orders")
      .select("requested_time")
      .eq("method", method)
      .neq("status", "cancelled")
      .gte("requested_time", start)
      .lte("requested_time", end);
    if (error || !data) return {};

    const counts: Record<string, number> = {};
    for (const row of data as { requested_time: string }[]) {
      const time = new Date(row.requested_time).toISOString().slice(11, 16);
      counts[time] = (counts[time] ?? 0) + 1;
    }
    return counts;
  } catch {
    return {};
  }
}

function generateOrderNumber(): string {
  const tail = Date.now().toString(36).toUpperCase().slice(-5);
  const rand = Math.random().toString(36).toUpperCase().slice(2, 4);
  return `P${tail}${rand}`;
}

export interface CreatePendingOrderInput {
  method: OrderMethod;
  timing: OrderTiming;
  requestedTime: string;
  customer: { firstName: string; lastName: string; phone: string; email: string };
  address?: { line1: string; line2?: string; postcode: string };
  notes?: string;
  items: OrderItemRecord[];
  subtotalMinor: number;
  deliveryFeeMinor: number;
  discountMinor: number;
  totalMinor: number;
  promoCode?: string;
}

export async function createPendingOrder(input: CreatePendingOrderInput): Promise<OrderRecord> {
  const order: OrderRecord = {
    id: crypto.randomUUID(),
    orderNumber: generateOrderNumber(),
    status: "pending_payment",
    method: input.method,
    timing: input.timing,
    requestedTime: input.requestedTime,
    createdAt: new Date().toISOString(),
    customer: input.customer,
    address: input.address,
    notes: input.notes,
    items: input.items,
    subtotalMinor: input.subtotalMinor,
    deliveryFeeMinor: input.deliveryFeeMinor,
    discountMinor: input.discountMinor,
    totalMinor: input.totalMinor,
    promoCode: input.promoCode,
    paymentStatus: "pending",
  };

  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    memoryOrders.set(order.id, order);
    return order;
  }

  const { error: orderError } = await supabase.from("orders").insert({
    id: order.id,
    order_number: order.orderNumber,
    status: order.status,
    method: order.method,
    timing: order.timing,
    requested_time: order.requestedTime,
    customer_first_name: order.customer.firstName,
    customer_last_name: order.customer.lastName,
    customer_phone: order.customer.phone,
    customer_email: order.customer.email,
    address_line1: order.address?.line1 ?? null,
    address_line2: order.address?.line2 ?? null,
    address_postcode: order.address?.postcode ?? null,
    notes: order.notes ?? null,
    subtotal_minor: order.subtotalMinor,
    delivery_fee_minor: order.deliveryFeeMinor,
    discount_minor: order.discountMinor,
    total_minor: order.totalMinor,
    promo_code: order.promoCode ?? null,
    payment_status: order.paymentStatus,
  });
  if (orderError) throw new Error(`Failed to create order: ${orderError.message}`);

  if (order.items.length > 0) {
    const { data: insertedItems, error: itemsError } = await supabase
      .from("order_items")
      .insert(
        order.items.map((item) => ({
          order_id: order.id,
          // Server-validated in calculateOrder() against the real product
          // catalogue — never trust a client-supplied id. Falls back to null
          // only if a product is deleted between pricing and insert (the FK
          // is ON DELETE SET NULL), which historical orders may already have.
          product_id: item.productId || null,
          name: item.name,
          unit_price_minor: item.unitPriceMinor,
          quantity: item.quantity,
          line_total_minor: item.lineTotalMinor,
          notes: item.notes ?? null,
        }))
      )
      .select("id");
    if (itemsError) throw new Error(`Failed to create order items: ${itemsError.message}`);

    const modifierRows = (insertedItems as { id: string }[]).flatMap((row, idx) =>
      order.items[idx].modifiers.map((mod) => ({
        order_item_id: row.id,
        // Server-validated in calculateOrder() alongside product_id — see the
        // comment above for why the id (not just the name) matters.
        group_id: mod.groupId || null,
        option_id: mod.optionId || null,
        group_name: mod.groupName,
        option_name: mod.optionName,
        price_minor: mod.priceMinor,
      }))
    );
    if (modifierRows.length > 0) {
      await supabase.from("order_item_modifiers").insert(modifierRows);
    }
  }

  await supabase.from("order_status_history").insert({ order_id: order.id, status: order.status, changed_by: "system" });

  return order;
}

export async function attachPaymentIntent(orderId: string, paymentIntentId: string): Promise<void> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    const order = memoryOrders.get(orderId);
    if (order) order.stripePaymentIntentId = paymentIntentId;
    return;
  }
  await supabase.from("orders").update({ stripe_payment_intent_id: paymentIntentId }).eq("id", orderId);
}

async function loadOrderFromSupabase(supabase: NonNullable<ReturnType<typeof getSupabaseAdminClient>>, orderId: string): Promise<OrderRecord | null> {
  const { data, error } = await supabase.from("orders").select("*").eq("id", orderId).maybeSingle();
  if (error || !data) return null;
  const row = data as OrderRow;

  const { data: itemsData } = await supabase.from("order_items").select("*").eq("order_id", orderId);
  const items = (itemsData ?? []) as OrderItemRow[];

  const { data: modifiersData } = await supabase
    .from("order_item_modifiers")
    .select("*")
    .in("order_item_id", items.map((i) => i.id).length ? items.map((i) => i.id) : ["00000000-0000-0000-0000-000000000000"]);
  const modifiers = (modifiersData ?? []) as OrderItemModifierRow[];

  return mapRowToOrder(row, items, modifiers);
}

function mapRowToOrder(row: OrderRow, items: OrderItemRow[], modifiers: OrderItemModifierRow[]): OrderRecord {
  return {
    id: row.id,
    orderNumber: row.order_number,
    status: row.status as OrderStatus,
    method: row.method as OrderMethod,
    timing: row.timing as OrderTiming,
    requestedTime: row.requested_time,
    createdAt: row.created_at,
    customer: {
      firstName: row.customer_first_name,
      lastName: row.customer_last_name,
      phone: row.customer_phone,
      email: row.customer_email,
    },
    address: row.address_line1
      ? { line1: row.address_line1, line2: row.address_line2 ?? undefined, postcode: row.address_postcode ?? "" }
      : undefined,
    notes: row.notes ?? undefined,
    items: items.map((item) => ({
      productId: item.product_id ?? "",
      name: item.name,
      unitPriceMinor: item.unit_price_minor,
      quantity: item.quantity,
      lineTotalMinor: item.line_total_minor,
      notes: item.notes ?? undefined,
      modifiers: modifiers
        .filter((m) => m.order_item_id === item.id)
        .map((m) => ({
          groupId: m.group_id ?? "",
          optionId: m.option_id ?? "",
          groupName: m.group_name,
          optionName: m.option_name,
          priceMinor: m.price_minor,
        })),
    })),
    subtotalMinor: row.subtotal_minor,
    deliveryFeeMinor: row.delivery_fee_minor,
    discountMinor: row.discount_minor,
    totalMinor: row.total_minor,
    promoCode: row.promo_code ?? undefined,
    paymentStatus: row.payment_status as OrderRecord["paymentStatus"],
    stripePaymentIntentId: row.stripe_payment_intent_id ?? undefined,
  };
}

export async function getOrderById(orderId: string): Promise<OrderRecord | null> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) return memoryOrders.get(orderId) ?? null;
  return loadOrderFromSupabase(supabase, orderId);
}

export async function getOrderByPaymentIntentId(paymentIntentId: string): Promise<OrderRecord | null> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    for (const order of memoryOrders.values()) {
      if (order.stripePaymentIntentId === paymentIntentId) return order;
    }
    return null;
  }
  const { data } = await supabase.from("orders").select("id").eq("stripe_payment_intent_id", paymentIntentId).maybeSingle();
  if (!data) return null;
  return loadOrderFromSupabase(supabase, (data as { id: string }).id);
}

/** Marks an order paid + received. Idempotent — safe to call twice for the same order. */
export async function markOrderPaid(orderId: string): Promise<void> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    const order = memoryOrders.get(orderId);
    if (order && order.paymentStatus !== "paid") {
      order.paymentStatus = "paid";
      order.status = "received";
    }
    return;
  }
  const { data } = await supabase
    .from("orders")
    .select("payment_status, promo_code, order_number, total_minor, customer_email, customer_phone")
    .eq("id", orderId)
    .maybeSingle();
  const row = data as {
    payment_status?: string;
    promo_code?: string | null;
    order_number: string;
    total_minor: number;
    customer_email: string;
    customer_phone: string;
  } | null;
  if (row?.payment_status === "paid") return;

  await supabase.from("orders").update({ payment_status: "paid", status: "received" }).eq("id", orderId);
  await supabase.from("order_status_history").insert({ order_id: orderId, status: "received", changed_by: "stripe_webhook" });
  await broadcastOrderStatus(supabase, orderId, "received");

  if (row?.promo_code) {
    await supabase.rpc("increment_promo_usage", { promo_code_input: row.promo_code });
  }

  // Architecture-only loyalty ledger (Stage 9) — no customer or staff UI
  // reads this anywhere; the flag just decides whether points quietly
  // accrue in the background.
  const { data: settingsRow } = await supabase.from("business_settings").select("rewards_enabled").eq("id", 1).maybeSingle();
  if (row && (settingsRow as { rewards_enabled?: boolean } | null)?.rewards_enabled) {
    await awardLoyaltyPoints({
      customerEmail: row.customer_email,
      customerPhone: row.customer_phone,
      orderId,
      orderNumber: row.order_number,
      totalMinor: row.total_minor,
    });
  }

  // Decrement limited-stock items only now that payment is confirmed — see
  // 0004_stock.sql for why this is the chosen reservation point (never at
  // order creation, so a failed/abandoned payment never consumes stock).
  // The RPC no-ops (returns false) for products that aren't stock_limited,
  // so this is safe to call unconditionally for every line without an
  // extra lookup first.
  const { data: itemsData } = await supabase.from("order_items").select("product_id, quantity, name").eq("order_id", orderId);
  const items = (itemsData ?? []) as { product_id: string | null; quantity: number; name: string }[];
  const oversoldNames: string[] = [];
  for (const item of items) {
    if (!item.product_id) continue;
    const { data: product } = await supabase.from("products").select("stock_limited").eq("id", item.product_id).maybeSingle();
    if (!(product as { stock_limited?: boolean } | null)?.stock_limited) continue;
    const { data: ok } = await supabase.rpc("decrement_product_stock", { product_id_input: item.product_id, qty_input: item.quantity });
    if (!ok) oversoldNames.push(item.name);
  }

  // Payment already succeeded — we can't silently undo that — but in the
  // rare case two near-simultaneous payments both cleared for the last
  // unit(s) of a limited item, flag it clearly so staff see it on the
  // order and can call the customer, rather than the order silently
  // looking identical to any other paid order.
  if (oversoldNames.length > 0) {
    const { data: current } = await supabase.from("orders").select("notes").eq("id", orderId).maybeSingle();
    const existingNotes = (current as { notes?: string | null } | null)?.notes ?? "";
    const flag = `⚠ Stock conflict: ${oversoldNames.join(", ")} may be oversold — please verify before preparing.`;
    await supabase.from("orders").update({ notes: existingNotes ? `${existingNotes}\n${flag}` : flag }).eq("id", orderId);
  }
}

export async function markOrderPaymentFailed(orderId: string): Promise<void> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    const order = memoryOrders.get(orderId);
    // Stripe doesn't guarantee webhook delivery order, so a "failed" event
    // for an already-paid order (e.g. a retried intent that later
    // succeeded) must never downgrade it back to failed.
    if (order && order.paymentStatus !== "paid") order.paymentStatus = "failed";
    return;
  }
  const { data } = await supabase.from("orders").select("payment_status").eq("id", orderId).maybeSingle();
  const row = data as { payment_status?: string } | null;
  if (row?.payment_status === "paid") return;
  await supabase.from("orders").update({ payment_status: "failed" }).eq("id", orderId);
}

export async function updateOrderStatus(orderId: string, status: OrderStatus, changedBy = "admin"): Promise<void> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    const order = memoryOrders.get(orderId);
    if (!order) return;
    const previousStatus = order.status;
    order.status = status;
    // No live Realtime broadcast in memory-store mode (no Supabase to send
    // through), but the ready-email dedup rule still applies.
    if (status === "ready" && previousStatus !== "ready") await sendOrderReadyEmail(order);
    return;
  }

  const { data: existing } = await supabase.from("orders").select("status, payment_status").eq("id", orderId).maybeSingle();
  const existingRow = existing as { status?: string; payment_status?: string } | null;
  const previousStatus = existingRow?.status;

  // A *paid* order being cancelled after the fact (staff-initiated) should
  // give any limited-stock items it consumed back — this is the one case
  // where stock is released, distinct from failed/abandoned payments,
  // which never decremented anything in the first place.
  if (status === "cancelled" && existingRow?.payment_status === "paid") {
    const { data: itemsData } = await supabase.from("order_items").select("product_id, quantity").eq("order_id", orderId);
    const items = (itemsData ?? []) as { product_id: string | null; quantity: number }[];
    await Promise.all(
      items
        .filter((item): item is { product_id: string; quantity: number } => Boolean(item.product_id))
        .map((item) => supabase.rpc("increment_product_stock", { product_id_input: item.product_id, qty_input: item.quantity }))
    );
  }

  await supabase.from("orders").update({ status }).eq("id", orderId);
  await supabase.from("order_status_history").insert({ order_id: orderId, status, changed_by: changedBy });
  await broadcastOrderStatus(supabase, orderId, status);

  // Only on the transition *into* ready — re-saving the same status (a
  // retried admin action, or toggling away and back) never re-sends it.
  if (status === "ready" && previousStatus !== "ready") {
    const order = await loadOrderFromSupabase(supabase, orderId);
    if (order) await sendOrderReadyEmail(order);
  }
}

export async function hasProcessedWebhookEvent(eventId: string): Promise<boolean> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) return memoryWebhookEvents.has(eventId);
  const { data } = await supabase.from("webhook_events").select("id").eq("id", eventId).maybeSingle();
  return Boolean(data);
}

export async function recordWebhookEvent(eventId: string, type: string): Promise<void> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    memoryWebhookEvents.add(eventId);
    return;
  }
  await supabase.from("webhook_events").insert({ id: eventId, type });
}

export async function listOrders(params: { statuses?: OrderStatus[]; since?: string } = {}): Promise<OrderRecord[]> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    let orders = Array.from(memoryOrders.values());
    if (params.statuses) orders = orders.filter((o) => params.statuses!.includes(o.status));
    if (params.since) orders = orders.filter((o) => o.createdAt >= params.since!);
    return orders.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
  }

  let query = supabase.from("orders").select("*").order("created_at", { ascending: false });
  if (params.statuses) query = query.in("status", params.statuses);
  if (params.since) query = query.gte("created_at", params.since);
  const { data, error } = await query;
  if (error || !data) return [];

  const rows = data as OrderRow[];
  const orderIds = rows.map((r) => r.id);
  if (orderIds.length === 0) return [];

  const { data: itemsData } = await supabase.from("order_items").select("*").in("order_id", orderIds);
  const items = (itemsData ?? []) as OrderItemRow[];
  const itemIds = items.map((i) => i.id);

  const { data: modifiersData } = itemIds.length
    ? await supabase.from("order_item_modifiers").select("*").in("order_item_id", itemIds)
    : { data: [] };
  const modifiers = (modifiersData ?? []) as OrderItemModifierRow[];

  return rows.map((row) => mapRowToOrder(row, items.filter((i) => i.order_id === row.id), modifiers));
}
