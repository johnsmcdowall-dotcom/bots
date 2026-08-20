import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  accent?: "fire" | "basil" | "ember";
}) {
  return (
    <div className="rounded-2xl border border-char-200 bg-cream-50 p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-char-400">{label}</p>
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full",
            accent === "fire" && "bg-fire-500/10 text-fire-600",
            accent === "basil" && "bg-basil-500/15 text-basil-600",
            accent === "ember" && "bg-ember-400/15 text-ember-500",
            !accent && "bg-char-900/5 text-char-500"
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-3 font-display text-3xl font-semibold text-char-900">{value}</p>
    </div>
  );
}
