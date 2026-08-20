import { Leaf, Sprout, Flame } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ProductImage } from "@/components/media/ProductImage";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Product } from "@/lib/types";

const DIETARY_ICON = {
  vegetarian: Leaf,
  vegan: Sprout,
  spicy: Flame,
  gluten_free: null,
} as const;

export function ProductCardContent({ product, className }: { product: Product; className?: string }) {
  return (
    <div className={cn("group flex h-full flex-col overflow-hidden rounded-2xl bg-cream-50 shadow-sm ring-1 ring-char-200/60 transition-all", "hover:-translate-y-0.5 hover:shadow-lg", className)}>
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-char-800">
        <ProductImage imageUrl={product.imageUrl} alt={product.name} className="transition-transform duration-500 group-hover:scale-[1.04]" />
        <div className="absolute left-3 top-3 flex flex-wrap gap-1.5">
          {product.isNew && <Badge variant="fire">New</Badge>}
          {product.featured && !product.isNew && <Badge variant="ember">Featured</Badge>}
          {product.popular && !product.featured && !product.isNew && <Badge variant="dark">Popular</Badge>}
        </div>
        {product.soldOut && (
          <div className="absolute inset-0 flex items-center justify-center bg-char-900/60 backdrop-blur-[1px]">
            <Badge variant="soldout" className="text-sm">Sold Out</Badge>
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-display text-lg uppercase leading-tight tracking-tight text-char-900">{product.name}</h3>
          <span className="shrink-0 font-display text-lg text-fire-600">{formatMoney(product.priceMinor)}</span>
        </div>
        {product.description && <p className="line-clamp-2 text-sm leading-snug text-char-500">{product.description}</p>}
        {product.dietary.length > 0 && (
          <div className="mt-auto flex flex-wrap items-center gap-2.5 pt-2 text-char-400">
            {product.dietary.map((tag) => {
              const Icon = DIETARY_ICON[tag];
              return (
                <span key={tag} className="flex items-center gap-1 text-xs font-medium capitalize">
                  {Icon && <Icon className="h-3.5 w-3.5" />}
                  {tag.replace("_", " ")}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
