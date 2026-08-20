import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide whitespace-nowrap",
  {
    variants: {
      variant: {
        neutral: "bg-char-900/[0.06] text-char-700",
        fire: "bg-fire-500 text-cream-50",
        ember: "bg-ember-400 text-char-900",
        basil: "bg-basil-500/15 text-basil-600",
        outline: "border border-char-300 text-char-600",
        dark: "bg-char-900 text-cream-50",
        soldout: "bg-char-900/80 text-cream-100",
        success: "bg-basil-500/15 text-basil-600",
        warning: "bg-ember-400/20 text-ember-500",
      },
    },
    defaultVariants: { variant: "neutral" },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}

export { Badge, badgeVariants };
