import "server-only";
import { getSupabaseAdminClient } from "@/lib/supabase/admin";

/**
 * 1 point per whole pound spent — simple and easy to change later. This is
 * the only "policy" this stage defines; there is deliberately no redemption
 * logic, no points balance anywhere a customer or even staff can see it.
 * Architecture only, per the brief.
 */
export function pointsForOrder(totalMinor: number): number {
  return Math.floor(totalMinor / 100);
}

/**
 * Records a loyalty ledger entry for a paid order via the atomic
 * award_loyalty_points RPC (see 0008_loyalty.sql) — never a read-then-write
 * balance update from application code. No-ops when Supabase isn't
 * configured (no loyalty tables exist in the memory-store fallback) or the
 * order earned zero points.
 */
export async function awardLoyaltyPoints(input: {
  customerEmail: string;
  customerPhone: string;
  orderId: string;
  orderNumber: string;
  totalMinor: number;
}): Promise<void> {
  const supabase = getSupabaseAdminClient();
  if (!supabase) return;

  const points = pointsForOrder(input.totalMinor);
  if (points <= 0) return;

  await supabase.rpc("award_loyalty_points", {
    customer_email_input: input.customerEmail,
    customer_phone_input: input.customerPhone,
    order_id_input: input.orderId,
    points_input: points,
    description_input: `Order #${input.orderNumber}`,
  });
}
