"use server";

import { revalidatePath } from "next/cache";
import { requireStaff } from "@/lib/actions/admin-auth";
import { updateOrderStatus } from "@/lib/data/orders";
import type { OrderStatus } from "@/lib/types";

const VALID_STATUSES: OrderStatus[] = ["received", "accepted", "preparing", "ready", "completed", "cancelled"];

export async function updateOrderStatusAction(orderId: string, status: OrderStatus) {
  const profile = await requireStaff();
  if (!VALID_STATUSES.includes(status)) {
    return { error: "Invalid status" };
  }

  await updateOrderStatus(orderId, status, profile.email);
  revalidatePath("/admin/orders");
  revalidatePath("/admin");
  return { success: true };
}
