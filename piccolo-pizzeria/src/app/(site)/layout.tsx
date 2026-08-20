import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { StickyBasketBar } from "@/components/basket/StickyBasketBar";
import { getBusinessSettings, getSpecialHours, getWeeklyHours } from "@/lib/data/business";

export default async function SiteLayout({ children }: { children: React.ReactNode }) {
  const [business, weeklyHours, specialHours] = await Promise.all([
    getBusinessSettings(),
    getWeeklyHours(),
    getSpecialHours(),
  ]);

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-full focus:bg-char-900 focus:px-4 focus:py-2 focus:text-cream-50"
      >
        Skip to content
      </a>
      <Header business={business} weeklyHours={weeklyHours} specialHours={specialHours} />
      <main id="main-content" className="flex-1 pb-24 md:pb-0">
        {children}
      </main>
      <Footer business={business} weeklyHours={weeklyHours} />
      <StickyBasketBar />
    </>
  );
}
