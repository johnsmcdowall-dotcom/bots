"use server";

import { revalidatePath } from "next/cache";
import { requireAdmin } from "@/lib/actions/admin-auth";
import { getSupabaseServerClient } from "@/lib/supabase/server";

function revalidateUpsells() {
  revalidatePath("/admin/upsells");
  revalidatePath("/order");
}

export async function createUpsellRuleAction(input: {
  triggerType: "product" | "category";
  triggerId: string;
  suggestedProductId: string;
}) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  if (!input.triggerId || !input.suggestedProductId) return { error: "Choose a trigger and a suggested product" };
  if (input.triggerType === "product" && input.triggerId === input.suggestedProductId) {
    return { error: "A product can't upsell itself" };
  }

  const { error } = await supabase.from("upsell_rules").insert({
    trigger_type: input.triggerType,
    trigger_product_id: input.triggerType === "product" ? input.triggerId : null,
    trigger_category_id: input.triggerType === "category" ? input.triggerId : null,
    suggested_product_id: input.suggestedProductId,
  });
  if (error) return { error: error.message };

  revalidateUpsells();
  return { success: true };
}

export async function deleteUpsellRuleAction(ruleId: string) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const { error } = await supabase.from("upsell_rules").delete().eq("id", ruleId);
  if (error) return { error: error.message };

  revalidateUpsells();
  return { success: true };
}
