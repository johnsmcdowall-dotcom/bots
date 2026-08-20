import type { Metadata } from "next";
import { OrderReview } from "@/components/order/OrderReview";
import { getBusinessSettings, getSpecialHours, getWeeklyHours } from "@/lib/data/business";

export const metadata: Metadata = {
  title: "Your Order",
  robots: { index: false },
};

export default async function OrderPage() {
  const [business, weeklyHours, specialHours] = await Promise.all([
    getBusinessSettings(),
    getWeeklyHours(),
    getSpecialHours(),
  ]);

  return <OrderReview business={business} weeklyHours={weeklyHours} specialHours={specialHours} />;
}
