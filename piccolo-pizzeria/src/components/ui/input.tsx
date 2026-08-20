import * as React from "react";
import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-12 w-full rounded-xl border border-char-200 bg-cream-50 px-4 text-base text-char-900 placeholder:text-char-400 transition-colors",
        "focus:border-fire-500 focus:outline-none focus:ring-2 focus:ring-fire-500/20",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "aria-[invalid=true]:border-fire-600 aria-[invalid=true]:ring-fire-600/10",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";

export { Input };
