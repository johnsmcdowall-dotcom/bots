import Link from "next/link";
import { MapPin, Phone, Mail } from "lucide-react";
import { InstagramIcon, FacebookIcon } from "@/components/icons/SocialIcons";
import { LogoMark } from "@/components/brand/LogoMark";
import { TricolorRule } from "@/components/brand/TricolorRule";
import { DAY_LABELS_FULL, formatHours } from "@/lib/format";
import type { BusinessSettings, WeeklyHours } from "@/lib/types";

export function Footer({ business, weeklyHours }: { business: BusinessSettings; weeklyHours: WeeklyHours }) {
  const today = new Date().getDay();

  return (
    <footer className="texture-grain border-t border-cream-100/10 bg-char-900 text-cream-100">
      <div className="mx-auto grid max-w-7xl grid-cols-2 gap-x-6 gap-y-10 px-4 py-14 sm:px-6 md:grid-cols-4 lg:px-8">
        <div className="col-span-2 md:col-span-1">
          <div className="w-20">
            <LogoMark />
          </div>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-cream-100/70">{business.tagline}</p>
          <TricolorRule className="mt-5" />
          <div className="mt-5 flex items-center gap-4">
            {business.instagramUrl && (
              <a href={business.instagramUrl} target="_blank" rel="noreferrer" aria-label="Instagram" className="text-cream-100/70 hover:text-cream-50">
                <InstagramIcon className="h-5 w-5" />
              </a>
            )}
            {business.facebookUrl && (
              <a href={business.facebookUrl} target="_blank" rel="noreferrer" aria-label="Facebook" className="text-cream-100/70 hover:text-cream-50">
                <FacebookIcon className="h-5 w-5" />
              </a>
            )}
          </div>
        </div>

        <div>
          <h3 className="font-display text-sm uppercase tracking-widest text-cream-100/50">Visit</h3>
          <ul className="mt-4 space-y-3 text-sm text-cream-100/80">
            <li className="flex gap-2">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-fire-400" />
              <span>
                {business.addressLine1}
                {business.addressLine2 ? `, ${business.addressLine2}` : ""}, {business.city}, {business.postcode}
              </span>
            </li>
            <li className="flex gap-2">
              <Phone className="mt-0.5 h-4 w-4 shrink-0 text-fire-400" />
              <a href={`tel:${business.phone.replace(/\s+/g, "")}`} className="hover:text-cream-50">
                {business.phone}
              </a>
            </li>
            <li className="flex gap-2">
              <Mail className="mt-0.5 h-4 w-4 shrink-0 text-fire-400" />
              <a href={`mailto:${business.email}`} className="hover:text-cream-50">
                {business.email}
              </a>
            </li>
          </ul>
        </div>

        <div>
          <h3 className="font-display text-sm uppercase tracking-widest text-cream-100/50">Piccolo</h3>
          <ul className="mt-4 space-y-2 text-sm text-cream-100/80">
            <li><Link href="/menu" className="hover:text-cream-50">Menu</Link></li>
            <li><Link href="/order" className="hover:text-cream-50">Order Online</Link></li>
            <li><Link href="/allergens" className="hover:text-cream-50">Allergen Information</Link></li>
            <li><Link href="/privacy" className="hover:text-cream-50">Privacy Policy</Link></li>
            <li><Link href="/terms" className="hover:text-cream-50">Terms &amp; Conditions</Link></li>
          </ul>
        </div>

        <div className="col-span-2 md:col-span-1">
          <h3 className="font-display text-sm uppercase tracking-widest text-cream-100/50">Opening Hours</h3>
          <ul className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm text-cream-100/80 sm:block sm:space-y-1.5">
            {DAY_LABELS_FULL.map((label, idx) => {
              const hours = weeklyHours[idx];
              return (
                <li key={label} className={`flex justify-between gap-4 ${idx === today ? "font-semibold text-cream-50" : ""}`}>
                  <span>{label}</span>
                  <span>{hours?.isOpen ? `${formatHours(hours.openTime)} – ${formatHours(hours.closeTime)}` : "Closed"}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
      <div className="border-t border-cream-100/10 px-4 py-5 text-center text-xs text-cream-100/50 sm:px-6 lg:px-8">
        © {new Date().getFullYear()} {business.name}. All rights reserved.
      </div>
    </footer>
  );
}
