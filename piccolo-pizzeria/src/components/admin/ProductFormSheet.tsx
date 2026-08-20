"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { upsertProductAction, type ProductFormInput } from "@/lib/actions/menu";
import type { Category, DietaryTag, Product } from "@/lib/types";

const DIETARY_OPTIONS: DietaryTag[] = ["vegetarian", "vegan", "spicy", "gluten_free"];

const EMPTY: ProductFormInput = {
  categoryId: "",
  slug: "",
  name: "",
  description: "",
  priceMinor: 0,
  imageUrl: "placeholder:pizzas:0",
  dietary: [],
  soldOut: false,
  featured: false,
  popular: false,
  isNew: false,
  sortOrder: 0,
};

export function ProductFormSheet({
  product,
  categories,
  open,
  onOpenChange,
}: {
  product: Product | null;
  categories: Category[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [form, setForm] = useState<ProductFormInput>(EMPTY);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  // Reseeds the form whenever a different product is targeted or the sheet
  // reopens. Stays mounted across open/close so Radix can animate, which
  // rules out a `key` remount instead.
  useEffect(() => {
    if (product) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({
        id: product.id,
        categoryId: product.categoryId,
        slug: product.slug,
        name: product.name,
        description: product.description,
        priceMinor: product.priceMinor,
        imageUrl: product.imageUrl,
        dietary: product.dietary,
        soldOut: product.soldOut,
        featured: product.featured,
        popular: product.popular,
        isNew: product.isNew,
        sortOrder: product.sortOrder,
      });
    } else {
      setForm({ ...EMPTY, categoryId: categories[0]?.id ?? "" });
    }
  }, [product, categories, open]);

  function set<K extends keyof ProductFormInput>(key: K, value: ProductFormInput[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function toggleDietary(tag: DietaryTag) {
    set("dietary", form.dietary.includes(tag) ? form.dietary.filter((d) => d !== tag) : [...form.dietary, tag]);
  }

  function save() {
    if (!form.name.trim() || !form.slug.trim() || !form.categoryId) {
      toast.error("Name, slug and category are required");
      return;
    }
    startTransition(async () => {
      const res = await upsertProductAction(form);
      if (res?.error) toast.error(res.error);
      else {
        toast.success(product ? "Product updated" : "Product created");
        onOpenChange(false);
        router.refresh();
      }
    });
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{product ? "Edit Product" : "Add Product"}</SheetTitle>
        </SheetHeader>
        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4 sm:px-6">
          <div>
            <Label htmlFor="p-name">Name</Label>
            <Input id="p-name" className="mt-1.5" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="p-slug">Slug</Label>
            <Input id="p-slug" className="mt-1.5" value={form.slug} onChange={(e) => set("slug", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="p-desc">Description</Label>
            <Textarea id="p-desc" className="mt-1.5" rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="p-price">Price (£)</Label>
              <Input
                id="p-price"
                type="number"
                min={0}
                step={0.01}
                className="mt-1.5"
                value={(form.priceMinor / 100).toFixed(2)}
                onChange={(e) => set("priceMinor", Math.round(Number(e.target.value) * 100))}
              />
            </div>
            <div>
              <Label htmlFor="p-sort">Sort order</Label>
              <Input id="p-sort" type="number" className="mt-1.5" value={form.sortOrder} onChange={(e) => set("sortOrder", Number(e.target.value))} />
            </div>
          </div>
          <div>
            <Label>Category</Label>
            <Select value={form.categoryId} onValueChange={(v) => set("categoryId", v)}>
              <SelectTrigger className="mt-1.5">
                <SelectValue placeholder="Choose category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="p-image">Image URL</Label>
            <Input id="p-image" className="mt-1.5" value={form.imageUrl} onChange={(e) => set("imageUrl", e.target.value)} />
            <p className="mt-1 text-xs text-char-400">
              Use <code>placeholder:category:0</code> for placeholder art, or a real photo path/URL.
            </p>
          </div>

          <div>
            <Label>Dietary</Label>
            <div className="mt-2 flex flex-wrap gap-3">
              {DIETARY_OPTIONS.map((tag) => (
                <label key={tag} className="flex items-center gap-1.5 text-sm capitalize text-char-700">
                  <Checkbox checked={form.dietary.includes(tag)} onCheckedChange={() => toggleDietary(tag)} />
                  {tag.replace("_", " ")}
                </label>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-1.5 text-sm text-char-700">
              <Checkbox checked={form.soldOut} onCheckedChange={(v) => set("soldOut", Boolean(v))} /> Sold out
            </label>
            <label className="flex items-center gap-1.5 text-sm text-char-700">
              <Checkbox checked={form.featured} onCheckedChange={(v) => set("featured", Boolean(v))} /> Featured
            </label>
            <label className="flex items-center gap-1.5 text-sm text-char-700">
              <Checkbox checked={form.popular} onCheckedChange={(v) => set("popular", Boolean(v))} /> Popular
            </label>
            <label className="flex items-center gap-1.5 text-sm text-char-700">
              <Checkbox checked={form.isNew} onCheckedChange={(v) => set("isNew", Boolean(v))} /> New
            </label>
          </div>
        </div>
        <div className="border-t border-char-200 p-4 sm:px-6">
          <Button size="lg" className="w-full" disabled={isPending} onClick={save}>
            {isPending ? "Saving…" : product ? "Save Changes" : "Create Product"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
