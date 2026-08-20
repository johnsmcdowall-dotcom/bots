import { describe, expect, it } from "vitest";
import { calculateOrder, PricingError, type PricingDeps } from "./pricing";
import type { ModifierGroup, Product } from "./types";

const margherita: Product = {
  id: "p-margherita",
  categoryId: "cat-pizzas",
  slug: "margherita",
  name: "Margherita",
  description: "Classic",
  priceMinor: 1000,
  imageUrl: "",
  dietary: [],
  allergens: [],
  soldOut: false,
  featured: false,
  popular: false,
  isNew: false,
  sortOrder: 0,
  modifierGroupIds: ["mg-extras"],
};

const soldOutPizza: Product = { ...margherita, id: "p-soldout", slug: "soldout", name: "Sold Out Pizza", soldOut: true };

const extras: ModifierGroup = {
  id: "mg-extras",
  name: "Extras",
  required: false,
  minSelect: 0,
  maxSelect: 3,
  options: [
    { id: "mo-honey", name: "Hot Honey", priceMinor: 100 },
    { id: "mo-jalapeno", name: "Jalapeños", priceMinor: 100, soldOut: true },
  ],
};

const requiredBase: ModifierGroup = {
  id: "mg-base",
  name: "Choose Your Base",
  required: true,
  minSelect: 1,
  maxSelect: 1,
  options: [
    { id: "mo-classic", name: "Classic Woodfired Base", priceMinor: 0, isDefault: true },
    { id: "mo-gf", name: "Gluten Free Base", priceMinor: 250 },
  ],
};

const withRequiredBase: Product = { ...margherita, id: "p-withbase", slug: "withbase", modifierGroupIds: ["mg-base"] };

const deps: PricingDeps = {
  products: [margherita, soldOutPizza, withRequiredBase],
  modifierGroups: [extras, requiredBase],
  deliveryZones: [
    { id: "dz-1", postcodePrefixes: ["TS18"], feeMinor: 250, minOrderMinor: 1500, freeDeliveryThresholdMinor: 3500, estimatedMinutes: 35 },
  ],
  promoCodes: [
    { id: "promo-1", code: "WELCOME10", type: "percentage", value: 10, minBasketMinor: 500, timesUsed: 0, active: true },
    { id: "promo-2", code: "EXPIRED", type: "fixed", value: 500, minBasketMinor: 0, timesUsed: 0, active: true, endsAt: "2020-01-01T00:00:00Z" },
    { id: "promo-3", code: "MAXEDOUT", type: "fixed", value: 500, minBasketMinor: 0, timesUsed: 5, usageLimit: 5, active: true },
  ],
};

describe("calculateOrder", () => {
  it("prices a simple line item and carries the real product id through (Stage 1 fix)", () => {
    const result = calculateOrder({ lines: [{ productId: "p-margherita", quantity: 2, modifierOptionIds: [] }], method: "collection" }, deps);
    expect(result.subtotalMinor).toBe(2000);
    expect(result.totalMinor).toBe(2000);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].productId).toBe("p-margherita");
    expect(result.items[0].quantity).toBe(2);
  });

  it("adds modifier prices into the line total", () => {
    const result = calculateOrder(
      { lines: [{ productId: "p-margherita", quantity: 1, modifierOptionIds: ["mo-honey"] }], method: "collection" },
      deps
    );
    expect(result.items[0].unitPriceMinor).toBe(1100);
    expect(result.items[0].modifiers).toEqual([{ groupName: "Extras", optionName: "Hot Honey", priceMinor: 100 }]);
  });

  it("rejects a sold-out product even if the client still thinks it's available", () => {
    expect(() => calculateOrder({ lines: [{ productId: "p-soldout", quantity: 1, modifierOptionIds: [] }], method: "collection" }, deps)).toThrow(
      PricingError
    );
  });

  it("rejects a sold-out modifier option", () => {
    expect(() =>
      calculateOrder({ lines: [{ productId: "p-margherita", quantity: 1, modifierOptionIds: ["mo-jalapeno"] }], method: "collection" }, deps)
    ).toThrowError(/currently sold out/);
  });

  it("rejects a missing required modifier group", () => {
    expect(() => calculateOrder({ lines: [{ productId: "p-withbase", quantity: 1, modifierOptionIds: [] }], method: "collection" }, deps)).toThrowError(
      /choose an option/i
    );
  });

  it("rejects an out-of-range quantity", () => {
    expect(() =>
      calculateOrder({ lines: [{ productId: "p-margherita", quantity: 0, modifierOptionIds: [] }], method: "collection" }, deps)
    ).toThrow(PricingError);
    expect(() =>
      calculateOrder({ lines: [{ productId: "p-margherita", quantity: 21, modifierOptionIds: [] }], method: "collection" }, deps)
    ).toThrow(PricingError);
  });

  it("rejects a product id that no longer exists (never trusts the client)", () => {
    expect(() =>
      calculateOrder({ lines: [{ productId: "does-not-exist", quantity: 1, modifierOptionIds: [] }], method: "collection" }, deps)
    ).toThrowError(/no longer exists/);
  });

  it("applies a percentage promo code", () => {
    const result = calculateOrder(
      { lines: [{ productId: "p-margherita", quantity: 1, modifierOptionIds: [] }], method: "collection", promoCode: "welcome10" },
      deps
    );
    expect(result.discountMinor).toBe(100);
    expect(result.totalMinor).toBe(900);
    expect(result.promoCode).toBe("WELCOME10");
  });

  it("rejects an expired promo code", () => {
    expect(() =>
      calculateOrder({ lines: [{ productId: "p-margherita", quantity: 1, modifierOptionIds: [] }], method: "collection", promoCode: "EXPIRED" }, deps)
    ).toThrowError(/expired/);
  });

  it("rejects a promo code at its usage limit", () => {
    expect(() =>
      calculateOrder({ lines: [{ productId: "p-margherita", quantity: 1, modifierOptionIds: [] }], method: "collection", promoCode: "MAXEDOUT" }, deps)
    ).toThrowError(/usage limit/);
  });

  it("rejects an unknown promo code", () => {
    expect(() =>
      calculateOrder({ lines: [{ productId: "p-margherita", quantity: 1, modifierOptionIds: [] }], method: "collection", promoCode: "NOPE" }, deps)
    ).toThrowError(/isn't valid/);
  });

  it("calculates delivery fees and enforces minimum order", () => {
    expect(() =>
      calculateOrder({ lines: [{ productId: "p-margherita", quantity: 1, modifierOptionIds: [] }], method: "delivery", postcode: "TS18 1AB" }, deps)
    ).toThrowError(/minimum order/i);

    const result = calculateOrder(
      { lines: [{ productId: "p-margherita", quantity: 2, modifierOptionIds: [] }], method: "delivery", postcode: "TS18 1AB" },
      deps
    );
    expect(result.deliveryFeeMinor).toBe(250);
    expect(result.totalMinor).toBe(2250);
  });

  it("waives the delivery fee above the free-delivery threshold", () => {
    const result = calculateOrder(
      { lines: [{ productId: "p-margherita", quantity: 4, modifierOptionIds: [] }], method: "delivery", postcode: "TS18 1AB" },
      deps
    );
    expect(result.deliveryFeeMinor).toBe(0);
  });

  it("rejects delivery outside the configured postcode zones", () => {
    expect(() =>
      calculateOrder({ lines: [{ productId: "p-margherita", quantity: 1, modifierOptionIds: [] }], method: "delivery", postcode: "AB1 2CD" }, deps)
    ).toThrowError(/outside our delivery area/);
  });

  it("rejects an empty basket", () => {
    expect(() => calculateOrder({ lines: [], method: "collection" }, deps)).toThrow(PricingError);
  });
});
