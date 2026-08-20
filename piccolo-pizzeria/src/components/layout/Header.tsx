import Link from "next/link";
import { ShoppingBag } from "lucide-react";
import { LogoWordmark } from "@/components/brand/LogoWordmark";
import { OpeningStatusBadge } from "@/components/home/OpeningStatusBadge";
import { Button } from "@/components/ui/button";
import { MobileNav } from "@/components/layout/MobileNav";
import { HeaderBasketButton } from "@/components/basket/HeaderBasketButton";
import type { BusinessSettings, SpecialHours, WeeklyHours } from "@/lib/types";

const LINKS = [
  { href: "/menu", label: "Menu" },
  { href: "/our-story", label: "Our Story" },
  { href: "/contact", label: "Find Us" },
];

export function Header({
  business,
  weeklyHours,
  specialHours,
}: {
  business: BusinessSettings;
  weeklyHours: WeeklyHours;
  specialHours: SpecialHours[];
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-cream-100/10 bg-char-900">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:h-20 sm:px-6 lg:px-8">
        <Link href="/" className="flex shrink-0 items-center gap-2" aria-label="Piccolo Pizzeria — home">
          <LogoWordmark className="h-14 sm:h-16 lg:h-[4.5rem]" />
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm font-semibold text-cream-100/80 transition-colors hover:text-fire-400"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <OpeningStatusBadge
            business={business}
            weeklyHours={weeklyHours}
            specialHours={specialHours}
            className="hidden bg-cream-50/10 text-cream-50 lg:inline-flex"
            compact={false}
          />
          <HeaderBasketButton />
          <Button asChild size="md" variant="accent" className="hidden md:inline-flex">
            <Link href="/order">
              <ShoppingBag className="h-4 w-4" />
              Order Now
            </Link>
          </Button>
          <MobileNav business={business} />
        </div>
      </div>
    </header>
  );
}
