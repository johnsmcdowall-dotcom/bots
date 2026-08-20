import Image from "next/image";
import { InstagramIcon } from "@/components/icons/SocialIcons";
import type { BusinessSettings } from "@/lib/types";

const TILES = [
  { src: "/images/real/pizza-vegetarian.jpg", alt: "Vegetarian pizza fresh from the oven" },
  { src: "/images/real/oven-flame-2.jpg", alt: "The oven at full heat" },
  { src: "/images/real/pizza-special-2.jpg", alt: "This week's special" },
  { src: "/images/real/trailer-interior.jpg", alt: "Inside the Piccolo trailer" },
  { src: "/images/real/pizza-special-4.jpg", alt: "Fresh out of the oven" },
  { src: "/images/real/oven-flame-1.jpg", alt: "Woodfired flame" },
];

export function InstagramGallery({ business }: { business: BusinessSettings }) {
  if (!business.instagramUrl) return null;
  const handle = business.instagramUrl.replace(/\/$/, "").split("/").pop();

  return (
    <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 sm:pb-24 lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-display text-3xl uppercase tracking-tight text-char-900 sm:text-4xl">From the Pass</h2>
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
        {TILES.map((tile, i) => (
          <a
            key={i}
            href={business.instagramUrl}
            target="_blank"
            rel="noreferrer"
            className="group relative aspect-square overflow-hidden rounded-xl bg-char-800"
          >
            <Image
              src={tile.src}
              alt={tile.alt}
              fill
              sizes="(min-width: 768px) 16vw, 33vw"
              className="object-cover transition-transform duration-500 ease-out group-hover:scale-[1.06]"
            />
            <div className="absolute inset-0 bg-char-900/0 transition-colors duration-200 group-hover:bg-char-900/10" />
          </a>
        ))}
      </div>
    </section>
  );
}
