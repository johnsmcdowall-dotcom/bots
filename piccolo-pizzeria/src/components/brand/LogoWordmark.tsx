import { LogoMark } from "@/components/brand/LogoMark";
import { cn } from "@/lib/utils";

/**
 * The real Piccolo Pizzeria badge sized for horizontal, space-constrained
 * contexts (sticky header, mobile nav, admin sidebar) — same asset as
 * LogoMark, just height-driven rather than width-driven.
 */
export function LogoWordmark({ className }: { className?: string }) {
  return <LogoMark className={cn("w-auto", className)} />;
}
