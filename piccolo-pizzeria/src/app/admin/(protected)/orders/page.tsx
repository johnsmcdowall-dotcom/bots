import { OrderBoard } from "@/components/admin/OrderBoard";
import { listOrders } from "@/lib/data/orders";
import { getBusinessSettings } from "@/lib/data/business";

export default async function AdminOrdersPage() {
  const [orders, business] = await Promise.all([listOrders({}), getBusinessSettings()]);
  return <OrderBoard initialOrders={orders} minPrepMinutes={business.minPrepMinutes} currentWaitMinutes={business.currentWaitMinutes} />;
}
