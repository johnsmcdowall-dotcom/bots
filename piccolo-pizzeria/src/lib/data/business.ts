import "server-only";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import {
  seedBusinessSettings,
  seedDeliveryZones,
  seedSpecialHours,
  seedWeeklyHours,
} from "@/lib/seed-data";
import { computeOpeningStatus } from "@/lib/opening-hours";
import type { BusinessSettings, DeliveryZone, SpecialHours, WeeklyHours } from "@/lib/types";
import type {
  BusinessSettingsRow,
  DeliveryZoneRow,
  OpeningHoursRow,
  SpecialHoursRow,
} from "@/lib/supabase/database.types";

export async function getBusinessSettings(): Promise<BusinessSettings> {
  try {
    const supabase = await getSupabaseServerClient();
    if (!supabase) return seedBusinessSettings;

    const { data, error } = await supabase.from("business_settings").select("*").eq("id", 1).maybeSingle();
    if (error || !data) return seedBusinessSettings;
    const row = data as BusinessSettingsRow;

    return {
      name: row.name,
      tagline: row.tagline,
      phone: row.phone,
      email: row.email,
      addressLine1: row.address_line1,
      addressLine2: row.address_line2 ?? undefined,
      city: row.city,
      postcode: row.postcode,
      latitude: row.latitude,
      longitude: row.longitude,
      instagramUrl: row.instagram_url ?? undefined,
      facebookUrl: row.facebook_url ?? undefined,
      tiktokUrl: row.tiktok_url ?? undefined,
      orderingPaused: row.ordering_paused,
      orderingPausedMessage: row.ordering_paused_message ?? undefined,
      asapOrdersEnabled: row.asap_orders_enabled,
      scheduledOrdersEnabled: row.scheduled_orders_enabled,
      deliveryEnabled: row.delivery_enabled,
      currentWaitMinutes: row.current_wait_minutes,
      minPrepMinutes: row.min_prep_minutes,
      maxAdvanceOrderDays: row.max_advance_order_days,
      slotIntervalMinutes: row.slot_interval_minutes,
      ordersPerSlot: row.orders_per_slot,
      deliveryOrdersPerSlot: row.delivery_orders_per_slot,
    };
  } catch {
    return seedBusinessSettings;
  }
}

export async function getWeeklyHours(): Promise<WeeklyHours> {
  try {
    const supabase = await getSupabaseServerClient();
    if (!supabase) return seedWeeklyHours;

    const { data, error } = await supabase.from("opening_hours").select("*");
    if (error || !data?.length) return seedWeeklyHours;
    const rows = data as OpeningHoursRow[];

    const hours: WeeklyHours = { ...seedWeeklyHours };
    for (const row of rows) {
      hours[row.day_of_week] = {
        isOpen: row.is_open,
        openTime: row.open_time.slice(0, 5),
        closeTime: row.close_time.slice(0, 5),
      };
    }
    return hours;
  } catch {
    return seedWeeklyHours;
  }
}

export async function getSpecialHours(): Promise<SpecialHours[]> {
  try {
    const supabase = await getSupabaseServerClient();
    if (!supabase) return seedSpecialHours;

    const { data, error } = await supabase
      .from("special_hours")
      .select("*")
      .gte("date", new Date().toISOString().slice(0, 10));
    if (error) return seedSpecialHours;
    const rows = (data ?? []) as SpecialHoursRow[];

    return rows.map((row) => ({
      id: row.id,
      date: row.date,
      label: row.label,
      isOpen: row.is_open,
      openTime: row.open_time?.slice(0, 5) ?? undefined,
      closeTime: row.close_time?.slice(0, 5) ?? undefined,
    }));
  } catch {
    return seedSpecialHours;
  }
}

export async function getDeliveryZones(): Promise<DeliveryZone[]> {
  try {
    const supabase = await getSupabaseServerClient();
    if (!supabase) return seedDeliveryZones;

    const { data, error } = await supabase.from("delivery_zones").select("*");
    if (error || !data?.length) return seedDeliveryZones;
    const rows = data as DeliveryZoneRow[];

    return rows.map((row) => ({
      id: row.id,
      postcodePrefixes: row.postcode_prefixes,
      feeMinor: row.fee_minor,
      minOrderMinor: row.min_order_minor,
      freeDeliveryThresholdMinor: row.free_delivery_threshold_minor ?? undefined,
      estimatedMinutes: row.estimated_minutes,
    }));
  } catch {
    return seedDeliveryZones;
  }
}

export async function getOpeningStatus(now: Date = new Date()) {
  const [business, weeklyHours, specialHours] = await Promise.all([
    getBusinessSettings(),
    getWeeklyHours(),
    getSpecialHours(),
  ]);
  return computeOpeningStatus(business, weeklyHours, specialHours, now);
}
