import { Suspense } from "react";
import type { Metadata } from "next";
import { MenuBrowser } from "@/components/menu/MenuBrowser";
import { OpeningStatusBadge } from "@/components/home/OpeningStatusBadge";
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
      <div className="border-b border-char-200 bg-cream-50">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
          <p className="text-xs font-semibold uppercase tracking-widest text-fire-600">The Menu</p>
          <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
            <h1 className="font-display text-4xl font-semibold text-char-900 sm:text-5xl">Wood-fired &amp; made to order</h1>
            <OpeningStatusBadge business={business} weeklyHours={weeklyHours} specialHours={specialHours} />
          </div>
        </div>
      </div>

      <Suspense>
        <MenuBrowser categories={categories} products={products} modifierGroups={modifierGroups} />
      </Suspense>
    </>
  );
}
