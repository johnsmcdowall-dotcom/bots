import type { Metadata } from "next";
import { getBusinessSettings } from "@/lib/data/business";

export const metadata: Metadata = { title: "Terms & Conditions", robots: { index: false } };

export default async function TermsPage() {
  const business = await getBusinessSettings();

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <h1 className="font-display text-5xl uppercase tracking-tight text-char-900">Terms &amp; Conditions</h1>
      <p className="mt-2 text-sm text-char-400">Last updated: {new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</p>

      <div className="mt-8 space-y-6 text-char-700">
        <section>
          <h2 className="font-display text-xl text-char-900">1. Orders</h2>
          <p className="mt-2">
            By placing an order through this website you agree to pay the total shown at checkout.
            Prices include VAT where applicable. We reserve the right to refuse or cancel an order,
            for example if an item becomes unavailable after ordering — in that case we&apos;ll
            refund you in full.
          </p>
        </section>
        <section>
          <h2 className="font-display text-xl text-char-900">2. Collection &amp; delivery times</h2>
          <p className="mt-2">
            Estimated collection and delivery times are just that — estimates. Times can vary with
            demand and traffic. We&apos;ll always try to have your order ready close to the time
            shown.
          </p>
        </section>
        <section>
          <h2 className="font-display text-xl text-char-900">3. Payment</h2>
          <p className="mt-2">
            Payment is taken securely online via Stripe at the time of ordering. We never see or
            store your full card details.
          </p>
        </section>
        <section>
          <h2 className="font-display text-xl text-char-900">4. Cancellations &amp; refunds</h2>
          <p className="mt-2">
            If you need to cancel or change an order, please call us on {business.phone} as soon
            as possible — once your order has entered the oven we may not be able to change it.
          </p>
        </section>
        <section>
          <h2 className="font-display text-xl text-char-900">5. Allergens</h2>
          <p className="mt-2">
            Please see our <a href="/allergens" className="text-fire-600 underline">Allergen Information</a> page before
            ordering if you have a food allergy or intolerance.
          </p>
        </section>
      </div>
    </div>
  );
}
