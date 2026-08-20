import type {
  DeliveryZone,
  ModifierGroup,
  OrderItemRecord,
  OrderMethod,
  Product,
  PromoCode,
} from "./types";

export class PricingError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "PricingError";
  }
}

export interface PriceLineInput {
  productId: string;
  quantity: number;
  modifierOptionIds: string[];
  notes?: string;
}

export interface PriceCartInput {
  lines: PriceLineInput[];
  method: OrderMethod;
  postcode?: string;
  promoCode?: string;
}

export interface PricingDeps {
  products: Product[];
  modifierGroups: ModifierGroup[];
  deliveryZones: DeliveryZone[];
  promoCodes: PromoCode[];
}

export interface PricedOrder {
  items: OrderItemRecord[];
  subtotalMinor: number;
  deliveryFeeMinor: number;
  discountMinor: number;
  totalMinor: number;
  promoCode?: string;
  deliveryZone?: DeliveryZone;
}

function normalisePostcode(postcode: string): string {
  return postcode.replace(/\s+/g, "").toUpperCase();
}

function findDeliveryZone(postcode: string, zones: DeliveryZone[]): DeliveryZone | undefined {
  const normalised = normalisePostcode(postcode);
  return zones.find((zone) => zone.postcodePrefixes.some((prefix) => normalised.startsWith(prefix.toUpperCase())));
}

/**
 * Recomputes an order's price entirely from trusted server-side data:
 * current product/modifier prices, sold-out flags, delivery zones and promo
 * rules. The client only ever supplies *selections* (product + modifier IDs
 * + quantities) — never prices or totals. Throws `PricingError` for any
 * invalid or now-unavailable selection so the caller can surface a clear
 * message instead of silently accepting a stale basket.
 */
export function calculateOrder(input: PriceCartInput, deps: PricingDeps): PricedOrder {
  if (input.lines.length === 0) {
    throw new PricingError("empty_basket", "Your basket is empty.");
  }

  const items: OrderItemRecord[] = [];
  let subtotalMinor = 0;

  for (const line of input.lines) {
    if (!Number.isInteger(line.quantity) || line.quantity < 1 || line.quantity > 20) {
      throw new PricingError("invalid_quantity", "Invalid item quantity.");
    }

    const product = deps.products.find((p) => p.id === line.productId);
    if (!product) throw new PricingError("product_not_found", "One of the items in your basket no longer exists.");
    if (product.soldOut) {
      throw new PricingError("sold_out", `${product.name} is currently sold out.`);
    }
    // Courtesy check against the last-known stock count — catches the
    // common case (someone else bought the rest since the page loaded)
    // before the customer even reaches payment. The actual guarantee
    // against overselling under concurrency is the atomic decrement at
    // payment success (see markOrderPaid / decrement_product_stock), not
    // this read, which can still be stale by the time payment completes.
    if (product.stockLimited && (product.stockRemaining ?? 0) < line.quantity) {
      throw new PricingError("insufficient_stock", `Only ${product.stockRemaining ?? 0} of ${product.name} left.`);
    }

    const groups = deps.modifierGroups.filter((g) => product.modifierGroupIds.includes(g.id));
    const selectedByGroup = new Map<string, string[]>();
    for (const optionId of line.modifierOptionIds) {
      const group = groups.find((g) => g.options.some((o) => o.id === optionId));
      if (!group) {
        throw new PricingError("invalid_modifier", `An option selected for ${product.name} is no longer available.`);
      }
      const option = group.options.find((o) => o.id === optionId)!;
      if (option.soldOut) {
        throw new PricingError("modifier_sold_out", `${option.name} is currently sold out.`);
      }
      const arr = selectedByGroup.get(group.id) || [];
      arr.push(optionId);
      selectedByGroup.set(group.id, arr);
    }

    let lineModifierTotal = 0;
    const modifierRecords: OrderItemRecord["modifiers"] = [];

    for (const group of groups) {
      const selected = selectedByGroup.get(group.id) || [];
      if (group.required && selected.length < Math.max(1, group.minSelect)) {
        throw new PricingError("modifier_required", `Please choose an option for "${group.name}" on ${product.name}.`);
      }
      if (selected.length < group.minSelect) {
        throw new PricingError("modifier_min", `Choose at least ${group.minSelect} option(s) for "${group.name}".`);
      }
      if (selected.length > group.maxSelect) {
        throw new PricingError("modifier_max", `Choose at most ${group.maxSelect} option(s) for "${group.name}".`);
      }
      for (const optionId of selected) {
        const option = group.options.find((o) => o.id === optionId)!;
        lineModifierTotal += option.priceMinor;
        modifierRecords.push({
          groupId: group.id,
          optionId: option.id,
          groupName: group.name,
          optionName: option.name,
          priceMinor: option.priceMinor,
        });
      }
    }

    const unitPriceMinor = product.priceMinor + lineModifierTotal;
    const lineTotalMinor = unitPriceMinor * line.quantity;
    subtotalMinor += lineTotalMinor;

    items.push({
      productId: product.id,
      name: product.name,
      unitPriceMinor,
      quantity: line.quantity,
      lineTotalMinor,
      notes: line.notes?.slice(0, 280),
      modifiers: modifierRecords,
    });
  }

  let deliveryFeeMinor = 0;
  let deliveryZone: DeliveryZone | undefined;
  if (input.method === "delivery") {
    if (!input.postcode) throw new PricingError("postcode_required", "A postcode is required for delivery.");
    deliveryZone = findDeliveryZone(input.postcode, deps.deliveryZones);
    if (!deliveryZone) {
      throw new PricingError("outside_delivery_area", "Sorry, that postcode is outside our delivery area.");
    }
    if (subtotalMinor < deliveryZone.minOrderMinor) {
      throw new PricingError(
        "below_minimum_order",
        `Minimum order for delivery to this area is ${(deliveryZone.minOrderMinor / 100).toFixed(2)}.`
      );
    }
    deliveryFeeMinor =
      deliveryZone.freeDeliveryThresholdMinor && subtotalMinor >= deliveryZone.freeDeliveryThresholdMinor
        ? 0
        : deliveryZone.feeMinor;
  }

  let discountMinor = 0;
  let appliedPromoCode: string | undefined;
  if (input.promoCode) {
    const promo = deps.promoCodes.find((p) => p.code.toUpperCase() === input.promoCode!.toUpperCase());
    if (!promo || !promo.active) {
      throw new PricingError("invalid_promo", "That promo code isn't valid.");
    }
    const now = new Date();
    if (promo.startsAt && now < new Date(promo.startsAt)) {
      throw new PricingError("invalid_promo", "That promo code isn't active yet.");
    }
    if (promo.endsAt && now > new Date(promo.endsAt)) {
      throw new PricingError("expired_promo", "That promo code has expired.");
    }
    if (promo.usageLimit !== undefined && promo.timesUsed >= promo.usageLimit) {
      throw new PricingError("promo_limit_reached", "That promo code has reached its usage limit.");
    }
    if (subtotalMinor < promo.minBasketMinor) {
      throw new PricingError(
        "promo_min_basket",
        `Spend ${(promo.minBasketMinor / 100).toFixed(2)} or more to use this code.`
      );
    }
    discountMinor = promo.type === "percentage" ? Math.round((subtotalMinor * promo.value) / 100) : promo.value;
    discountMinor = Math.min(discountMinor, subtotalMinor);
    appliedPromoCode = promo.code;
  }

  const totalMinor = Math.max(0, subtotalMinor + deliveryFeeMinor - discountMinor);

  return {
    items,
    subtotalMinor,
    deliveryFeeMinor,
    discountMinor,
    totalMinor,
    promoCode: appliedPromoCode,
    deliveryZone,
  };
}
