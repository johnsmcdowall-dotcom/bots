import Image from "next/image";
import Link from "next/link";
import type { Metadata } from "next";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Our Story",
  description: "Piccolo Pizzeria is an independent pizza trailer built around one woodfired oven.",
};

export default function OurStoryPage() {
  return (
    <div>
      <div className="relative h-[46vh] min-h-[320px] w-full overflow-hidden bg-char-900">
        <Image src="/images/real/oven-flame-2.jpg" alt="The woodfired oven at Piccolo Pizzeria" fill priority sizes="100vw" className="object-cover opacity-80" />
        <div className="absolute inset-0 bg-gradient-to-t from-char-900 via-char-900/20 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 mx-auto max-w-4xl px-4 pb-10 sm:px-6 lg:px-8">
          <p className="text-xs font-semibold uppercase tracking-widest text-fire-400">Our Story</p>
          <h1 className="mt-2 text-balance font-display text-5xl uppercase tracking-tight text-cream-50 sm:text-6xl">
            One Oven. One Idea Done Properly.
          </h1>
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <div className="space-y-6 text-lg leading-relaxed text-char-700">
          <p>
            Piccolo is an independent pizza trailer, built around one woodfired oven. We make the
            dough ourselves, stretch every base to order and cook it right in front of you.
            Blistered, chewy, gone in a couple of minutes.
          </p>
          <p>
            We keep the menu short: a handful of pizzas and pizza sandwiches done properly, rather
            than a long list done averagely.
          </p>
          <p>
            Find us most weeks in the car park at Elm Tree Social Club. Follow us on Instagram for
            exact days, or order ahead for collection when we&apos;re parked up.
          </p>
          <p>
            We also take the oven out for weddings, corporate events and festivals. Fancy Piccolo
            at your event?{" "}
            <Link href="/contact" className="font-semibold text-fire-600 underline underline-offset-2">
              Get in touch
            </Link>{" "}
            and we&apos;ll sort the details.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-2 gap-4">
          <div className="relative aspect-square overflow-hidden rounded-2xl bg-char-800">
            <Image
              src="/images/real/trailer-interior.jpg"
              alt="Inside the Piccolo Pizzeria trailer"
              fill
              sizes="(min-width: 768px) 384px, 50vw"
              className="object-cover"
            />
          </div>
          <div className="relative aspect-square overflow-hidden rounded-2xl bg-char-800">
            <Image
              src="/images/real/pizza-vegetarian.jpg"
              alt="A vegetarian pizza fresh from the oven"
              fill
              sizes="(min-width: 768px) 384px, 50vw"
              className="object-cover"
            />
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
