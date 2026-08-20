import { NextResponse } from "next/server";
import { getCurrentProfile } from "@/lib/data/auth";
import { listOrders } from "@/lib/data/orders";

/** Used by the live order board to refresh after a Realtime change event. */
export async function GET() {
  const profile = await getCurrentProfile();
  if (!profile) {
    return NextResponse.json({ error: "Not authorized" }, { status: 401 });
  }

  const orders = await listOrders({});
  return NextResponse.json({ orders }, { headers: { "Cache-Control": "no-store" } });
}
