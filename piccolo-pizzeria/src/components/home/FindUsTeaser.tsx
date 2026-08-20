import Link from "next/link";
import { MapPin, Clock, Phone, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TricolorRule } from "@/components/brand/TricolorRule";
import { DAY_LABELS_SHORT, formatHours } from "@/lib/format";
import type { BusinessSettings, WeeklyHours } from "@/lib/types";

export function FindUsTeaser({ business, weeklyHours }: { business: BusinessSettings; weeklyHours: WeeklyHours }) {
  const today = new Date().getDay();
  const mapsQuery = encodeURIComponent(`${business.addressLine1}, ${business.city}, ${business.postcode}`);

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
      <div className="texture-grain grid gap-8 rounded-3xl bg-char-900 p-6 text-cream-50 sm:p-10 lg:grid-cols-2 lg:gap-16 lg:p-14">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-fire-400">Find Us</p>
          <h2 className="mt-2 font-display text-4xl uppercase tracking-tight sm:text-5xl">{business.city}</h2>
          <TricolorRule className="mt-4" />

          <div className="mt-6 space-y-4 text-cream-100/85">
            <p className="flex gap-3">
              <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-fire-400" />
              <span>
                {business.addressLine1}, {business.city}, {business.postcode}
              </span>
            </p>
            <p className="flex gap-3">
              <Phone className="mt-0.5 h-5 w-5 shrink-0 text-fire-400" />
              <a href={`tel:${business.phone.replace(/\s+/g, "")}`} className="hover:text-cream-50">
                {business.phone}
              </a>
            </p>
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg" variant="accent">
              <a href={`https://www.google.com/maps/search/?api=1&query=${mapsQuery}`} target="_blank" rel="noreferrer">
                Get Directions <ArrowRight className="h-4 w-4" />
              </a>
            </Button>
            <Button asChild size="lg" variant="light">
              <Link href="/contact">Contact Us</Link>
            </Button>
          </div>
        </div>

        <div className="rounded-2xl bg-cream-50/5 p-6">
          <p className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-cream-100/60">
            <Clock className="h-4 w-4" /> Opening Hours
          </p>
          <ul className="space-y-2 text-sm">
            {DAY_LABELS_SHORT.map((label, idx) => {
              const hours = weeklyHours[idx];
              return (
                <li key={label} className={`flex justify-between border-b border-cream-100/10 pb-2 ${idx === today ? "font-semibold text-cream-50" : "text-cream-100/75"}`}>
                  <span>{label}</span>
                  <span>{hours?.isOpen ? `${formatHours(hours.openTime)} – ${formatHours(hours.closeTime)}` : "Closed"}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}
