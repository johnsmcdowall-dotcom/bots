"use client";

import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { OrderCard } from "@/components/admin/OrderCard";
import { PrepTimeControl } from "@/components/admin/PrepTimeControl";
import { getSupabaseBrowserClient } from "@/lib/supabase/browser";
import type { OrderRecord, OrderStatus } from "@/lib/types";

const COLUMNS: { status: OrderStatus; label: string }[] = [
  { status: "received", label: "New" },
  { status: "accepted", label: "Accepted" },
  { status: "preparing", label: "Preparing" },
  { status: "ready", label: "Ready" },
  { status: "completed", label: "Completed" },
  { status: "cancelled", label: "Cancelled" },
];

export function OrderBoard({
  initialOrders,
  minPrepMinutes,
  currentWaitMinutes,
}: {
  initialOrders: OrderRecord[];
  minPrepMinutes: number;
  currentWaitMinutes: number;
}) {
  const [orders, setOrders] = useState(initialOrders);
  const [refreshing, setRefreshing] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function refresh() {
    setRefreshing(true);
    try {
      const res = await fetch("/api/admin/orders", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setOrders(data.orders ?? []);
      }
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) return;

    const channel = supabase
      .channel("admin-orders")
      .on("postgres_changes", { event: "*", schema: "public", table: "orders" }, () => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(refresh, 400);
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const paidOrders = orders.filter((o) => o.paymentStatus === "paid");

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-3xl text-char-900">Live Orders</h1>
        <div className="flex items-center gap-3">
          <PrepTimeControl minPrepMinutes={minPrepMinutes} currentWaitMinutes={currentWaitMinutes} />
          <button
            onClick={refresh}
            className="flex items-center gap-1.5 rounded-full bg-char-900/5 px-3 py-1.5 text-xs font-semibold text-char-600 hover:bg-char-900/10"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 overflow-x-auto sm:grid-cols-2 xl:grid-cols-6">
        {COLUMNS.map((col) => {
          const columnOrders = paidOrders
            .filter((o) => o.status === col.status)
            .sort((a, b) => (a.requestedTime < b.requestedTime ? -1 : 1));
          return (
            <div key={col.status} className="min-w-[260px]">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-bold uppercase tracking-wide text-char-500">{col.label}</h2>
                <span className="rounded-full bg-char-900/5 px-2 py-0.5 text-xs font-semibold text-char-500">
                  {columnOrders.length}
                </span>
              </div>
              <div className="space-y-3">
                {columnOrders.map((order) => (
                  <OrderCard key={order.id} order={order} />
                ))}
                {columnOrders.length === 0 && <p className="text-xs text-char-300">No orders</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
