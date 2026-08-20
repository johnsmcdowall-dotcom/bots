import { MenuEditor } from "@/components/admin/MenuEditor";
import { getCategories, getProducts } from "@/lib/data/menu";

export default async function AdminMenuPage() {
  const [categories, products] = await Promise.all([getCategories(), getProducts()]);
  return <MenuEditor categories={categories} products={products} />;
}
