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
    <div className="flex items-center">
      {STEPS.map((step, idx) => {
        const done = idx <= activeIndex;
        return (
          <div key={step.status} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-bold transition-colors",
                  done ? "border-fire-500 bg-fire-500 text-cream-50" : "border-char-200 bg-cream-50 text-char-300"
                )}
              >
                {done ? <Check className="h-4 w-4" /> : idx + 1}
              </div>
              <span className={cn("text-[11px] font-semibold", done ? "text-char-800" : "text-char-300")}>{step.label}</span>
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
