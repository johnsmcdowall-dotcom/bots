export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") || "http://localhost:3000";

export const isSupabaseConfigured = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

export const isStripeConfigured = Boolean(
  process.env.STRIPE_SECRET_KEY && process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
);

// The no-key `google.com/maps?...&output=embed` URL looks convenient but is
// unofficial and can silently render blank (blocked embed, consent
// interstitial, region quirks) with no reliable way to detect the failure
// from an iframe. Only the officially supported Maps Embed API — which
// requires a key — is used, and only once one is configured; otherwise the
// contact page shows a location card instead of gambling on a live map.
export const googleMapsEmbedKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_EMBED_KEY || "";
export const isGoogleMapsConfigured = Boolean(googleMapsEmbedKey);
