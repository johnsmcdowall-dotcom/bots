import type { Metadata, Viewport } from "next";
import { Fraunces, Manrope, Kaushan_Script } from "next/font/google";
import { Toaster } from "sonner";
import { SITE_URL } from "@/lib/config";
import "./globals.css";

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz", "SOFT", "WONK"],
  display: "swap",
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  display: "swap",
});

const kaushan = Kaushan_Script({
  variable: "--font-script",
  subsets: ["latin"],
  weight: "400",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Piccolo Pizzeria — Wood-Fired Pizza, North East England",
    template: "%s — Piccolo Pizzeria",
  },
  description:
    "Proper wood-fired pizza, hand-stretched daily. Independent pizzeria on Teesside serving Stockton-on-Tees, Middlesbrough and beyond. Order online for collection or delivery.",
  keywords: [
    "wood-fired pizza",
    "pizza Stockton-on-Tees",
    "pizza Teesside",
    "pizza Middlesbrough",
    "Neapolitan pizza North East",
  ],
  applicationName: "Piccolo Pizzeria",
  manifest: "/manifest.webmanifest",
  openGraph: {
    type: "website",
    siteName: "Piccolo Pizzeria",
    title: "Piccolo Pizzeria — Wood-Fired Pizza, North East England",
    description:
      "Proper wood-fired pizza, hand-stretched daily. Order online for collection or delivery.",
    url: SITE_URL,
    locale: "en_GB",
  },
  twitter: {
    card: "summary_large_image",
    title: "Piccolo Pizzeria",
    description: "Proper wood-fired pizza, hand-stretched daily.",
  },
  icons: {
    icon: "/icon.svg",
    apple: "/icons/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#1c1712",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en-GB"
      className={`${fraunces.variable} ${manrope.variable} ${kaushan.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-cream-100 font-sans text-char-900">
        {children}
        <Toaster
          position="top-center"
          toastOptions={{
            style: {
              background: "var(--color-char-900)",
              color: "var(--color-cream-50)",
              border: "none",
            },
          }}
        />
      </body>
    </html>
  );
}
