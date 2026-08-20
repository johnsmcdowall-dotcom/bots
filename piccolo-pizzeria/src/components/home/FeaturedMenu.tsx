import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { ProductCardContent } from "@/components/menu/ProductCardContent";
import type { Product } from "@/lib/types";

export function FeaturedMenu({ products }: { products: Product[] }) {
  const featured = products.filter((p) => p.featured || p.popular).slice(0, 4);
  if (featured.length === 0) return null;

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-fire-600">From the oven</p>
          <h2 className="mt-2 font-display text-4xl uppercase tracking-tight text-char-900 sm:text-5xl">Crowd Favourites</h2>
        </div>
        <Link href="/menu" className="hidden shrink-0 items-center gap-1.5 text-sm font-semibold text-char-700 hover:text-fire-600 sm:flex">
          Full menu <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
        {featured.map((product) => (
          <Link key={product.id} href={`/menu?item=${product.slug}`} className="block">
            <ProductCardContent product={product} />
          </Link>
        ))}
      </div>

      <Link href="/menu" className="mt-8 flex items-center justify-center gap-1.5 text-sm font-semibold text-char-700 hover:text-fire-600 sm:hidden">
        Full menu <ArrowRight className="h-4 w-4" />
      </Link>
    </section>
  );
}
