import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OrderStatus } from "@/lib/types";

const STEPS: { status: OrderStatus; label: string }[] = [
  { status: "received", label: "Received" },
  { status: "preparing", label: "Preparing" },
  { status: "ready", label: "Ready" },
  { status: "completed", label: "Completed" },
];

export function OrderStatusTracker({ status }: { status: OrderStatus }) {
  if (status === "cancelled") {
    return <p className="text-sm font-semibold text-fire-600">This order was cancelled.</p>;
  }

  const activeIndex = Math.max(
    0,
    STEPS.findIndex((s) => s.status === status)
  );

  return (
    <div className="flex items-center" role="list" aria-label="Order status">
      {STEPS.map((step, idx) => {
        const isPast = idx < activeIndex;
        const isCurrent = idx === activeIndex;
        return (
          <div key={step.status} className="flex flex-1 items-center last:flex-none" role="listitem" aria-current={isCurrent ? "step" : undefined}>
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-bold transition-colors",
                  isPast && "border-fire-500 bg-fire-500 text-cream-50",
                  isCurrent && "border-fire-500 bg-cream-50 text-fire-600 ring-2 ring-fire-500/30",
                  !isPast && !isCurrent && "border-char-200 bg-cream-50 text-char-300"
                )}
              >
                {isPast ? <Check className="h-4 w-4" /> : isCurrent ? <span className="h-2 w-2 animate-pulse rounded-full bg-fire-500" /> : idx + 1}
              </div>
              <span
                className={cn(
                  "text-[11px]",
                  isPast && "font-semibold text-char-800",
                  isCurrent && "font-bold text-fire-600",
                  !isPast && !isCurrent && "font-semibold text-char-300"
                )}
              >
                {step.label}
                {isCurrent && <span className="sr-only"> (current status)</span>}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div className={cn("mx-1 h-0.5 flex-1 rounded-full transition-colors", idx < activeIndex ? "bg-fire-500" : "bg-char-200")} />
            )}
          </div>
        );
      })}
    </div>
  );
}
