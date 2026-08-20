"use server";

import { revalidatePath } from "next/cache";
import { requireAdmin } from "@/lib/actions/admin-auth";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import type { DietaryTag } from "@/lib/types";

function revalidateMenu() {
  revalidatePath("/", "layout");
  revalidatePath("/admin/menu");
}

export async function toggleProductSoldOutAction(productId: string, soldOut: boolean) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const { error } = await supabase.from("products").update({ sold_out: soldOut }).eq("id", productId);
  if (error) return { error: error.message };

  revalidateMenu();
  return { success: true };
}

export async function toggleModifierSoldOutAction(modifierId: string, soldOut: boolean) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const { error } = await supabase.from("modifiers").update({ sold_out: soldOut }).eq("id", modifierId);
  if (error) return { error: error.message };

  revalidateMenu();
  return { success: true };
}

export interface ProductFormInput {
  id?: string;
  categoryId: string;
  slug: string;
  name: string;
  description: string;
  priceMinor: number;
  imageUrl: string;
  dietary: DietaryTag[];
  soldOut: boolean;
  featured: boolean;
  popular: boolean;
  isNew: boolean;
  sortOrder: number;
}

export async function upsertProductAction(input: ProductFormInput) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const row = {
    category_id: input.categoryId,
    slug: input.slug,
    name: input.name,
    description: input.description,
    price_minor: input.priceMinor,
    image_url: input.imageUrl,
    dietary: input.dietary,
    sold_out: input.soldOut,
    featured: input.featured,
    popular: input.popular,
    is_new: input.isNew,
    sort_order: input.sortOrder,
  };

  const { error } = input.id
    ? await supabase.from("products").update(row).eq("id", input.id)
    : await supabase.from("products").insert(row);

  if (error) return { error: error.message };

  revalidateMenu();
  return { success: true };
}

export async function deleteProductAction(productId: string) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const { error } = await supabase.from("products").delete().eq("id", productId);
  if (error) return { error: error.message };

  revalidateMenu();
  return { success: true };
}

export async function upsertCategoryAction(input: { id?: string; slug: string; name: string; description?: string; sortOrder: number }) {
  await requireAdmin();
  const supabase = await getSupabaseServerClient();
  if (!supabase) return { error: "Supabase is not configured" };

  const row = { slug: input.slug, name: input.name, description: input.description || null, sort_order: input.sortOrder };

  const { error } = input.id
    ? await supabase.from("categories").update(row).eq("id", input.id)
    : await supabase.from("categories").insert(row);

  if (error) return { error: error.message };

  revalidateMenu();
  return { success: true };
}
