import { describe, expect, it } from "vitest";
import { estimatedWaitRange } from "./prep-time";

describe("estimatedWaitRange", () => {
  it("collapses to a single ~N min estimate when the kitchen isn't backed up", () => {
    expect(estimatedWaitRange({ minPrepMinutes: 15, currentWaitMinutes: 0 })).toEqual({
      lowMinutes: 15,
      highMinutes: 15,
      label: "~15 min",
    });
  });

  it("shows a range once currentWaitMinutes adds a real buffer", () => {
    expect(estimatedWaitRange({ minPrepMinutes: 15, currentWaitMinutes: 10 })).toEqual({
      lowMinutes: 15,
      highMinutes: 25,
      label: "15-25 min",
    });
  });

  it("never reports a negative floor even if minPrepMinutes is misconfigured to 0 or below", () => {
    expect(estimatedWaitRange({ minPrepMinutes: 0, currentWaitMinutes: 5 })).toEqual({
      lowMinutes: 0,
      highMinutes: 5,
      label: "0-5 min",
    });
  });
});
