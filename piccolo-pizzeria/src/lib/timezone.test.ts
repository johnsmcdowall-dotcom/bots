import { describe, expect, it } from "vitest";
import {
  addDaysToISODate,
  dayOfWeekForISODate,
  londonDateISO,
  londonDayOfWeek,
  londonHHMM,
  londonMinutesOfDay,
  londonWallTimeToUTC,
} from "./timezone";

// This whole suite exists because the server this app runs on is not
// guaranteed to be in Europe/London (Vercel and most serverless hosts
// default to UTC) — every case here is picked to fail loudly if any
// function silently reverts to using the server's own local timezone
// instead of going through Intl's Europe/London data.

describe("londonDateISO / londonMinutesOfDay / londonDayOfWeek — BST (UTC+1)", () => {
  it("reads the correct London calendar date and time near a UTC midnight rollover", () => {
    // 2026-08-20T23:30:00Z is 2026-08-21T00:30 in BST — a different day AND hour than UTC.
    const d = new Date("2026-08-20T23:30:00Z");
    expect(londonDateISO(d)).toBe("2026-08-21");
    expect(londonMinutesOfDay(d)).toBe(30); // 00:30
    expect(londonHHMM(d)).toBe("00:30");
    expect(londonDayOfWeek(d)).toBe(5); // Friday
  });
});

describe("londonDateISO / londonMinutesOfDay / londonDayOfWeek — GMT (UTC+0)", () => {
  it("matches UTC exactly in winter, when there's no offset to get wrong", () => {
    const d = new Date("2026-01-15T20:15:00Z");
    expect(londonDateISO(d)).toBe("2026-01-15");
    expect(londonMinutesOfDay(d)).toBe(20 * 60 + 15);
    expect(londonDayOfWeek(d)).toBe(4); // Thursday
  });
});

describe("addDaysToISODate / dayOfWeekForISODate", () => {
  it("adds days without being affected by DST transitions", () => {
    // 2026-03-29 is the BST spring-forward date in the UK.
    expect(addDaysToISODate("2026-03-28", 1)).toBe("2026-03-29");
    expect(addDaysToISODate("2026-03-29", 1)).toBe("2026-03-30");
  });

  it("returns the correct weekday for a plain date string", () => {
    expect(dayOfWeekForISODate("2026-08-21")).toBe(5); // Friday
    expect(dayOfWeekForISODate("2026-01-15")).toBe(4); // Thursday
  });
});

describe("londonWallTimeToUTC", () => {
  it("converts a BST wall-clock time to the correct UTC instant (London is 1h ahead)", () => {
    // A customer picking the 18:00 slot in August means 18:00 BST = 17:00 UTC.
    const result = londonWallTimeToUTC("2026-08-21", "18:00");
    expect(result.toISOString()).toBe("2026-08-21T17:00:00.000Z");
  });

  it("converts a GMT wall-clock time to the correct UTC instant (no offset)", () => {
    // A customer picking the 18:00 slot in January means 18:00 GMT = 18:00 UTC.
    const result = londonWallTimeToUTC("2026-01-15", "18:00");
    expect(result.toISOString()).toBe("2026-01-15T18:00:00.000Z");
  });

  it("round-trips: converting then reading back in London time returns the original wall-clock time", () => {
    const bst = londonWallTimeToUTC("2026-07-04", "19:30");
    expect(londonHHMM(bst)).toBe("19:30");
    expect(londonDateISO(bst)).toBe("2026-07-04");

    const gmt = londonWallTimeToUTC("2026-12-24", "17:45");
    expect(londonHHMM(gmt)).toBe("17:45");
    expect(londonDateISO(gmt)).toBe("2026-12-24");
  });

  it("handles a date right after the BST spring-forward transition correctly", () => {
    // Clocks go forward at 1am on 2026-03-29 — 02:30 that day is BST (UTC+1).
    const result = londonWallTimeToUTC("2026-03-29", "14:00");
    expect(result.toISOString()).toBe("2026-03-29T13:00:00.000Z");
  });

  it("handles a date right after the BST-to-GMT autumn transition correctly", () => {
    // Clocks go back at 2am on 2026-10-25 — by afternoon it's GMT (UTC+0) again.
    const result = londonWallTimeToUTC("2026-10-25", "14:00");
    expect(result.toISOString()).toBe("2026-10-25T14:00:00.000Z");
  });
});
