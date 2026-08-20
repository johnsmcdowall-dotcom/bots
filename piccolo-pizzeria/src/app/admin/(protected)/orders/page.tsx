import { OrderBoard } from "@/components/admin/OrderBoard";
import { listOrders } from "@/lib/data/orders";

export default async function AdminOrdersPage() {
  const orders = await listOrders({});
  return <OrderBoard initialOrders={orders} />;
}
