import Image from "next/image";
import { InstagramIcon } from "@/components/icons/SocialIcons";
import type { BusinessSettings } from "@/lib/types";

const TILES = [
  "/images/real/pizza-vegetarian.jpg",
  "/images/real/oven-flame-2.jpg",
  "/images/real/pizza-special-2.jpg",
  "/images/real/trailer-interior.jpg",
  "/images/real/pizza-special-4.jpg",
  "/images/real/oven-flame-1.jpg",
];

export function InstagramGallery({ business }: { business: BusinessSettings }) {
  if (!business.instagramUrl) return null;
  const handle = business.instagramUrl.replace(/\/$/, "").split("/").pop();

  return (
    <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 sm:pb-24 lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-display text-2xl font-semibold text-char-900 sm:text-3xl">From the pass</h2>
        <a
          href={business.instagramUrl}
          target="_blank"
          rel="noreferrer"
          className="flex shrink-0 items-center gap-1.5 text-sm font-semibold text-char-700 hover:text-fire-600"
        >
          <InstagramIcon className="h-4 w-4" /> @{handle}
        </a>
      </div>
      <div className="mt-6 grid grid-cols-3 gap-2 sm:gap-4 md:grid-cols-6">
        {TILES.map((src, i) => (
          <a
            key={i}
            href={business.instagramUrl}
            target="_blank"
            rel="noreferrer"
            className="relative aspect-square overflow-hidden rounded-xl bg-char-800 transition-opacity hover:opacity-90"
          >
            <Image src={src} alt="" fill className="object-cover" />
          </a>
        ))}
      </div>
    </section>
  );
}
