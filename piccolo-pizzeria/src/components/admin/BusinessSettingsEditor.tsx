"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { updateBusinessSettingsAction } from "@/lib/actions/settings";
import type { BusinessSettings } from "@/lib/types";

export function BusinessSettingsEditor({ business }: { business: BusinessSettings }) {
  const [form, setForm] = useState(business);
  const [isPending, startTransition] = useTransition();

  function set<K extends keyof BusinessSettings>(key: K, value: BusinessSettings[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function save() {
    startTransition(async () => {
      const res = await updateBusinessSettingsAction(form);
      if (res?.error) toast.error(res.error);
      else toast.success("Settings saved");
    });
  }

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-fire-500/30 bg-fire-500/5 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-lg text-char-900">Pause Ordering</h2>
            <p className="text-sm text-char-500">Immediately stops customers from placing new orders.</p>
          </div>
          <Switch checked={form.orderingPaused} onCheckedChange={(v) => set("orderingPaused", v)} />
        </div>
        {form.orderingPaused && (
          <div className="mt-4">
            <Label htmlFor="pauseMessage">Message shown to customers</Label>
            <Textarea
              id="pauseMessage"
              className="mt-1.5"
              rows={2}
              value={form.orderingPausedMessage ?? ""}
              onChange={(e) => set("orderingPausedMessage", e.target.value)}
            />
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-basil-500/30 bg-basil-500/5 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-lg text-char-900">Tonight at Piccolo</h2>
            <p className="text-sm text-char-500">A banner shown storefront-wide — a tonight-only special, an event, anything worth flagging.</p>
          </div>
          <Switch checked={form.announcementActive} onCheckedChange={(v) => set("announcementActive", v)} />
        </div>
        {form.announcementActive && (
          <div className="mt-4">
            <Label htmlFor="announcementMessage">Message shown to customers</Label>
            <Textarea
              id="announcementMessage"
              className="mt-1.5"
              rows={2}
              placeholder="E.g. Live music from 6pm — come early for a table."
              value={form.announcementMessage ?? ""}
              onChange={(e) => set("announcementMessage", e.target.value)}
            />
          </div>
        )}
      </section>

      <section>
        <h2 className="font-display text-lg text-char-900">Order Timing</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div className="flex items-center justify-between rounded-xl border border-char-200 p-4">
            <span className="text-sm font-semibold text-char-800">ASAP orders</span>
            <Switch checked={form.asapOrdersEnabled} onCheckedChange={(v) => set("asapOrdersEnabled", v)} />
          </div>
          <div className="flex items-center justify-between rounded-xl border border-char-200 p-4">
            <span className="text-sm font-semibold text-char-800">Scheduled orders</span>
            <Switch checked={form.scheduledOrdersEnabled} onCheckedChange={(v) => set("scheduledOrdersEnabled", v)} />
          </div>
          <div className="flex items-center justify-between rounded-xl border border-char-200 p-4">
            <span className="text-sm font-semibold text-char-800">Delivery</span>
            <Switch checked={form.deliveryEnabled} onCheckedChange={(v) => set("deliveryEnabled", v)} />
          </div>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <Label htmlFor="currentWait">Current wait (minutes)</Label>
            <Input
              id="currentWait"
              type="number"
              min={0}
              className="mt-1.5"
              value={form.currentWaitMinutes}
              onChange={(e) => set("currentWaitMinutes", Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="minPrep">Minimum prep time (minutes)</Label>
            <Input
              id="minPrep"
              type="number"
              min={0}
              className="mt-1.5"
              value={form.minPrepMinutes}
              onChange={(e) => set("minPrepMinutes", Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="maxAdvance">Max advance order (days)</Label>
            <Input
              id="maxAdvance"
              type="number"
              min={0}
              className="mt-1.5"
              value={form.maxAdvanceOrderDays}
              onChange={(e) => set("maxAdvanceOrderDays", Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="slotInterval">Slot interval (minutes)</Label>
            <Input
              id="slotInterval"
              type="number"
              min={5}
              className="mt-1.5"
              value={form.slotIntervalMinutes}
              onChange={(e) => set("slotIntervalMinutes", Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="ordersPerSlot">Collection orders per slot</Label>
            <Input
              id="ordersPerSlot"
              type="number"
              min={1}
              className="mt-1.5"
              value={form.ordersPerSlot}
              onChange={(e) => set("ordersPerSlot", Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="deliveryOrdersPerSlot">Delivery orders per slot</Label>
            <Input
              id="deliveryOrdersPerSlot"
              type="number"
              min={1}
              className="mt-1.5"
              value={form.deliveryOrdersPerSlot}
              onChange={(e) => set("deliveryOrdersPerSlot", Number(e.target.value))}
            />
          </div>
        </div>
      </section>

      <section>
        <h2 className="font-display text-lg text-char-900">Business Details</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="name">Business name</Label>
            <Input id="name" className="mt-1.5" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="tagline">Tagline</Label>
            <Input id="tagline" className="mt-1.5" value={form.tagline} onChange={(e) => set("tagline", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" className="mt-1.5" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" className="mt-1.5" value={form.email} onChange={(e) => set("email", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="addressLine1">Address</Label>
            <Input id="addressLine1" className="mt-1.5" value={form.addressLine1} onChange={(e) => set("addressLine1", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="city">City</Label>
            <Input id="city" className="mt-1.5" value={form.city} onChange={(e) => set("city", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="postcode">Postcode</Label>
            <Input id="postcode" className="mt-1.5" value={form.postcode} onChange={(e) => set("postcode", e.target.value)} />
          </div>
          <div>
            <Label htmlFor="instagramUrl">Instagram URL</Label>
            <Input id="instagramUrl" className="mt-1.5" value={form.instagramUrl ?? ""} onChange={(e) => set("instagramUrl", e.target.value)} />
          </div>
        </div>
      </section>

      <Button size="lg" onClick={save} disabled={isPending}>
        {isPending ? "Saving…" : "Save Settings"}
      </Button>
    </div>
  );
}
