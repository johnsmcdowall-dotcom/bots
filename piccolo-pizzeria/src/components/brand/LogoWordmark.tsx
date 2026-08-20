import { cn } from "@/lib/utils";

/**
 * Compact horizontal lockup for space-constrained contexts (sticky header,
 * mobile nav). Small oven+flame glyph beside a two-line script/serif type
 * pairing, matching the LogoMark badge.
 */
export function LogoWordmark({
  className,
  tone = "dark",
}: {
  className?: string;
  tone?: "dark" | "light";
}) {
  const ink = tone === "dark" ? "var(--color-char-900)" : "var(--color-cream-100)";
  const accent = "var(--color-fire-500)";
  return (
    <svg
      viewBox="0 0 220 56"
      className={cn("h-10 w-auto sm:h-11", className)}
      role="img"
      aria-label="Piccolo Pizzeria"
    >
      <g transform="translate(2 8)" stroke={accent} fill="none" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 30 v-5 a20 20 0 0 1 40 0 v5" />
        <path d="M2 30 h40" />
        <rect x="16" y="-9" width="12" height="6" rx="1.5" />
        <path
          d="M15 30c0-4.5 3-6 3-9.5 0-2-.7-3.5-2-5 3.5.7 6.5 4 6.5 8.5 0 2-.7 3.5-2 5 2-.7 3.5-3 3.5-5.5 3 2 4.5 5 4.5 8 0 5-3.5 8.5-9.5 8.5s-6.5-3.5-6.5-8.5c0-1.3.6-2 1.3-3.3 0 2 0 2 1.2 2"
          fill={accent}
          strokeWidth="1.4"
          opacity="0.95"
        />
      </g>
      <text x="56" y="30" fill={ink} fontFamily="var(--font-script), cursive" fontSize="27">
        Piccolo
      </text>
      <text
        x="57"
        y="46"
        fill={ink}
        fontFamily="var(--font-display), serif"
        fontWeight="600"
        fontSize="11"
        letterSpacing="3"
        opacity="0.85"
      >
        PIZZERIA
      </text>
    </svg>
  );
}
