import type { Metadata } from "next";
import { getBusinessSettings } from "@/lib/data/business";

export const metadata: Metadata = { title: "Privacy Policy", robots: { index: false } };

export default async function PrivacyPage() {
  const business = await getBusinessSettings();

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <h1 className="font-display text-5xl uppercase tracking-tight text-char-900">Privacy Policy</h1>
      <p className="mt-2 text-sm text-char-400">Last updated: {new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</p>

      <div className="prose-content mt-8 space-y-6 text-char-700">
        <section>
          <h2 className="font-display text-xl text-char-900">1. Who we are</h2>
          <p className="mt-2">
            {business.name} (&ldquo;we&rdquo;, &ldquo;us&rdquo;) operates this website and online
            ordering service. You can contact us at{" "}
            <a href={`mailto:${business.email}`} className="text-fire-600 underline">
              {business.email}
            </a>{" "}
            or {business.phone}.
          </p>
        </section>
        <section>
          <h2 className="font-display text-xl text-char-900">2. Information we collect</h2>
          <p className="mt-2">
            When you place an order we collect your name, phone number, email address and, for
            delivery orders, your delivery address. We do not collect or store your card details.
            Payments are processed securely by Stripe.
          </p>
        </section>
        <section>
          <h2 className="font-display text-xl text-char-900">3. How we use it</h2>
          <p className="mt-2">
            We use your details to fulfil your order, contact you about it, and, if you agree, let
            you know about offers and updates. We keep order records for accounting and food safety
            purposes as required by law.
          </p>
        </section>
        <section>
          <h2 className="font-display text-xl text-char-900">4. Sharing your data</h2>
          <p className="mt-2">
            We share payment data with Stripe to process transactions, and may use analytics or
            email providers to operate the service. We do not sell your personal data.
          </p>
        </section>
        <section>
          <h2 className="font-display text-xl text-char-900">5. Your rights</h2>
          <p className="mt-2">
            You can ask us to access, correct or delete your personal data at any time by
            contacting us using the details above.
          </p>
        </section>
      </div>
    </div>
  );
}
