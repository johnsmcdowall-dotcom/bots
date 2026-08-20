"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { addSpecialHoursAction, deleteSpecialHoursAction, updateWeeklyHoursAction } from "@/lib/actions/hours";
import type { SpecialHours, WeeklyHours } from "@/lib/types";

const DAY_LABELS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export function OpeningHoursEditor({
  weeklyHours,
  specialHours,
}: {
  weeklyHours: WeeklyHours;
  specialHours: SpecialHours[];
}) {
  const [hours, setHours] = useState(weeklyHours);
  const [specials, setSpecials] = useState(specialHours);
  const [newSpecial, setNewSpecial] = useState({ date: "", label: "", isOpen: false, openTime: "17:00", closeTime: "21:00" });
  const [isPending, startTransition] = useTransition();

  function updateDay(day: number, patch: Partial<WeeklyHours[number]>) {
    setHours((h) => ({ ...h, [day]: { ...h[day], ...patch } }));
  }

  function saveWeekly() {
    startTransition(async () => {
      const res = await updateWeeklyHoursAction(hours);
      if (res?.error) toast.error(res.error);
      else toast.success("Opening hours saved");
    });
  }

  function addSpecial() {
    if (!newSpecial.date || !newSpecial.label) {
      toast.error("Add a date and label first");
      return;
    }
    startTransition(async () => {
      const res = await addSpecialHoursAction(newSpecial);
      if (res?.error) toast.error(res.error);
      else {
        toast.success("Added");
        setSpecials((s) => [...s, { ...newSpecial, id: crypto.randomUUID() }]);
        setNewSpecial({ date: "", label: "", isOpen: false, openTime: "17:00", closeTime: "21:00" });
      }
    });
  }

  function removeSpecial(id: string) {
    startTransition(async () => {
      const res = await deleteSpecialHoursAction(id);
      if (res?.error) toast.error(res.error);
      else setSpecials((s) => s.filter((sp) => sp.id !== id));
    });
  }

  return (
    <div className="space-y-8">
      <section>
        <h2 className="font-display text-lg font-semibold text-char-900">Weekly Hours</h2>
        <div className="mt-3 space-y-2">
          {DAY_LABELS.map((label, day) => {
            const d = hours[day];
            return (
              <div key={day} className="flex flex-wrap items-center gap-3 rounded-xl border border-char-200 p-3">
                <span className="w-24 shrink-0 text-sm font-semibold text-char-800">{label}</span>
                <Switch checked={d.isOpen} onCheckedChange={(v) => updateDay(day, { isOpen: v })} />
                {d.isOpen ? (
                  <>
                    <Input
                      type="time"
                      className="w-32"
                      value={d.openTime}
                      onChange={(e) => updateDay(day, { openTime: e.target.value })}
                    />
                    <span className="text-char-400">to</span>
                    <Input
                      type="time"
                      className="w-32"
                      value={d.closeTime}
                      onChange={(e) => updateDay(day, { closeTime: e.target.value })}
                    />
                  </>
                ) : (
                  <span className="text-sm text-char-400">Closed</span>
                )}
              </div>
            );
          })}
        </div>
        <Button size="lg" className="mt-4" onClick={saveWeekly} disabled={isPending}>
          {isPending ? "Saving…" : "Save Weekly Hours"}
        </Button>
      </section>

      <section>
        <h2 className="font-display text-lg font-semibold text-char-900">Special Dates &amp; Holidays</h2>
        <p className="mt-1 text-sm text-char-500">Override the weekly schedule for a specific date — closures, holidays or special opening times.</p>

        <div className="mt-4 space-y-2">
          {specials.map((s) => (
            <div key={s.id} className="flex items-center justify-between rounded-xl border border-char-200 p-3">
              <div>
                <p className="text-sm font-semibold text-char-800">
                  {s.date} — {s.label}
                </p>
                <p className="text-xs text-char-400">{s.isOpen ? `Open ${s.openTime}–${s.closeTime}` : "Closed"}</p>
              </div>
              <button onClick={() => removeSpecial(s.id)} className="p-2 text-char-400 hover:text-fire-600" aria-label="Remove">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
          {specials.length === 0 && <p className="text-sm text-char-400">No special dates set.</p>}
        </div>

        <div className="mt-4 grid gap-3 rounded-xl border border-dashed border-char-300 p-4 sm:grid-cols-2">
          <Input
            type="date"
            value={newSpecial.date}
            onChange={(e) => setNewSpecial((s) => ({ ...s, date: e.target.value }))}
          />
          <Input
            placeholder="Label (e.g. Christmas Day)"
            value={newSpecial.label}
            onChange={(e) => setNewSpecial((s) => ({ ...s, label: e.target.value }))}
          />
          <div className="flex items-center gap-2">
            <Switch checked={newSpecial.isOpen} onCheckedChange={(v) => setNewSpecial((s) => ({ ...s, isOpen: v }))} />
            <span className="text-sm text-char-600">{newSpecial.isOpen ? "Open" : "Closed"}</span>
          </div>
          {newSpecial.isOpen && (
            <div className="flex items-center gap-2">
              <Input type="time" value={newSpecial.openTime} onChange={(e) => setNewSpecial((s) => ({ ...s, openTime: e.target.value }))} />
              <Input type="time" value={newSpecial.closeTime} onChange={(e) => setNewSpecial((s) => ({ ...s, closeTime: e.target.value }))} />
            </div>
          )}
          <Button className="sm:col-span-2" variant="outline" onClick={addSpecial} disabled={isPending}>
            <Plus className="h-4 w-4" /> Add Special Date
          </Button>
        </div>
      </section>
    </div>
  );
}
