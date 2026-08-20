"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, Phone } from "lucide-react";
import { InstagramIcon, FacebookIcon } from "@/components/icons/SocialIcons";
import * as Dialog from "@radix-ui/react-dialog";
import { LogoWordmark } from "@/components/brand/LogoWordmark";
import { Button } from "@/components/ui/button";
import type { BusinessSettings } from "@/lib/types";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/menu", label: "Menu" },
  { href: "/order", label: "Order Online" },
  { href: "/our-story", label: "Our Story" },
  { href: "/contact", label: "Find Us" },
];

export function MobileNav({ business }: { business: BusinessSettings }) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          className="flex h-11 w-11 items-center justify-center rounded-full text-char-900 hover:bg-char-900/5 md:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-6 w-6" />
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[60] bg-char-900/60 data-[state=open]:animate-fade-in" />
        <Dialog.Content
          className="fixed inset-y-0 right-0 z-[60] flex w-[86%] max-w-sm flex-col bg-cream-50 p-6 shadow-2xl outline-none data-[state=open]:animate-in data-[state=open]:slide-in-from-right data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between">
            <Dialog.Title asChild>
              <LogoWordmark className="h-9" />
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="flex h-10 w-10 items-center justify-center rounded-full text-char-700 hover:bg-char-900/5" aria-label="Close menu">
                ✕
              </button>
            </Dialog.Close>
          </div>

          <nav className="mt-10 flex flex-col gap-1">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-xl px-3 py-3.5 font-display text-2xl font-semibold text-char-900 transition-colors hover:bg-char-900/5"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="mt-auto flex flex-col gap-4 border-t border-char-200 pt-6">
            <Button asChild size="lg" onClick={() => setOpen(false)}>
              <Link href="/order">Order Now</Link>
            </Button>
            <a href={`tel:${business.phone.replace(/\s+/g, "")}`} className="flex items-center gap-2 text-sm font-medium text-char-600">
              <Phone className="h-4 w-4" /> {business.phone}
            </a>
            <div className="flex items-center gap-3">
              {business.instagramUrl && (
                <a href={business.instagramUrl} target="_blank" rel="noreferrer" aria-label="Instagram" className="text-char-500 hover:text-fire-500">
                  <InstagramIcon className="h-5 w-5" />
                </a>
              )}
              {business.facebookUrl && (
                <a href={business.facebookUrl} target="_blank" rel="noreferrer" aria-label="Facebook" className="text-char-500 hover:text-fire-500">
                  <FacebookIcon className="h-5 w-5" />
                </a>
              )}
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
