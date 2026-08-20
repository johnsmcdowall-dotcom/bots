import { isSoldOut } from "./product";
import type { Product, UpsellRule } from "./types";

/**
 * Rule-based only — no ML, no purchase history. An admin maps a trigger
 * (one product, or an entire category) to suggested products; this just
 * matches the current basket against those rules and returns real,
 * server-priced Product records (never a name/price snapshot from when the
 * rule was created) for whatever's eligible right now.
 */
export function computeUpsellSuggestions(
  basketProductIds: string[],
  rules: UpsellRule[],
  products: Product[],
  maxSuggestions = 4
): Product[] {
  const basketProducts = basketProductIds
    .map((id) => products.find((p) => p.id === id))
    .filter((p): p is Product => Boolean(p));
  const basketIdSet = new Set(basketProductIds);
  const basketCategoryIds = new Set(basketProducts.map((p) => p.categoryId));

  const matchingRules = rules
    .filter((rule) =>
      rule.triggerType === "product"
        ? Boolean(rule.triggerProductId && basketIdSet.has(rule.triggerProductId))
        : Boolean(rule.triggerCategoryId && basketCategoryIds.has(rule.triggerCategoryId))
    )
    .sort((a, b) => a.sortOrder - b.sortOrder);

  const seen = new Set<string>();
  const suggestions: Product[] = [];
  for (const rule of matchingRules) {
    if (suggestions.length >= maxSuggestions) break;
    if (seen.has(rule.suggestedProductId)) continue;
    if (basketIdSet.has(rule.suggestedProductId)) continue;
    const product = products.find((p) => p.id === rule.suggestedProductId);
    if (!product || isSoldOut(product)) continue;
    seen.add(rule.suggestedProductId);
    suggestions.push(product);
  }
  return suggestions;
}
