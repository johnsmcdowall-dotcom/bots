"use client";

import { useTransition } from "react";
import { Bike, ShoppingBag, Phone, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { updateOrderStatusAction } from "@/lib/actions/orders";
import { formatMoney, formatOrderTime } from "@/lib/format";
import type { OrderRecord, OrderStatus } from "@/lib/types";

const NEXT_STATUS: Partial<Record<OrderStatus, { status: OrderStatus; label: string }>> = {
  received: { status: "accepted", label: "Accept" },
  accepted: { status: "preparing", label: "Start Preparing" },
  preparing: { status: "ready", label: "Mark Ready" },
  ready: { status: "completed", label: "Complete" },
};

export function OrderCard({ order }: { order: OrderRecord }) {
  const [isPending, startTransition] = useTransition();
  const next = NEXT_STATUS[order.status];
  const canCancel = order.status !== "completed" && order.status !== "cancelled";

  function advance(status: OrderStatus) {
    startTransition(async () => {
      const res = await updateOrderStatusAction(order.id, status);
      if (res?.error) toast.error(res.error);
    });
  }

  return (
    <div className="rounded-2xl border border-char-200 bg-cream-50 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-display text-lg font-semibold text-char-900">#{order.orderNumber}</p>
          <p className="text-sm text-char-600">
            {order.customer.firstName} {order.customer.lastName}
          </p>
        </div>
        <span className="shrink-0 font-display text-lg font-semibold text-fire-600">{formatOrderTime(order.requestedTime)}</span>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="flex items-center gap-1 rounded-full bg-char-900/5 px-2 py-1 font-semibold text-char-600">
          {order.method === "delivery" ? <Bike className="h-3 w-3" /> : <ShoppingBag className="h-3 w-3" />}
          {order.method === "delivery" ? "Delivery" : "Collection"}
        </span>
        <span
          className={`rounded-full px-2 py-1 font-semibold ${order.paymentStatus === "paid" ? "bg-basil-500/15 text-basil-600" : "bg-ember-400/15 text-ember-500"}`}
        >
          {order.paymentStatus === "paid" ? "Paid" : "Payment " + order.paymentStatus}
        </span>
        <a href={`tel:${order.customer.phone}`} className="flex items-center gap-1 text-char-500 hover:text-char-900">
          <Phone className="h-3 w-3" /> {order.customer.phone}
        </a>
      </div>

      <ul className="mt-3 space-y-1.5 border-t border-char-200 pt-3 text-sm">
        {order.items.map((item, idx) => (
          <li key={idx}>
            <span className="font-semibold text-char-800">
              {item.quantity}× {item.name}
            </span>
            {item.modifiers.length > 0 && (
              <span className="block text-xs text-char-400">{item.modifiers.map((m) => m.optionName).join(", ")}</span>
            )}
            {item.notes && <span className="block text-xs italic text-char-400">&ldquo;{item.notes}&rdquo;</span>}
          </li>
        ))}
      </ul>

      {order.notes && <p className="mt-2 rounded-lg bg-ember-400/10 p-2 text-xs text-ember-600">Note: {order.notes}</p>}

      <div className="mt-3 flex items-center justify-between border-t border-char-200 pt-3">
        <span className="font-display text-base font-semibold text-char-900">{formatMoney(order.totalMinor)}</span>
        <div className="flex gap-2">
          {canCancel && (
            <Button size="sm" variant="ghost" disabled={isPending} onClick={() => advance("cancelled")} aria-label="Cancel order">
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
          {next && (
            <Button size="sm" disabled={isPending} onClick={() => advance(next.status)}>
              {next.label}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
