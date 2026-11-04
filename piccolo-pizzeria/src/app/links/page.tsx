import type { Metadata } from "next";
import { LogoMark } from "@/components/brand/LogoMark";
import { TricolorRule } from "@/components/brand/TricolorRule";
import { InstagramIcon, FacebookIcon, TikTokIcon } from "@/components/icons/SocialIcons";
import { Button } from "@/components/ui/button";
import { UtensilsCrossed, ShoppingBag, MapPin } from "lucide-react";

export const metadata: Metadata = {
  title: "Links",
  description: "Find Piccolo Pizzeria on Instagram, Facebook and TikTok.",
};

const SOCIAL_LINKS = [
  { name: "Instagram", href: "https://www.instagram.com/piccolo_pizzeria25/", Icon: InstagramIcon },
  { name: "Facebook", href: "https://www.facebook.com/share/1FMtQf1k4J/?mibextid=wwXIfr", Icon: FacebookIcon },
  { name: "TikTok", href: "https://www.tiktok.com/@piccolo.pizzeria?_r=1&_t=ZG-9B1KHzo1ulc", Icon: TikTokIcon },
];

const COMING_SOON = [
  { name: "View Our Menu", Icon: UtensilsCrossed },
  { name: "Order Online", Icon: ShoppingBag },
  { name: "Find Us", Icon: MapPin },
];

/**
 * Standalone "link in bio" page — deliberately outside the (site) route
 * group, so it renders from the root layout alone (fonts + base colour)
 * with no Header/Footer and no business-settings/menu data fetch of any
 * kind. That's what makes it work regardless of whether the rest of the
 * site is finished or connected to a real Supabase project: there is
 * nothing here for an unfinished page or an unconfigured service to break.
 */
export default function LinksPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center bg-cream-100 px-5 py-14 text-char-900">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center text-center">
          <div className="w-28 sm:w-32">
            <LogoMark />
          </div>
          <TricolorRule className="mt-5" />
          <h1 className="mt-5 text-balance font-display text-3xl uppercase tracking-tight sm:text-4xl">
            Piccolo Pizzeria
          </h1>
          <p className="mt-2 text-char-500">Woodfired. Hand stretched. Piccolo.</p>
        </div>

        <div className="mt-10 flex flex-col gap-3">
          {SOCIAL_LINKS.map(({ name, href, Icon }) => (
            <Button key={name} asChild variant="dark" size="xl" className="w-full justify-start px-6 text-base">
              <a href={href} target="_blank" rel="noreferrer">
                <Icon className="h-5 w-5 shrink-0" />
                {name}
              </a>
            </Button>
          ))}
        </div>

        <div className="mt-10 flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-char-400">
          <div className="h-px flex-1 bg-char-200" />
          More from Piccolo
          <div className="h-px flex-1 bg-char-200" />
        </div>

        <div className="mt-5 flex flex-col gap-3">
          {COMING_SOON.map(({ name, Icon }) => (
            <div
              key={name}
              aria-disabled="true"
              className="flex h-14 w-full items-center gap-3 rounded-full border border-char-200 bg-cream-50 px-6 text-base font-semibold tracking-wide text-char-400"
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="flex-1 text-left">{name}</span>
              <span className="rounded-full bg-char-900/5 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wide text-char-500">
                Coming Soon
              </span>
            </div>
          ))}
        </div>

        <p className="mt-12 text-center text-xs text-char-400">
          © {new Date().getFullYear()} Piccolo Pizzeria
        </p>
      </div>
    </main>
  );
}
