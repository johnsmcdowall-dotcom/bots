import { describe, expect, it } from "vitest";
import { isSoldOut, lowStockLabel } from "./product";

describe("isSoldOut", () => {
  it("is true when explicitly marked sold out", () => {
    expect(isSoldOut({ soldOut: true, stockLimited: false, stockRemaining: null })).toBe(true);
  });
  it("is true when stock-limited and out of stock", () => {
    expect(isSoldOut({ soldOut: false, stockLimited: true, stockRemaining: 0 })).toBe(true);
  });
  it("is false when stock-limited with stock remaining", () => {
    expect(isSoldOut({ soldOut: false, stockLimited: true, stockRemaining: 3 })).toBe(false);
  });
  it("is false for an ordinary unlimited product", () => {
    expect(isSoldOut({ soldOut: false, stockLimited: false, stockRemaining: null })).toBe(false);
  });
});

describe("lowStockLabel", () => {
  it("returns null for unlimited products (never fake urgency)", () => {
    expect(lowStockLabel({ stockLimited: false, stockRemaining: null })).toBeNull();
  });
  it("returns null once stock hits zero (that's sold out, not low stock)", () => {
    expect(lowStockLabel({ stockLimited: true, stockRemaining: 0 })).toBeNull();
  });
  it("returns the real remaining count for a genuinely limited item", () => {
    expect(lowStockLabel({ stockLimited: true, stockRemaining: 6 })).toBe("Only 6 left");
  });
});
