import { cn } from "@/lib/utils";

/**
 * Circular badge lockup of the Piccolo Pizzeria mark: brick oven + flame,
 * script wordmark, serif "PIZZERIA" subtext and an Italian tricolour bar.
 * Used at larger sizes (hero, footer, admin login, PWA/social icons).
 */
export function LogoMark({
  className,
  ink = "var(--color-cream-100)",
  bg = "var(--color-char-900)",
}: {
  className?: string;
  ink?: string;
  bg?: string;
}) {
  const id = "piccolo-grain";
  return (
    <svg
      viewBox="0 0 240 240"
      className={cn("h-auto w-full", className)}
      role="img"
      aria-label="Piccolo Pizzeria"
    >
      <defs>
        <filter id={id}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" result="noise" />
          <feColorMatrix in="noise" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.05 0" />
        </filter>
      </defs>

      <circle cx="120" cy="120" r="119" fill={bg} />
      <circle cx="120" cy="120" r="119" filter={`url(#${id})`} />

      <circle cx="120" cy="120" r="107" fill="none" stroke={ink} strokeWidth="2.5" opacity="0.9" />
      <circle cx="120" cy="120" r="100" fill="none" stroke={ink} strokeWidth="1" opacity="0.7" />

      {/* wood-fired oven + flame */}
      <g transform="translate(120 62)" stroke={ink} fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M-34 18 v-6 a34 34 0 0 1 68 0 v6" />
        <path d="M-34 18 h68" />
        <rect x="-9" y="-32" width="18" height="9" rx="2" />
        <path
          d="M-8 18c0-6 4-8 4-13 0-3-1-5-3-7 5 1 9 6 9 12 0 3-1 5-3 7 3-1 5-4 5-8 4 3 6 7 6 11 0 7-5 12-13 12s-9-5-9-12c0-2 1-3 2-5 0 3 0 3 2 3"
          strokeWidth="2"
          fill={ink}
          opacity="0.92"
        />
      </g>

      {/* script wordmark */}
      <text
        x="120"
        y="140"
        textAnchor="middle"
        fill={ink}
        fontFamily="var(--font-script), cursive"
        fontSize="40"
      >
        Piccolo
      </text>

      {/* serif subtext */}
      <text
        x="120"
        y="164"
        textAnchor="middle"
        fill={ink}
        fontFamily="var(--font-display), sans-serif"
        fontSize="19"
        letterSpacing="4"
      >
        PIZZERIA
      </text>

      {/* tricolour bar */}
      <g transform="translate(75 178)">
        <rect x="0" y="0" width="30" height="8" fill="var(--color-basil-500)" />
        <rect x="30" y="0" width="30" height="8" fill={ink} />
        <rect x="60" y="0" width="30" height="8" fill="var(--color-fire-500)" />
      </g>
    </svg>
  );
}
