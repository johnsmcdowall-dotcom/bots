"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseBrowserClient } from "@/lib/supabase/browser";

/**
 * Genuine push updates for a single order, mirroring the Realtime pattern
 * already proven on the admin OrderBoard — but Broadcast, not
 * postgres_changes, since customers have no accounts to grant `orders` RLS
 * against (see broadcastOrderStatus() in lib/data/orders.ts for why).
 * Each mount subscribes to exactly one order-scoped topic, so there's no
 * way to observe another order's updates, and the channel is torn down on
 * unmount/navigation the same way OrderBoard tears its channel down.
 */
export function OrderStatusListener({ orderId, active }: { orderId: string; active: boolean }) {
  const router = useRouter();

  useEffect(() => {
    if (!active) return;
    const supabase = getSupabaseBrowserClient();
    if (!supabase) return;

    const channel = supabase
      .channel(`order-status-${orderId}`)
      .on("broadcast", { event: "status" }, () => router.refresh())
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [orderId, active, router]);

  return null;
}
