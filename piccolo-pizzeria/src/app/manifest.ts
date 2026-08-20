import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Piccolo Pizzeria",
    short_name: "Piccolo",
    description: "Independent woodfired pizza trailer on Teesside. Order online for collection.",
    start_url: "/",
    display: "standalone",
    background_color: "#faf5ea",
    theme_color: "#0b0b0b",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-512-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
