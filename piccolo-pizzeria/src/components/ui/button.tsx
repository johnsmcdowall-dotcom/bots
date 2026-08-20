import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-semibold tracking-wide transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fire-500 focus-visible:ring-offset-2 focus-visible:ring-offset-cream-100 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-fire-500 text-cream-50 hover:bg-fire-600 active:bg-fire-600 shadow-sm shadow-fire-500/20",
        dark: "bg-char-900 text-cream-50 hover:bg-char-800",
        outline: "border border-char-300 bg-transparent text-char-900 hover:bg-char-900 hover:text-cream-50 hover:border-char-900",
        ghost: "bg-transparent text-char-900 hover:bg-char-900/5",
        light: "bg-cream-50 text-char-900 hover:bg-cream-200 border border-char-200",
        link: "bg-transparent underline-offset-4 hover:underline text-fire-600 p-0 h-auto rounded-none",
        destructive: "bg-fire-600 text-cream-50 hover:bg-fire-500",
      },
      size: {
        sm: "h-9 px-4 text-xs",
        md: "h-11 px-5",
        lg: "h-13 px-7 text-base",
        xl: "h-14 px-8 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
