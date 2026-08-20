import Image from "next/image";
import { cn } from "@/lib/utils";

/**
 * The real Piccolo Pizzeria badge (brick oven + flame, script wordmark,
 * "PIZZERIA" subtext, Italian tricolour bar) supplied by the business.
 * Square/circular, transparent outside the ring so it drops onto any
 * background. Used at larger sizes (hero, footer, admin login, PWA icons).
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <Image
      src="/images/brand/piccolo-logo.png"
      alt="Piccolo Pizzeria"
      width={800}
      height={800}
      className={cn("h-auto w-full", className)}
    />
  );
}
