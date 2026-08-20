import { isSoldOut } from "./product";
import { formatMoney } from "./format";
import type { ModifierGroup, OrderItemRecord, OrderRecord, Product } from "./types";

export interface ReorderLineModifier {
  groupId: string;
  groupName: string;
  optionId: string;
  optionName: string;
  priceMinor: number;
}

export interface ReorderLine {
  productId: string;
  name: string;
  imageUrl: string;
  quantity: number;
  requestedQuantity: number;
  unitPriceMinor: number;
  modifiers: ReorderLineModifier[];
  notes?: string;
  available: boolean;
  changeNotes: string[];
}

export interface ReorderPreview {
  orderId: string;
  orderNumber: string;
  lines: ReorderLine[];
  hasChanges: boolean;
  anyAvailable: boolean;
}

/**
 * Re-derives a past order against the *current* catalogue, item by item, so
 * "Order Again" can never silently add something that isn't actually
 * available or charge a stale price. Pure/deterministic (no I/O) so it's
 * unit-testable the same way calculateOrder() is — the server action that
 * calls this only adds the getOrderById/getProducts/getModifierGroups I/O.
 */
export function buildReorderPreview(order: OrderRecord, products: Product[], modifierGroups: ModifierGroup[]): ReorderPreview {
  const lines = order.items.map((item) => buildLine(item, products, modifierGroups));
  return {
    orderId: order.id,
    orderNumber: order.orderNumber,
    lines,
    hasChanges: lines.some((l) => !l.available || l.changeNotes.length > 0),
    anyAvailable: lines.some((l) => l.available),
  };
}

function buildLine(item: OrderItemRecord, products: Product[], modifierGroups: ModifierGroup[]): ReorderLine {
  const base: Pick<ReorderLine, "productId" | "name" | "requestedQuantity" | "notes"> = {
    productId: item.productId,
    name: item.name,
    requestedQuantity: item.quantity,
    notes: item.notes,
  };

  const product = products.find((p) => p.id === item.productId);
  if (!product) {
    return { ...base, imageUrl: "", quantity: 0, unitPriceMinor: 0, modifiers: [], available: false, changeNotes: [`${item.name} is no longer on the menu.`] };
  }

  if (isSoldOut(product)) {
    return { ...base, name: product.name, imageUrl: product.imageUrl, quantity: 0, unitPriceMinor: 0, modifiers: [], available: false, changeNotes: [`${product.name} is currently sold out.`] };
  }

  let quantity = item.quantity;
  const changeNotes: string[] = [];
  if (product.stockLimited) {
    const remaining = product.stockRemaining ?? 0;
    if (remaining < quantity) {
      quantity = remaining;
      changeNotes.push(`Only ${remaining} of ${product.name} left — quantity reduced from ${item.quantity}.`);
    }
  }
  if (quantity <= 0) {
    return { ...base, name: product.name, imageUrl: product.imageUrl, quantity: 0, unitPriceMinor: 0, modifiers: [], available: false, changeNotes: [`${product.name} is currently sold out.`] };
  }

  const groups = modifierGroups.filter((g) => product.modifierGroupIds.includes(g.id));
  const kept: ReorderLineModifier[] = [];
  for (const mod of item.modifiers) {
    const group = groups.find((g) => g.id === mod.groupId);
    const option = group?.options.find((o) => o.id === mod.optionId);
    if (!mod.optionId || !group || !option) {
      changeNotes.push(`${mod.optionName} is no longer available and was removed.`);
      continue;
    }
    if (option.soldOut) {
      changeNotes.push(`${option.name} is currently sold out and was removed.`);
      continue;
    }
    kept.push({ groupId: group.id, groupName: group.name, optionId: option.id, optionName: option.name, priceMinor: option.priceMinor });
  }

  // A required group that lost its only selected option needs a stand-in so
  // the line stays orderable — fall back to the group's current default,
  // same as a fresh ProductModal visit would preselect.
  for (const group of groups) {
    if (!group.required) continue;
    if (kept.some((m) => m.groupId === group.id)) continue;
    const fallback = group.options.find((o) => o.isDefault && !o.soldOut) ?? group.options.find((o) => !o.soldOut);
    if (!fallback) {
      return {
        ...base,
        name: product.name,
        imageUrl: product.imageUrl,
        quantity: 0,
        unitPriceMinor: 0,
        modifiers: [],
        available: false,
        changeNotes: [`${product.name} can't be ordered right now — no option is available for "${group.name}".`],
      };
    }
    kept.push({ groupId: group.id, groupName: group.name, optionId: fallback.id, optionName: fallback.name, priceMinor: fallback.priceMinor });
    changeNotes.push(`"${group.name}" defaulted to ${fallback.name}.`);
  }

  const unitPriceMinor = product.priceMinor + kept.reduce((sum, m) => sum + m.priceMinor, 0);
  if (unitPriceMinor !== item.unitPriceMinor) {
    changeNotes.push(`Price changed to ${formatMoney(unitPriceMinor)} (was ${formatMoney(item.unitPriceMinor)}).`);
  }

  return {
    productId: product.id,
    name: product.name,
    imageUrl: product.imageUrl,
    quantity,
    requestedQuantity: item.quantity,
    unitPriceMinor,
    modifiers: kept,
    notes: item.notes,
    available: true,
    changeNotes,
  };
}
