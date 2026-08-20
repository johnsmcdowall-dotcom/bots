"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { ProductCardContent } from "@/components/menu/ProductCardContent";
import { ProductModal } from "@/components/menu/ProductModal";
import { CategoryNav } from "@/components/menu/CategoryNav";
import type { Category, ModifierGroup, Product } from "@/lib/types";

export function MenuBrowser({
  categories,
  products,
  modifierGroups,
}: {
  categories: Category[];
  products: Product[];
  modifierGroups: ModifierGroup[];
}) {
  const [selected, setSelected] = useState<Product | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Opens the modal for a `?item=slug` deep link (e.g. from the homepage's
  // featured section) — a one-time sync from the URL on load/navigation.
  useEffect(() => {
    const slug = searchParams.get("item");
    if (!slug) return;
    const product = products.find((p) => p.slug === slug);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (product) setSelected(product);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function closeModal() {
    setSelected(null);
    if (searchParams.get("item")) {
      router.replace(pathname, { scroll: false });
    }
  }

  return (
    <>
      <CategoryNav categories={categories} />

      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        {categories.map((category) => {
          const items = products
            .filter((p) => p.categoryId === category.id)
            .sort((a, b) => a.sortOrder - b.sortOrder);
          if (items.length === 0) return null;

          return (
            <section key={category.id} id={`category-${category.slug}`} className="scroll-mt-36 py-8 first:pt-0">
              <h2 className="font-display text-2xl font-semibold text-char-900 sm:text-3xl">{category.name}</h2>
              {category.description && <p className="mt-1 text-char-500">{category.description}</p>}

              <div className="mt-6 grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-3">
                {items.map((product) => (
                  <button
                    key={product.id}
                    onClick={() => setSelected(product)}
                    className="block text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fire-500 focus-visible:ring-offset-2 focus-visible:ring-offset-cream-100 rounded-2xl"
                    aria-haspopup="dialog"
                  >
                    <ProductCardContent product={product} />
                  </button>
                ))}
              </div>
            </section>
          );
        })}
      </div>

      <ProductModal product={selected} modifierGroups={modifierGroups} onClose={closeModal} />
    </>
  );
}
