"use client";

import { useEffect, useState, useTransition } from "react";
import { toast } from "sonner";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ProductImage } from "@/components/media/ProductImage";
import { ProductFormSheet } from "@/components/admin/ProductFormSheet";
import { deleteProductAction, toggleProductSoldOutAction } from "@/lib/actions/menu";
import { formatMoney } from "@/lib/format";
import type { Category, Product } from "@/lib/types";

export function MenuEditor({ categories, products }: { categories: Category[]; products: Product[] }) {
  const [items, setItems] = useState(products);
  const [editing, setEditing] = useState<Product | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [, startTransition] = useTransition();

  // Resyncs local (optimistic) state after router.refresh() re-fetches
  // `products` server-side — e.g. following a create/edit in the sheet.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setItems(products);
  }, [products]);

  function handleToggleSoldOut(product: Product, soldOut: boolean) {
    setItems((prev) => prev.map((p) => (p.id === product.id ? { ...p, soldOut } : p)));
    startTransition(async () => {
      const res = await toggleProductSoldOutAction(product.id, soldOut);
      if (res?.error) {
        toast.error(res.error);
        setItems((prev) => prev.map((p) => (p.id === product.id ? { ...p, soldOut: !soldOut } : p)));
      }
    });
  }

  function handleDelete(product: Product) {
    if (!confirm(`Delete "${product.name}"? This can't be undone.`)) return;
    startTransition(async () => {
      const res = await deleteProductAction(product.id);
      if (res?.error) toast.error(res.error);
      else {
        setItems((prev) => prev.filter((p) => p.id !== product.id));
        toast.success("Product deleted");
      }
    });
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl text-char-900">Menu</h1>
        <Button
          onClick={() => {
            setEditing(null);
            setSheetOpen(true);
          }}
        >
          <Plus className="h-4 w-4" /> Add Product
        </Button>
      </div>

      {categories.map((category) => {
        const categoryItems = items.filter((p) => p.categoryId === category.id).sort((a, b) => a.sortOrder - b.sortOrder);
        if (categoryItems.length === 0) return null;

        return (
          <section key={category.id} className="mt-8">
            <h2 className="font-display text-lg text-char-900">{category.name}</h2>
            <div className="mt-3 divide-y divide-char-200 rounded-2xl border border-char-200 bg-cream-50">
              {categoryItems.map((product) => (
                <div key={product.id} className="flex items-center gap-3 p-3 sm:gap-4 sm:p-4">
                  <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-xl bg-char-800">
                    <ProductImage imageUrl={product.imageUrl} alt={product.name} sizes="56px" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-char-900">{product.name}</p>
                    <p className="text-sm text-char-500">{formatMoney(product.priceMinor)}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 sm:gap-3">
                    <div className="flex items-center gap-2">
                      <Switch checked={!product.soldOut} onCheckedChange={(v) => handleToggleSoldOut(product, !v)} />
                      <span className="hidden text-xs font-semibold text-char-500 sm:inline">
                        {product.soldOut ? "Sold out" : "Available"}
                      </span>
                    </div>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => {
                        setEditing(product);
                        setSheetOpen(true);
                      }}
                      aria-label="Edit product"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => handleDelete(product)} aria-label="Delete product">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        );
      })}

      <ProductFormSheet product={editing} categories={categories} open={sheetOpen} onOpenChange={setSheetOpen} />
    </div>
  );
}
