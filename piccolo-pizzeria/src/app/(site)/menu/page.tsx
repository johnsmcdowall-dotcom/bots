import { Suspense } from "react";
import type { Metadata } from "next";
import { MenuBrowser } from "@/components/menu/MenuBrowser";
import { OpeningStatusBadge } from "@/components/home/OpeningStatusBadge";
import { TricolorRule } from "@/components/brand/TricolorRule";
import { getMenu } from "@/lib/data/menu";
import { getBusinessSettings, getSpecialHours, getWeeklyHours } from "@/lib/data/business";

export const metadata: Metadata = {
  title: "Menu",
  description: "Wood-fired pizzas, pizza sandwiches and specials — order online for collection from Piccolo Pizzeria.",
};

export default async function MenuPage() {
  const [{ categories, products, modifierGroups }, business, weeklyHours, specialHours] = await Promise.all([
    getMenu(),
    getBusinessSettings(),
    getWeeklyHours(),
    getSpecialHours(),
  ]);

  return (
    <>
      <div className="texture-grain border-b border-cream-100/10 bg-char-900">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
          <p className="text-xs font-semibold uppercase tracking-widest text-fire-400">The Menu</p>
          <TricolorRule className="mt-3" />
          <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
            <h1 className="font-display text-5xl uppercase tracking-tight text-cream-50 sm:text-6xl">
              Wood-Fired &amp; Made to Order
            </h1>
            <OpeningStatusBadge
              business={business}
              weeklyHours={weeklyHours}
              specialHours={specialHours}
              className="bg-cream-50/10 text-cream-50"
            />
          </div>
        </div>
      </div>

      <Suspense>
        <MenuBrowser categories={categories} products={products} modifierGroups={modifierGroups} />
      </Suspense>
    </>
  );
}
