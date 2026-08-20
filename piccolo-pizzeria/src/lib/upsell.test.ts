import { describe, expect, it } from "vitest";
import { computeUpsellSuggestions } from "./upsell";
import type { Product, UpsellRule } from "./types";

function makeProduct(overrides: Partial<Product>): Product {
  return {
    id: "p-x",
    categoryId: "cat-x",
    slug: "x",
    name: "X",
    description: "",
    priceMinor: 100,
    imageUrl: "",
    dietary: [],
    allergens: [],
    soldOut: false,
    featured: false,
    popular: false,
    isNew: false,
    sortOrder: 0,
    modifierGroupIds: [],
    stockLimited: false,
    stockRemaining: null,
    ...overrides,
  };
}

const pizza = makeProduct({ id: "p-margherita", categoryId: "cat-pizzas", name: "Margherita" });
const garlicMayo = makeProduct({ id: "p-dip-garlic-mayo", categoryId: "cat-dips", name: "Garlic Mayo" });
const coke = makeProduct({ id: "p-coke", categoryId: "cat-drinks", name: "Coke" });
const soldOutDip = makeProduct({ id: "p-dip-soldout", categoryId: "cat-dips", name: "Sold Out Dip", soldOut: true });

const products = [pizza, garlicMayo, coke, soldOutDip];

const categoryRule: UpsellRule = {
  id: "r1",
  triggerType: "category",
  triggerProductId: null,
  triggerCategoryId: "cat-pizzas",
  suggestedProductId: "p-dip-garlic-mayo",
  sortOrder: 0,
};

const productRule: UpsellRule = {
  id: "r2",
  triggerType: "product",
  triggerProductId: "p-margherita",
  triggerCategoryId: null,
  suggestedProductId: "p-coke",
  sortOrder: 1,
};

describe("computeUpsellSuggestions", () => {
  it("matches a category-trigger rule against a basket product's category", () => {
    const result = computeUpsellSuggestions(["p-margherita"], [categoryRule], products);
    expect(result.map((p) => p.id)).toEqual(["p-dip-garlic-mayo"]);
  });

  it("matches a product-trigger rule against the exact product id", () => {
    const result = computeUpsellSuggestions(["p-margherita"], [productRule], products);
    expect(result.map((p) => p.id)).toEqual(["p-coke"]);
  });

  it("combines multiple matching rules, deduped and ordered by sort_order", () => {
    const result = computeUpsellSuggestions(["p-margherita"], [productRule, categoryRule], products);
    expect(result.map((p) => p.id)).toEqual(["p-dip-garlic-mayo", "p-coke"]);
  });

  it("excludes a suggestion that's sold out", () => {
    const soldOutRule: UpsellRule = { ...categoryRule, suggestedProductId: "p-dip-soldout" };
    const result = computeUpsellSuggestions(["p-margherita"], [soldOutRule], products);
    expect(result).toEqual([]);
  });

  it("excludes a suggestion already in the basket", () => {
    const result = computeUpsellSuggestions(["p-margherita", "p-dip-garlic-mayo"], [categoryRule], products);
    expect(result).toEqual([]);
  });

  it("returns nothing when no rule matches the basket", () => {
    const result = computeUpsellSuggestions(["p-dip-garlic-mayo"], [categoryRule, productRule], products);
    expect(result).toEqual([]);
  });

  it("caps the number of suggestions", () => {
    const manyRules: UpsellRule[] = products
      .filter((p) => p.id !== "p-margherita")
      .map((p, i) => ({ id: `gen-${i}`, triggerType: "product", triggerProductId: "p-margherita", triggerCategoryId: null, suggestedProductId: p.id, sortOrder: i }));
    const result = computeUpsellSuggestions(["p-margherita"], manyRules, products, 2);
    expect(result).toHaveLength(2);
  });
});
