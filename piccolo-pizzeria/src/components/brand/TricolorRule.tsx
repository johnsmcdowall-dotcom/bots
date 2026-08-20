import { cn } from "@/lib/utils";

/** The Italian tricolour bar from the Piccolo mark, used sparingly as a signature detail. */
export function TricolorRule({ className }: { className?: string }) {
  return (
    <span className={cn("tricolor-rule", className)} aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}
