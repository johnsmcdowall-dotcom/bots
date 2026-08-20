"use client";

import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ModifierGroup } from "@/lib/types";

export function ModifierSelector({
  group,
  selected,
  onChange,
}: {
  group: ModifierGroup;
  selected: string[];
  onChange: (optionIds: string[]) => void;
}) {
  const isSingle = group.maxSelect === 1;
  const atMax = selected.length >= group.maxSelect;

  return (
    <fieldset className="border-t border-char-200 py-5 first:border-t-0 first:pt-0">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <legend className="font-display text-base text-char-900">
          {group.name}
          {group.required && <span className="ml-1.5 text-fire-600">*</span>}
        </legend>
        <span className="text-xs font-medium text-char-400">
          {group.required
            ? "Required"
            : group.maxSelect > 1
              ? `Choose up to ${group.maxSelect}`
              : "Optional"}
        </span>
      </div>
      {group.description && <p className="mb-3 -mt-2 text-xs text-char-500">{group.description}</p>}

      {isSingle ? (
        <RadioGroup value={selected[0] ?? ""} onValueChange={(v) => onChange([v])}>
          {group.options.map((opt) => (
            <label
              key={opt.id}
              className={cn(
                "flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-char-200 px-4 py-3 transition-colors",
                selected[0] === opt.id ? "border-fire-500 bg-fire-500/5" : "hover:bg-char-900/[0.03]",
                opt.soldOut && "cursor-not-allowed opacity-50"
              )}
            >
              <span className="flex items-center gap-3">
                <RadioGroupItem value={opt.id} disabled={opt.soldOut} />
                <span className="text-sm font-medium text-char-800">{opt.name}</span>
                {opt.soldOut && <Badge variant="soldout">Sold Out</Badge>}
              </span>
              {opt.priceMinor > 0 && <span className="text-sm text-char-500">+{formatMoney(opt.priceMinor)}</span>}
            </label>
          ))}
        </RadioGroup>
      ) : (
        <div className="grid gap-2">
          {group.options.map((opt) => {
            const checked = selected.includes(opt.id);
            const disabled = opt.soldOut || (!checked && atMax);
            return (
              <label
                key={opt.id}
                className={cn(
                  "flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-char-200 px-4 py-3 transition-colors",
                  checked ? "border-fire-500 bg-fire-500/5" : "hover:bg-char-900/[0.03]",
                  disabled && "cursor-not-allowed opacity-50"
                )}
              >
                <span className="flex items-center gap-3">
                  <Checkbox
                    checked={checked}
                    disabled={disabled}
                    onCheckedChange={(v) => {
                      if (v) onChange([...selected, opt.id]);
                      else onChange(selected.filter((id) => id !== opt.id));
                    }}
                  />
                  <span className="text-sm font-medium text-char-800">{opt.name}</span>
                  {opt.soldOut && <Badge variant="soldout">Sold Out</Badge>}
                </span>
                {opt.priceMinor > 0 && <span className="text-sm text-char-500">+{formatMoney(opt.priceMinor)}</span>}
              </label>
            );
          })}
        </div>
      )}
    </fieldset>
  );
}
