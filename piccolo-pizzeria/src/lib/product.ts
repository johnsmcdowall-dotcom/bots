import type { Product } from "./types";

/** True when a customer cannot order this product right now, whether marked sold out directly or out of tracked stock. */
export function isSoldOut(product: Pick<Product, "soldOut" | "stockLimited" | "stockRemaining">): boolean {
  if (product.soldOut) return true;
  if (product.stockLimited && (product.stockRemaining ?? 0) <= 0) return true;
  return false;
}

/** "Only N left" label, only for products with genuinely configured limited stock — never fabricated urgency. */
export function lowStockLabel(product: Pick<Product, "stockLimited" | "stockRemaining">): string | null {
  if (!product.stockLimited) return null;
  const remaining = product.stockRemaining ?? 0;
  if (remaining <= 0) return null;
  return `Only ${remaining} left`;
}
