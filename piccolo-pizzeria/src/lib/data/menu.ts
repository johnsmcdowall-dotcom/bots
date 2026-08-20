import "server-only";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { getSupabaseAdminClient } from "@/lib/supabase/admin";
import { seedCategories, seedModifierGroups, seedProducts, seedPromoCodes } from "@/lib/seed-data";
import type { Category, ModifierGroup, Product, PromoCode } from "@/lib/types";
import type {
  CategoryRow,
  ModifierGroupRow,
  ModifierRow,
  ProductModifierGroupRow,
  ProductRow,
  PromoCodeRow,
} from "@/lib/supabase/database.types";

export async function getCategories(): Promise<Category[]> {
  try {
    const supabase = await getSupabaseServerClient();
    if (!supabase) return seedCategories;

    const { data, error } = await supabase.from("categories").select("*").order("sort_order");
    if (error || !data?.length) return seedCategories;
    const rows = data as CategoryRow[];

    return rows.map((row) => ({
      id: row.id,
      slug: row.slug,
      name: row.name,
      description: row.description ?? undefined,
      sortOrder: row.sort_order,
    }));
  } catch {
    return seedCategories;
  }
}

export async function getModifierGroups(): Promise<ModifierGroup[]> {
  try {
    const supabase = await getSupabaseServerClient();
    if (!supabase) return seedModifierGroups;

    const [{ data: groupsData, error: groupsError }, { data: optionsData, error: optionsError }] = await Promise.all([
      supabase.from("modifier_groups").select("*").order("sort_order"),
      supabase.from("modifiers").select("*").order("sort_order"),
    ]);
    if (groupsError || optionsError || !groupsData?.length) return seedModifierGroups;
    const groups = groupsData as ModifierGroupRow[];
    const options = (optionsData ?? []) as ModifierRow[];

    return groups.map((group) => ({
      id: group.id,
      name: group.name,
      description: group.description ?? undefined,
      required: group.required,
      minSelect: group.min_select,
      maxSelect: group.max_select,
      options: options
        .filter((o) => o.group_id === group.id)
        .map((o) => ({
          id: o.id,
          name: o.name,
          priceMinor: o.price_minor,
          soldOut: o.sold_out,
          isDefault: o.is_default,
        })),
    }));
  } catch {
    return seedModifierGroups;
  }
}

export async function getProducts(): Promise<Product[]> {
  try {
    const supabase = await getSupabaseServerClient();
    if (!supabase) return seedProducts;

    const [{ data: productsData, error }, { data: linksData }] = await Promise.all([
      supabase.from("products").select("*").order("sort_order"),
      supabase.from("product_modifier_groups").select("*"),
    ]);
    if (error || !productsData?.length) return seedProducts;
    const products = productsData as ProductRow[];
    const links = (linksData ?? []) as ProductModifierGroupRow[];

    return products.map((row) => ({
      id: row.id,
      categoryId: row.category_id,
      slug: row.slug,
      name: row.name,
      description: row.description ?? "",
      priceMinor: row.price_minor,
      imageUrl: row.image_url ?? "",
      dietary: (row.dietary ?? []) as Product["dietary"],
      allergens: row.allergens ?? [],
      soldOut: row.sold_out,
      featured: row.featured,
      popular: row.popular,
      isNew: row.is_new,
      sortOrder: row.sort_order,
      modifierGroupIds: links.filter((l) => l.product_id === row.id).map((l) => l.modifier_group_id),
    }));
  } catch {
    return seedProducts;
  }
}

export async function getMenu() {
  const [categories, products, modifierGroups] = await Promise.all([
    getCategories(),
    getProducts(),
    getModifierGroups(),
  ]);
  return { categories, products, modifierGroups };
}

export async function getPromoCodes(): Promise<PromoCode[]> {
  try {
    // Admin client: promo_codes has no public RLS policy at all, so
    // validating a code during checkout (or listing them in /admin) must go
    // through the service role rather than the anon-key server client.
    const supabase = getSupabaseAdminClient();
    if (!supabase) return seedPromoCodes;

    const { data, error } = await supabase.from("promo_codes").select("*").order("created_at", { ascending: false });
    if (error) return seedPromoCodes;
    const rows = (data ?? []) as PromoCodeRow[];

    return rows.map((row) => ({
      id: row.id,
      code: row.code,
      type: row.type,
      value: row.value,
      minBasketMinor: row.min_basket_minor,
      startsAt: row.starts_at ?? undefined,
      endsAt: row.ends_at ?? undefined,
      usageLimit: row.usage_limit ?? undefined,
      timesUsed: row.times_used,
      active: row.active,
    }));
  } catch {
    return seedPromoCodes;
  }
}
