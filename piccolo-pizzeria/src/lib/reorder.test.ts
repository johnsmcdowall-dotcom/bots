import { describe, expect, it } from "vitest";
import { buildReorderPreview } from "./reorder";
import type { ModifierGroup, OrderRecord, Product } from "./types";

const margherita: Product = {
  id: "p-margherita",
  categoryId: "cat-pizzas",
  slug: "margherita",
  name: "Margherita",
  description: "Classic",
  priceMinor: 1000,
  imageUrl: "/margherita.jpg",
  dietary: [],
  allergens: [],
  soldOut: false,
  featured: false,
  popular: false,
  isNew: false,
  sortOrder: 0,
  modifierGroupIds: ["mg-extras", "mg-base"],
  stockLimited: false,
  stockRemaining: null,
};

const extras: ModifierGroup = {
  id: "mg-extras",
  name: "Extras",
  required: false,
  minSelect: 0,
  maxSelect: 3,
  options: [
    { id: "mo-honey", name: "Hot Honey", priceMinor: 100 },
    { id: "mo-jalapeno", name: "Jalapeños", priceMinor: 150, soldOut: true },
  ],
};

const base: ModifierGroup = {
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

function makeOrder(overrides: Partial<OrderRecord> = {}): OrderRecord {
  return {
    id: "order-1",
    orderNumber: "P123",
    status: "completed",
    method: "collection",
    timing: "asap",
    requestedTime: new Date().toISOString(),
    createdAt: new Date().toISOString(),
    customer: { firstName: "Jane", lastName: "Doe", phone: "07700900000", email: "jane@example.com" },
    notes: undefined,
    items: [
      {
        productId: "p-margherita",
        name: "Margherita",
        unitPriceMinor: 1100,
        quantity: 2,
        lineTotalMinor: 2200,
        modifiers: [
          { groupId: "mg-extras", optionId: "mo-honey", groupName: "Extras", optionName: "Hot Honey", priceMinor: 100 },
          { groupId: "mg-base", optionId: "mo-classic", groupName: "Choose Your Base", optionName: "Classic Woodfired Base", priceMinor: 0 },
        ],
      },
    ],
    subtotalMinor: 2200,
    deliveryFeeMinor: 0,
    discountMinor: 0,
    totalMinor: 2200,
    paymentStatus: "paid",
    ...overrides,
  };
}

describe("buildReorderPreview", () => {
  it("reconstructs an unchanged order with no notes", () => {
    const preview = buildReorderPreview(makeOrder(), [margherita], [extras, base]);
    expect(preview.lines).toHaveLength(1);
    expect(preview.lines[0].available).toBe(true);
    expect(preview.lines[0].quantity).toBe(2);
    expect(preview.lines[0].changeNotes).toEqual([]);
    expect(preview.hasChanges).toBe(false);
    expect(preview.anyAvailable).toBe(true);
  });

  it("flags a product that no longer exists", () => {
    const preview = buildReorderPreview(makeOrder(), [], [extras, base]);
    expect(preview.lines[0].available).toBe(false);
    expect(preview.lines[0].changeNotes[0]).toMatch(/no longer on the menu/);
    expect(preview.anyAvailable).toBe(false);
  });

  it("flags a product that's now sold out", () => {
    const preview = buildReorderPreview(makeOrder(), [{ ...margherita, soldOut: true }], [extras, base]);
    expect(preview.lines[0].available).toBe(false);
    expect(preview.lines[0].changeNotes[0]).toMatch(/sold out/);
  });

  it("caps quantity to remaining limited stock and explains why", () => {
    const preview = buildReorderPreview(makeOrder(), [{ ...margherita, stockLimited: true, stockRemaining: 1 }], [extras, base]);
    expect(preview.lines[0].available).toBe(true);
    expect(preview.lines[0].quantity).toBe(1);
    expect(preview.lines[0].requestedQuantity).toBe(2);
    expect(preview.lines[0].changeNotes[0]).toMatch(/Only 1 of Margherita left/);
  });

  it("drops a modifier option that no longer exists and explains why", () => {
    const groupsWithoutHoney: ModifierGroup = { ...extras, options: extras.options.filter((o) => o.id !== "mo-honey") };
    const preview = buildReorderPreview(makeOrder(), [margherita], [groupsWithoutHoney, base]);
    expect(preview.lines[0].modifiers.find((m) => m.optionId === "mo-honey")).toBeUndefined();
    expect(preview.lines[0].changeNotes.some((n) => /Hot Honey.*no longer available/.test(n))).toBe(true);
  });

  it("drops a modifier option that's now sold out", () => {
    const order = makeOrder({
      items: [
        {
          productId: "p-margherita",
          name: "Margherita",
          unitPriceMinor: 1150,
          quantity: 1,
          lineTotalMinor: 1150,
          modifiers: [
            { groupId: "mg-extras", optionId: "mo-jalapeno", groupName: "Extras", optionName: "Jalapeños", priceMinor: 150 },
            { groupId: "mg-base", optionId: "mo-classic", groupName: "Choose Your Base", optionName: "Classic Woodfired Base", priceMinor: 0 },
          ],
        },
      ],
    });
    const preview = buildReorderPreview(order, [margherita], [extras, base]);
    expect(preview.lines[0].modifiers.find((m) => m.optionId === "mo-jalapeno")).toBeUndefined();
    expect(preview.lines[0].changeNotes.some((n) => /Jalapeños is currently sold out/.test(n))).toBe(true);
  });

  it("falls back to the current default when a required selection is gone, and notes it", () => {
    const order = makeOrder({
      items: [
        {
          productId: "p-margherita",
          name: "Margherita",
          unitPriceMinor: 1250,
          quantity: 1,
          lineTotalMinor: 1250,
          modifiers: [{ groupId: "mg-base", optionId: "mo-gf", groupName: "Choose Your Base", optionName: "Gluten Free Base", priceMinor: 250 }],
        },
      ],
    });
    const baseWithoutGF: ModifierGroup = { ...base, options: base.options.filter((o) => o.id !== "mo-gf") };
    const preview = buildReorderPreview(order, [margherita], [extras, baseWithoutGF]);
    expect(preview.lines[0].available).toBe(true);
    expect(preview.lines[0].modifiers.find((m) => m.groupId === "mg-base")?.optionId).toBe("mo-classic");
    expect(preview.lines[0].changeNotes.some((n) => /defaulted to Classic Woodfired Base/.test(n))).toBe(true);
  });

  it("reports a price change without needing a modifier change", () => {
    const preview = buildReorderPreview(makeOrder(), [{ ...margherita, priceMinor: 1200 }], [extras, base]);
    expect(preview.lines[0].changeNotes.some((n) => /Price changed/.test(n))).toBe(true);
    expect(preview.hasChanges).toBe(true);
  });

  it("treats a pre-migration modifier with no optionId as unmatched", () => {
    const order = makeOrder({
      items: [
        {
          productId: "p-margherita",
          name: "Margherita",
          unitPriceMinor: 1100,
          quantity: 1,
          lineTotalMinor: 1100,
          modifiers: [
            { groupId: "", optionId: "", groupName: "Extras", optionName: "Hot Honey", priceMinor: 100 },
            { groupId: "mg-base", optionId: "mo-classic", groupName: "Choose Your Base", optionName: "Classic Woodfired Base", priceMinor: 0 },
          ],
        },
      ],
    });
    const preview = buildReorderPreview(order, [margherita], [extras, base]);
    expect(preview.lines[0].modifiers).toHaveLength(1);
    expect(preview.lines[0].changeNotes.some((n) => /Hot Honey is no longer available/.test(n))).toBe(true);
  });
});
