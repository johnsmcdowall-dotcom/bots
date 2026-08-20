import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/config";

export default function sitemap(): MetadataRoute.Sitemap {
  const routes = ["", "/menu", "/our-story", "/contact", "/allergens", "/privacy", "/terms"];

  return routes.map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified: new Date(),
    changeFrequency: route === "/menu" ? "daily" : "monthly",
    priority: route === "" ? 1 : route === "/menu" ? 0.9 : 0.5,
  }));
}
