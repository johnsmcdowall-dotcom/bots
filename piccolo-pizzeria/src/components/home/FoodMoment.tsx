import Image from "next/image";

/**
 * One deliberate cinematic beat on the homepage — minimal copy, maximum
 * photography. No fabricated stats; just the pizza doing the talking.
 */
export function FoodMoment() {
  return (
    <section className="relative flex min-h-[70vh] items-end overflow-hidden bg-char-900 sm:min-h-[80vh]">
      <Image
        src="/images/real/pizza-special-3.jpg"
        alt="A charred Piccolo pizza, fresh from the oven"
        fill
        sizes="100vw"
        className="object-cover object-[50%_30%]"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-char-900 via-char-900/55 to-char-900/10" />

      <div className="relative mx-auto w-full max-w-7xl px-4 pb-14 pt-24 sm:px-6 sm:pb-20 lg:px-8">
        <h2 className="font-display text-5xl uppercase leading-[0.95] tracking-tight text-cream-50 sm:text-7xl">
          Fire. Dough. Pizza.
        </h2>
        <p className="mt-4 text-lg text-cream-100/75">That&apos;s how Piccolo does it.</p>
      </div>
    </section>
  );
}
