"use client";

// The `/pure` entry point avoids @stripe/stripe-js's default side effect of
// injecting the js.stripe.com <script> tag on import — with it, every page
// that imports this module fetches Stripe's script even when checkout never
// renders payment UI (e.g. demo mode with no keys configured). The `Stripe`
// type itself is type-only so importing it from the main package is safe.
import { loadStripe } from "@stripe/stripe-js/pure";
import type { Stripe } from "@stripe/stripe-js";

let stripePromise: Promise<Stripe | null> | null = null;

export function getStripe() {
  const key = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
  if (!key) return null;
  if (!stripePromise) stripePromise = loadStripe(key);
  return stripePromise;
}
