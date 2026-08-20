"use server";

import { getOrderById } from "@/lib/data/orders";
import { getModifierGroups, getProducts } from "@/lib/data/menu";
import { buildReorderPreview, type ReorderPreview } from "@/lib/reorder";

/**
 * Same exposure as the order-confirmation page: the order id is an
 * unguessable UUID acting as the bearer token (no customer accounts exist
 * in this app), so this action requires no separate auth check.
 */
export async function previewReorderAction(orderId: string): Promise<{ preview: ReorderPreview } | { error: string }> {
  if (!orderId || typeof orderId !== "string") return { error: "Invalid order." };

  const order = await getOrderById(orderId);
  if (!order) return { error: "We couldn't find that order." };

  const [products, modifierGroups] = await Promise.all([getProducts(), getModifierGroups()]);
  const preview = buildReorderPreview(order, products, modifierGroups);

  if (!preview.anyAvailable) {
    return { error: "None of the items from that order are available right now." };
  }

  return { preview };
}
