import "server-only";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { getSupabaseAdminClient } from "@/lib/supabase/admin";
import { memoryOrders, memoryWebhookEvents } from "@/lib/data/memory-store";
import type {
  OrderItemRecord,
  OrderMethod,
  OrderRecord,
  OrderStatus,
  OrderTiming,
} from "@/lib/types";
import type { OrderItemModifierRow, OrderItemRow, OrderRow } from "@/lib/supabase/database.types";

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
          product_id: null,
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
        .map((m) => ({ groupName: m.group_name, optionName: m.option_name, priceMinor: m.price_minor })),
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
  const { data } = await supabase.from("orders").select("payment_status, promo_code").eq("id", orderId).maybeSingle();
  const row = data as { payment_status?: string; promo_code?: string | null } | null;
  if (row?.payment_status === "paid") return;

  await supabase.from("orders").update({ payment_status: "paid", status: "received" }).eq("id", orderId);
  await supabase.from("order_status_history").insert({ order_id: orderId, status: "received", changed_by: "stripe_webhook" });

  if (row?.promo_code) {
    await supabase.rpc("increment_promo_usage", { promo_code_input: row.promo_code });
  }
}

export async function markOrderPaymentFailed(orderId: string): Promise<void> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    const order = memoryOrders.get(orderId);
    if (order) order.paymentStatus = "failed";
    return;
  }
  await supabase.from("orders").update({ payment_status: "failed" }).eq("id", orderId);
}

export async function updateOrderStatus(orderId: string, status: OrderStatus, changedBy = "admin"): Promise<void> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) {
    const order = memoryOrders.get(orderId);
    if (order) order.status = status;
    return;
  }
  await supabase.from("orders").update({ status }).eq("id", orderId);
  await supabase.from("order_status_history").insert({ order_id: orderId, status, changed_by: changedBy });
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
