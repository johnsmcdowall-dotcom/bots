import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { OpeningStatusBadge } from "@/components/home/OpeningStatusBadge";
import type { BusinessSettings, SpecialHours, WeeklyHours } from "@/lib/types";

export function Hero({
  business,
  weeklyHours,
  specialHours,
}: {
  business: BusinessSettings;
  weeklyHours: WeeklyHours;
  specialHours: SpecialHours[];
}) {
  return (
    <section className="relative overflow-hidden bg-char-900">
      <Image
        src="/images/real/oven-flame-1.jpg"
        alt=""
        fill
        priority
        className="object-cover opacity-80"
        aria-hidden
      />
      <div className="absolute inset-0 bg-gradient-to-t from-char-900 via-char-900/40 to-char-900/10" />

      <div className="relative mx-auto flex min-h-[86dvh] max-w-7xl flex-col justify-end px-4 pb-14 pt-28 sm:px-6 sm:pb-20 lg:px-8 lg:pb-28">
        <OpeningStatusBadge
          business={business}
          weeklyHours={weeklyHours}
          specialHours={specialHours}
          className="mb-6 w-fit bg-cream-50/10 text-cream-50 backdrop-blur-sm"
        />

        <h1 className="max-w-2xl text-balance font-display text-5xl font-semibold leading-[1.05] text-cream-50 sm:text-6xl lg:text-7xl animate-fade-up">
          Wood-fired.
          <br />
          Hand-stretched.
          <br />
          <span className="text-fire-400">Piccolo.</span>
        </h1>

        <p className="mt-6 max-w-md text-balance text-lg leading-relaxed text-cream-100/80 animate-fade-up [animation-delay:100ms]">
          Our own wood-fired oven, hand-stretched dough and a menu that doesn&apos;t cut corners.
          Order ahead and collect straight from the trailer — no queuing required.
        </p>

        <div className="mt-9 flex flex-col gap-3 sm:flex-row animate-fade-up [animation-delay:200ms]">
          <Button asChild size="xl">
            <Link href="/order">
              Order Now
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="xl" variant="light">
            <Link href="/menu">View Menu</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
