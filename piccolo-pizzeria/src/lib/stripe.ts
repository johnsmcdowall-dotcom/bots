import "server-only";
import Stripe from "stripe";

let stripeClient: Stripe | null = null;

/** Server-side Stripe client. Returns `null` when STRIPE_SECRET_KEY isn't set (demo mode). */
export function getStripeClient(): Stripe | null {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) return null;
  if (!stripeClient) {
    // No pinned apiVersion: uses the version configured on the Stripe
    // account/dashboard. Pin one explicitly here if you need to lock it.
    stripeClient = new Stripe(key);
  }
  return stripeClient;
}
