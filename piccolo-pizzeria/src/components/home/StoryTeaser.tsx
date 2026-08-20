import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function StoryTeaser() {
  return (
    <section className="bg-cream-200/60">
      <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-2 lg:px-8">
        <div className="relative aspect-[4/5] overflow-hidden rounded-3xl bg-char-800 lg:order-2">
          <Image
            src="/images/real/trailer-exterior.jpg"
            alt="The Piccolo Pizzeria trailer"
            fill
            sizes="(min-width: 1024px) 50vw, 100vw"
            className="object-cover"
          />
        </div>
        <div className="lg:order-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-fire-600">Our Story</p>
          <h2 className="mt-2 max-w-md text-balance font-display text-4xl uppercase tracking-tight text-char-900 sm:text-5xl">
            An Independent Pizza Trailer, Built Around One Oven.
          </h2>
          <p className="mt-5 max-w-md leading-relaxed text-char-600">
            We make the dough ourselves, stretch every base by hand and cook it right there in
            front of you. Nothing sits under a heat lamp.
          </p>
          <Button asChild variant="outline" size="lg" className="mt-7">
            <Link href="/our-story">
              Read our story <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
