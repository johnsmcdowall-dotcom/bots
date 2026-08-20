import { describe, expect, it } from "vitest";
import { pointsForOrder } from "./loyalty";

describe("pointsForOrder", () => {
  it("awards 1 point per whole pound spent", () => {
    expect(pointsForOrder(1000)).toBe(10);
  });

  it("floors partial pounds rather than rounding up", () => {
    expect(pointsForOrder(1099)).toBe(10);
  });

  it("awards zero points for an order under a pound", () => {
    expect(pointsForOrder(50)).toBe(0);
  });
});
