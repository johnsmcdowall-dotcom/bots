"use server";

import { revalidatePath } from "next/cache";
import { requireAdmin } from "@/lib/actions/admin-auth";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import type { SpecialHours, WeeklyHours } from "@/lib/types";

export async function updateWeeklyHoursAction(hours: WeeklyHours) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const rows = Object.entries(hours).map(([day, h]) => ({
    day_of_week: Number(day),
    is_open: h.isOpen,
    open_time: h.openTime,
    close_time: h.closeTime,
  }));

  const { error } = await supabase.from("opening_hours").upsert(rows, { onConflict: "day_of_week" });
  if (error) return { error: error.message };

  revalidatePath("/", "layout");
  revalidatePath("/admin/opening-hours");
  return { success: true };
}

export async function addSpecialHoursAction(entry: Omit<SpecialHours, "id">) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const { error } = await supabase.from("special_hours").insert({
    date: entry.date,
    label: entry.label,
    is_open: entry.isOpen,
    open_time: entry.openTime || null,
    close_time: entry.closeTime || null,
  });
  if (error) return { error: error.message };

  revalidatePath("/", "layout");
  revalidatePath("/admin/opening-hours");
  return { success: true };
}

export async function deleteSpecialHoursAction(id: string) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const { error } = await supabase.from("special_hours").delete().eq("id", id);
  if (error) return { error: error.message };

  revalidatePath("/", "layout");
  revalidatePath("/admin/opening-hours");
  return { success: true };
}
