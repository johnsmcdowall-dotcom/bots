import Link from "next/link";
import { PoundSterling, ShoppingBag, Receipt, ChefHat, ArrowRight } from "lucide-react";
import { StatCard } from "@/components/admin/StatCard";
import { listOrders } from "@/lib/data/orders";
import { formatMoney, formatOrderTime } from "@/lib/format";

export default async function AdminDashboardPage() {
  const startOfDay = new Date();
  startOfDay.setHours(0, 0, 0, 0);

  const [todayOrders, awaitingPrep] = await Promise.all([
    listOrders({ since: startOfDay.toISOString() }),
    listOrders({ statuses: ["received", "accepted", "preparing"] }),
  ]);

  const paidToday = todayOrders.filter((o) => o.paymentStatus === "paid");
  const revenueToday = paidToday.reduce((sum, o) => sum + o.totalMinor, 0);
  const aov = paidToday.length > 0 ? Math.round(revenueToday / paidToday.length) : 0;

  const upcoming = awaitingPrep
    .slice()
    .sort((a, b) => (a.requestedTime < b.requestedTime ? -1 : 1))
    .slice(0, 6);

  return (
    <div>
      <h1 className="font-display text-3xl text-char-900">Dashboard</h1>
      <p className="mt-1 text-char-500">Today at a glance.</p>

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Orders Today" value={String(paidToday.length)} icon={ShoppingBag} accent="fire" />
        <StatCard label="Revenue Today" value={formatMoney(revenueToday)} icon={PoundSterling} accent="basil" />
        <StatCard label="Average Order" value={formatMoney(aov)} icon={Receipt} />
        <StatCard label="Awaiting Prep" value={String(awaitingPrep.length)} icon={ChefHat} accent="ember" />
      </div>

      <div className="mt-8 rounded-2xl border border-char-200 bg-cream-50 p-5">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg text-char-900">Upcoming Collections</h2>
          <Link href="/admin/orders" className="flex items-center gap-1 text-sm font-semibold text-fire-600 hover:underline">
            View board <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {upcoming.length === 0 ? (
          <p className="mt-4 text-sm text-char-500">Nothing in the queue right now.</p>
        ) : (
          <ul className="mt-4 divide-y divide-char-200">
            {upcoming.map((order) => (
              <li key={order.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-semibold text-char-800">
                    #{order.orderNumber} — {order.customer.firstName} {order.customer.lastName}
                  </p>
                  <p className="text-sm text-char-400">
                    {order.method === "delivery" ? "Delivery" : "Collection"} · {order.items.length} item{order.items.length === 1 ? "" : "s"}
                  </p>
                </div>
                <span className="font-display text-lg text-char-900">{formatOrderTime(order.requestedTime)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
