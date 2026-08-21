import { describe, expect, it } from "vitest";
import { formatOrderDateTime, formatOrderTime } from "./format";

// Order times are always meant in Europe/London, regardless of which
// timezone the server (or a viewer's browser) happens to run in — these
// pin that down explicitly so a missing timeZone option can never regress
// silently for the ~7 months of the year British Summer Time is active.
describe("formatOrderTime", () => {
  it("shows the correct London wall-clock hour during BST, not the raw UTC hour", () => {
    // 17:00 UTC in August is 18:00 BST — a customer's order for "6pm" must read 18:00, not 17:00.
    expect(formatOrderTime("2026-08-21T17:00:00.000Z")).toBe("18:00");
  });

  it("matches UTC exactly during GMT (winter), when there's no offset", () => {
    expect(formatOrderTime("2026-01-15T18:00:00.000Z")).toBe("18:00");
  });
});

describe("formatOrderDateTime", () => {
  it("shows the correct London calendar day and hour near a UTC midnight rollover during BST", () => {
    // 23:30 UTC on the 20th is 00:30 BST on the 21st — a different day.
    const result = formatOrderDateTime("2026-08-20T23:30:00.000Z");
    expect(result).toContain("21 Aug");
    expect(result).toContain("0:30");
  });
});
