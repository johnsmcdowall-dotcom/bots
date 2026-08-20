"use server";

import { revalidatePath } from "next/cache";
import { requireAdmin } from "@/lib/actions/admin-auth";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import type { BusinessSettings } from "@/lib/types";

export async function updateBusinessSettingsAction(input: Partial<BusinessSettings>) {
  await requireAdmin();

  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const patch: Record<string, unknown> = {};
  if (input.name !== undefined) patch.name = input.name;
  if (input.tagline !== undefined) patch.tagline = input.tagline;
  if (input.phone !== undefined) patch.phone = input.phone;
  if (input.email !== undefined) patch.email = input.email;
  if (input.addressLine1 !== undefined) patch.address_line1 = input.addressLine1;
  if (input.addressLine2 !== undefined) patch.address_line2 = input.addressLine2 || null;
  if (input.city !== undefined) patch.city = input.city;
  if (input.postcode !== undefined) patch.postcode = input.postcode;
  if (input.instagramUrl !== undefined) patch.instagram_url = input.instagramUrl || null;
  if (input.facebookUrl !== undefined) patch.facebook_url = input.facebookUrl || null;
  if (input.tiktokUrl !== undefined) patch.tiktok_url = input.tiktokUrl || null;
  if (input.orderingPaused !== undefined) patch.ordering_paused = input.orderingPaused;
  if (input.orderingPausedMessage !== undefined) patch.ordering_paused_message = input.orderingPausedMessage || null;
  if (input.asapOrdersEnabled !== undefined) patch.asap_orders_enabled = input.asapOrdersEnabled;
  if (input.scheduledOrdersEnabled !== undefined) patch.scheduled_orders_enabled = input.scheduledOrdersEnabled;
  if (input.deliveryEnabled !== undefined) patch.delivery_enabled = input.deliveryEnabled;
  if (input.currentWaitMinutes !== undefined) patch.current_wait_minutes = input.currentWaitMinutes;
  if (input.minPrepMinutes !== undefined) patch.min_prep_minutes = input.minPrepMinutes;
  if (input.maxAdvanceOrderDays !== undefined) patch.max_advance_order_days = input.maxAdvanceOrderDays;
  if (input.slotIntervalMinutes !== undefined) patch.slot_interval_minutes = input.slotIntervalMinutes;
  if (input.ordersPerSlot !== undefined) patch.orders_per_slot = input.ordersPerSlot;
  if (input.deliveryOrdersPerSlot !== undefined) patch.delivery_orders_per_slot = input.deliveryOrdersPerSlot;

  const { error } = await supabase.from("business_settings").update(patch).eq("id", 1);
  if (error) return { error: error.message };

  revalidatePath("/", "layout");
  revalidatePath("/admin/settings");
  revalidatePath("/admin/orders");
  return { success: true };
}
