"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import { Plus, Trash2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { createUpsellRuleAction, deleteUpsellRuleAction } from "@/lib/actions/upsell";
import type { Category, Product, UpsellRule } from "@/lib/types";

export function UpsellEditor({ rules, categories, products }: { rules: UpsellRule[]; categories: Category[]; products: Product[] }) {
  const [items, setItems] = useState(rules);
  const [triggerType, setTriggerType] = useState<"product" | "category">("category");
  const [triggerId, setTriggerId] = useState("");
  const [suggestedProductId, setSuggestedProductId] = useState("");
  const [isPending, startTransition] = useTransition();

  function nameFor(rule: UpsellRule) {
    const trigger =
      rule.triggerType === "category"
        ? categories.find((c) => c.id === rule.triggerCategoryId)?.name
        : products.find((p) => p.id === rule.triggerProductId)?.name;
    const suggested = products.find((p) => p.id === rule.suggestedProductId)?.name;
    return { trigger: trigger ?? "Unknown", suggested: suggested ?? "Unknown" };
  }

  function handleCreate() {
    if (!triggerId || !suggestedProductId) {
      toast.error("Choose a trigger and a suggested product");
      return;
    }
    startTransition(async () => {
      const res = await createUpsellRuleAction({ triggerType, triggerId, suggestedProductId });
      if (res?.error) {
        toast.error(res.error);
        return;
      }
      toast.success("Upsell rule added");
      setTriggerId("");
      setSuggestedProductId("");
      // The new row's real id comes back on next server refetch; a
      // placeholder keeps the list responsive without an extra round trip.
      const newRule: UpsellRule = {
        id: `pending-${Date.now()}`,
        triggerType,
        triggerProductId: triggerType === "product" ? triggerId : null,
        triggerCategoryId: triggerType === "category" ? triggerId : null,
        suggestedProductId,
        sortOrder: items.length,
      };
      setItems((prev) => [...prev, newRule]);
    });
  }

  function handleDelete(rule: UpsellRule) {
    setItems((prev) => prev.filter((r) => r.id !== rule.id));
    startTransition(async () => {
      const res = await deleteUpsellRuleAction(rule.id);
      if (res?.error) {
        toast.error(res.error);
        setItems((prev) => [...prev, rule]);
      }
    });
  }

  const triggerOptions = triggerType === "category" ? categories.map((c) => ({ id: c.id, name: c.name })) : products.map((p) => ({ id: p.id, name: p.name }));

  return (
    <div>
      <h1 className="font-display text-3xl text-char-900">Smart Upsells</h1>
      <p className="mt-1.5 max-w-2xl text-sm text-char-500">
        When a customer&apos;s basket matches a trigger below, we suggest the linked product once per visit — server-priced, never sold-out, never something
        already in their basket.
      </p>

      <div className="mt-6 rounded-2xl border border-char-200 bg-cream-50 p-5">
        <h2 className="text-sm font-bold uppercase tracking-wide text-char-500">Add a rule</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-[auto_1fr_1fr_auto] sm:items-end">
          <div>
            <span className="text-xs font-semibold text-char-500">When basket has</span>
            <Select value={triggerType} onValueChange={(v) => { setTriggerType(v as "product" | "category"); setTriggerId(""); }}>
              <SelectTrigger className="mt-1.5 w-full sm:w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="category">Any in category</SelectItem>
                <SelectItem value="product">A specific product</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <span className="text-xs font-semibold text-char-500">{triggerType === "category" ? "Category" : "Product"}</span>
            <Select value={triggerId} onValueChange={setTriggerId}>
              <SelectTrigger className="mt-1.5">
                <SelectValue placeholder={triggerType === "category" ? "Choose category" : "Choose product"} />
              </SelectTrigger>
              <SelectContent>
                {triggerOptions.map((o) => (
                  <SelectItem key={o.id} value={o.id}>
                    {o.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <span className="text-xs font-semibold text-char-500">Suggest</span>
            <Select value={suggestedProductId} onValueChange={setSuggestedProductId}>
              <SelectTrigger className="mt-1.5">
                <SelectValue placeholder="Choose product to suggest" />
              </SelectTrigger>
              <SelectContent>
                {products.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={handleCreate} disabled={isPending} className="sm:mb-0.5">
            <Plus className="h-4 w-4" /> Add rule
          </Button>
        </div>
      </div>

      <div className="mt-6 space-y-2">
        {items.length === 0 && (
          <p className="rounded-2xl border border-dashed border-char-200 p-8 text-center text-sm text-char-400">
            No upsell rules yet — add one above to start suggesting extras.
          </p>
        )}
        {items.map((rule) => {
          const { trigger, suggested } = nameFor(rule);
          return (
            <div key={rule.id} className="flex items-center justify-between gap-3 rounded-xl border border-char-200 bg-cream-50 px-4 py-3">
              <div className="flex items-center gap-2 text-sm">
                <Sparkles className="h-3.5 w-3.5 shrink-0 text-fire-500" />
                <span className="text-char-500">{rule.triggerType === "category" ? "Basket has any" : "Basket has"}</span>
                <span className="font-semibold text-char-900">{trigger}</span>
                <span className="text-char-400">&rarr;</span>
                <span className="text-char-500">suggest</span>
                <span className="font-semibold text-char-900">{suggested}</span>
              </div>
              <Button size="icon" variant="ghost" className="h-8 w-8 shrink-0 text-char-400 hover:text-fire-600" onClick={() => handleDelete(rule)} aria-label="Delete rule">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
