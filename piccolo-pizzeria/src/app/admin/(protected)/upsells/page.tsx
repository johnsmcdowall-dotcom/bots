import { UpsellEditor } from "@/components/admin/UpsellEditor";
import { getCategories, getProducts, getUpsellRules } from "@/lib/data/menu";

export default async function AdminUpsellsPage() {
  const [rules, categories, products] = await Promise.all([getUpsellRules(), getCategories(), getProducts()]);
  return <UpsellEditor rules={rules} categories={categories} products={products} />;
}
