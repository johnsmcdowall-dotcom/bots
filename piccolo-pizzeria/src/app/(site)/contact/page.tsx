import type { Metadata } from "next";
import { MapPin, Phone, Mail, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { InstagramIcon, FacebookIcon } from "@/components/icons/SocialIcons";
import { getBusinessSettings, getWeeklyHours } from "@/lib/data/business";

export const metadata: Metadata = {
  title: "Find Us",
  description: "Find Piccolo Pizzeria, get directions, opening hours and contact details.",
};

const DAY_LABELS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function formatTime(hhmm: string) {
  const [h, m] = hhmm.split(":").map(Number);
  const period = h >= 12 ? "pm" : "am";
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return m === 0 ? `${hour12}${period}` : `${hour12}:${String(m).padStart(2, "0")}${period}`;
}

export default async function ContactPage() {
  const [business, weeklyHours] = await Promise.all([getBusinessSettings(), getWeeklyHours()]);
  const today = new Date().getDay();
  const mapsQuery = encodeURIComponent(`${business.addressLine1}, ${business.city}, ${business.postcode}`);

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <p className="text-xs font-semibold uppercase tracking-widest text-fire-600">Find Us</p>
      <h1 className="mt-2 font-display text-5xl uppercase tracking-tight text-char-900 sm:text-6xl">Get in Touch</h1>
      <p className="mt-3 max-w-xl text-char-500">
        Our regular pitch is the car park at Elm Tree Social Club — order ahead for collection, or
        follow us on Instagram for one-off pitches elsewhere.
      </p>

      <div className="mt-10 grid gap-10 lg:grid-cols-2">
        <div>
          <div className="aspect-[4/3] overflow-hidden rounded-2xl border border-char-200 bg-char-100">
            <iframe
              title="Map"
              src={`https://www.google.com/maps?q=${mapsQuery}&output=embed`}
              className="h-full w-full border-0"
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
          </div>
          <Button asChild size="lg" className="mt-4 w-full">
            <a href={`https://www.google.com/maps/search/?api=1&query=${mapsQuery}`} target="_blank" rel="noreferrer">
              Get Directions
            </a>
          </Button>
        </div>

        <div className="space-y-8">
          <div>
            <h2 className="font-display text-xl text-char-900">Contact</h2>
            <ul className="mt-4 space-y-3 text-char-600">
              <li className="flex gap-3">
                <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-fire-500" />
                <span>
                  {business.addressLine1}
                  {business.addressLine2 ? `, ${business.addressLine2}` : ""}, {business.city}, {business.postcode}
                </span>
              </li>
              <li className="flex gap-3">
                <Phone className="mt-0.5 h-5 w-5 shrink-0 text-fire-500" />
                <a href={`tel:${business.phone.replace(/\s+/g, "")}`} className="hover:text-char-900">
                  {business.phone}
                </a>
              </li>
              <li className="flex gap-3">
                <Mail className="mt-0.5 h-5 w-5 shrink-0 text-fire-500" />
                <a href={`mailto:${business.email}`} className="hover:text-char-900">
                  {business.email}
                </a>
              </li>
            </ul>
            <div className="mt-4 flex gap-3">
              {business.instagramUrl && (
                <a
                  href={business.instagramUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-char-900/5 text-char-700 hover:bg-char-900 hover:text-cream-50"
                  aria-label="Instagram"
                >
                  <InstagramIcon className="h-4 w-4" />
                </a>
              )}
              {business.facebookUrl && (
                <a
                  href={business.facebookUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-char-900/5 text-char-700 hover:bg-char-900 hover:text-cream-50"
                  aria-label="Facebook"
                >
                  <FacebookIcon className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>

          <div>
            <h2 className="flex items-center gap-2 font-display text-xl text-char-900">
              <Clock className="h-5 w-5 text-fire-500" /> Opening Hours
            </h2>
            <ul className="mt-4 space-y-2 text-sm">
              {DAY_LABELS.map((label, idx) => {
                const hours = weeklyHours[idx];
                return (
                  <li
                    key={label}
                    className={`flex justify-between border-b border-char-100 pb-2 ${idx === today ? "font-semibold text-char-900" : "text-char-600"}`}
                  >
                    <span>{label}</span>
                    <span>{hours?.isOpen ? `${formatTime(hours.openTime)} – ${formatTime(hours.closeTime)}` : "Closed"}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="rounded-2xl bg-char-900 p-5 text-cream-100">
            <h2 className="font-display text-lg text-cream-50">Weddings, Corporate &amp; Festivals</h2>
            <p className="mt-2 text-sm leading-relaxed text-cream-100/75">
              We take the oven on the road for private and corporate bookings of any size —
              weddings, corporate events, festivals, we&apos;ve done them all. Get in touch by
              phone or email above and we&apos;ll sort the details.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
