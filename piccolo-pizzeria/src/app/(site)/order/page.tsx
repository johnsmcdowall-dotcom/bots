import type { Metadata } from "next";
import { OrderReview } from "@/components/order/OrderReview";
import { getBusinessSettings, getSpecialHours, getWeeklyHours } from "@/lib/data/business";
import { getProducts, getUpsellRules } from "@/lib/data/menu";

export const metadata: Metadata = {
  title: "Your Order",
  robots: { index: false },
};

export default async function OrderPage() {
  const [business, weeklyHours, specialHours, products, upsellRules] = await Promise.all([
    getBusinessSettings(),
    getWeeklyHours(),
    getSpecialHours(),
    getProducts(),
    getUpsellRules(),
  ]);

  return <OrderReview business={business} weeklyHours={weeklyHours} specialHours={specialHours} products={products} upsellRules={upsellRules} />;
}
