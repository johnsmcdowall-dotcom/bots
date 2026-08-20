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
    <header className="sticky top-0 z-30 border-b border-char-200/70 bg-cream-100/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:h-20 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2" aria-label="Piccolo Pizzeria — home">
          <LogoWordmark tone="dark" />
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm font-semibold text-char-700 transition-colors hover:text-fire-600"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <OpeningStatusBadge business={business} weeklyHours={weeklyHours} specialHours={specialHours} className="hidden lg:inline-flex" compact={false} />
          <HeaderBasketButton />
          <Button asChild size="md" className="hidden md:inline-flex">
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
