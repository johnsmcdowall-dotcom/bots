"use client";

import { useState, useTransition } from "react";
import { Minus, Plus, Timer } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { updateBusinessSettingsAction } from "@/lib/actions/settings";
import { estimatedWaitRange } from "@/lib/prep-time";

/**
 * Quick -5/+5 nudge for the kitchen's current backlog, right where staff
 * are already watching orders come in — no need to leave the board and go
 * into Settings for what's often a several-times-a-shift adjustment.
 * Writes to the exact same current_wait_minutes field Settings edits (via
 * the same updateBusinessSettingsAction), so there's one source of truth,
 * not a shadow copy.
 */
export function PrepTimeControl({ minPrepMinutes, currentWaitMinutes }: { minPrepMinutes: number; currentWaitMinutes: number }) {
  const [value, setValue] = useState(currentWaitMinutes);
  const [isPending, startTransition] = useTransition();

  function adjust(delta: number) {
    const next = Math.max(0, value + delta);
    if (next === value) return;
    const previous = value;
    setValue(next);
    startTransition(async () => {
      const res = await updateBusinessSettingsAction({ currentWaitMinutes: next });
      if (res?.error) {
        toast.error(res.error);
        setValue(previous);
      }
    });
  }

  const range = estimatedWaitRange({ minPrepMinutes, currentWaitMinutes: value });

  return (
    <div className="flex items-center gap-3 rounded-full border border-char-200 bg-cream-50 py-1.5 pl-4 pr-1.5">
      <Timer className="h-4 w-4 text-char-400" />
      <div className="text-xs">
        <span className="font-semibold text-char-700">Kitchen wait</span>
        <span className="ml-1.5 text-char-400">customers see {range.label}</span>
      </div>
      <div className="ml-1 flex items-center rounded-full border border-char-200">
        <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => adjust(-5)} disabled={isPending || value <= 0} aria-label="Decrease current wait by 5 minutes">
          <Minus className="h-3.5 w-3.5" />
        </Button>
        <span className="w-14 text-center text-xs font-semibold tabular-nums text-char-800">+{value} min</span>
        <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => adjust(5)} disabled={isPending} aria-label="Increase current wait by 5 minutes">
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
