import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function StoryTeaser() {
  return (
    <section className="bg-cream-200/60">
      <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-2 lg:px-8">
        <div className="relative aspect-[4/5] overflow-hidden rounded-3xl lg:order-2">
          <Image src="/images/real/trailer-exterior.jpg" alt="The Piccolo Pizzeria wood-fired trailer" fill className="object-cover" />
        </div>
        <div className="lg:order-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-fire-600">Our Story</p>
          <h2 className="mt-2 max-w-md text-balance font-display text-3xl font-semibold text-char-900 sm:text-4xl">
            An independent pizza trailer, built around one oven.
          </h2>
          <p className="mt-5 max-w-md leading-relaxed text-char-600">
            Piccolo is a small, independent wood-fired pizza trailer — one oven, hand-stretched
            dough and a menu that doesn&apos;t cut corners. We fire every pizza to order, right
            there in front of you, nothing sits under a heat lamp.
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
