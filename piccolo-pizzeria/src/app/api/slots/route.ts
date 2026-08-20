import { NextRequest, NextResponse } from "next/server";
import { getBusinessSettings, getSpecialHours, getWeeklyHours } from "@/lib/data/business";
import { getBookedCounts } from "@/lib/data/orders";
import { generateSlots } from "@/lib/slots";
import type { OrderMethod } from "@/lib/types";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const dateISO = searchParams.get("date");
  const method = searchParams.get("method") as OrderMethod | null;

  if (!dateISO || !/^\d{4}-\d{2}-\d{2}$/.test(dateISO) || (method !== "collection" && method !== "delivery")) {
    return NextResponse.json({ error: "Invalid date or method" }, { status: 400 });
  }

  const [business, weeklyHours, specialHours, bookedCounts] = await Promise.all([
    getBusinessSettings(),
    getWeeklyHours(),
    getSpecialHours(),
    getBookedCounts(dateISO, method),
  ]);

  const slots = generateSlots({ dateISO, method, weeklyHours, specialHours, business, bookedCounts });

  return NextResponse.json({ slots }, { headers: { "Cache-Control": "no-store" } });
}
