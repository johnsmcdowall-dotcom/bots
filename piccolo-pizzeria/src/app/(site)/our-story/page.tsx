import Image from "next/image";
import Link from "next/link";
import type { Metadata } from "next";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Our Story",
  description: "Piccolo Pizzeria is an independent wood-fired pizza trailer — one oven, hand-stretched dough, no shortcuts.",
};

export default function OurStoryPage() {
  return (
    <div>
      <div className="relative h-[46vh] min-h-[320px] w-full overflow-hidden bg-char-900">
        <Image src="/images/real/oven-flame-2.jpg" alt="The wood-fired oven at Piccolo Pizzeria" fill priority className="object-cover opacity-80" />
        <div className="absolute inset-0 bg-gradient-to-t from-char-900 via-char-900/20 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 mx-auto max-w-4xl px-4 pb-10 sm:px-6 lg:px-8">
          <p className="text-xs font-semibold uppercase tracking-widest text-fire-400">Our Story</p>
          <h1 className="mt-2 text-balance font-display text-4xl font-semibold text-cream-50 sm:text-5xl">
            One oven. One idea done properly.
          </h1>
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <div className="space-y-6 text-lg leading-relaxed text-char-700">
          <p>
            Piccolo Pizzeria started as a simple idea: build a proper wood-fired oven, put it on a
            trailer, and make the best pizza we could with it — nothing more complicated than
            that. No shortcuts, no compromises on the dough.
          </p>
          <p>
            Every base is hand-stretched to order and fired at high heat, the way it&apos;s meant
            to be — blistered, chewy, gone in a couple of minutes. We keep the menu focused: a
            short list of pizzas and pizza sandwiches done well, rather than a long list done
            averagely.
          </p>
          <p>
            You&apos;ll find us out and about across the North East — at social clubs, events and
            our regular pitches. Follow us on Instagram for where we&apos;ll be next, or order
            ahead for collection when we&apos;re parked up.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-2 gap-4">
          <div className="relative aspect-square overflow-hidden rounded-2xl">
            <Image src="/images/real/trailer-interior.jpg" alt="Inside the Piccolo Pizzeria trailer" fill className="object-cover" />
          </div>
          <div className="relative aspect-square overflow-hidden rounded-2xl">
            <Image src="/images/real/pizza-vegetarian.jpg" alt="A wood-fired vegetarian pizza fresh from the oven" fill className="object-cover" />
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/order">Order Now</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/menu">View Menu</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
