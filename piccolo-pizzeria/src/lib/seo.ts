import type { BusinessSettings, WeeklyHours } from "./types";
import { SITE_URL } from "./config";

const DAY_CODES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export function restaurantJsonLd(business: BusinessSettings, weeklyHours: WeeklyHours) {
  const openingHoursSpecification = Object.entries(weeklyHours)
    .filter(([, hours]) => hours.isOpen)
    .map(([day, hours]) => ({
      "@type": "OpeningHoursSpecification",
      dayOfWeek: DAY_CODES[Number(day)],
      opens: hours.openTime,
      closes: hours.closeTime,
    }));

  return {
    "@context": "https://schema.org",
    "@type": "Restaurant",
    name: business.name,
    description: business.tagline,
    servesCuisine: ["Pizza", "Italian"],
    priceRange: "££",
    url: SITE_URL,
    telephone: business.phone,
    email: business.email,
    image: `${SITE_URL}/images/placeholders/hero.svg`,
    address: {
      "@type": "PostalAddress",
      streetAddress: business.addressLine1,
      addressLocality: business.city,
      postalCode: business.postcode,
      addressCountry: "GB",
    },
    geo: {
      "@type": "GeoCoordinates",
      latitude: business.latitude,
      longitude: business.longitude,
    },
    openingHoursSpecification,
    sameAs: [business.instagramUrl, business.facebookUrl, business.tiktokUrl].filter(Boolean),
    acceptsReservations: "False",
    menu: `${SITE_URL}/menu`,
  };
}
