import { summarizeInvestigationLinkHealth } from "./investigationLinkHealth";

describe("investigation link-health response validation", () => {
  test("accepts verified consistent links", () => {
    expect(summarizeInvestigationLinkHealth({
      consistent: true, linked_alerts: 2,
      missing_from_investigation: [], stale_in_investigation: [],
    })).toEqual({ consistent: true, linkedAlerts: 2, missing: 0, stale: 0 });
  });

  test("reports missing and stale links", () => {
    expect(summarizeInvestigationLinkHealth({
      consistent: false, linked_alerts: 3,
      missing_from_investigation: ["a"], stale_in_investigation: ["b", "c"],
    })).toEqual({ consistent: false, linkedAlerts: 3, missing: 1, stale: 2 });
  });

  test("never reports success for a contradictory server response", () => {
    expect(summarizeInvestigationLinkHealth({
      consistent: true, linked_alerts: 1,
      missing_from_investigation: ["a"], stale_in_investigation: [],
    }).consistent).toBe(false);
  });

  test.each([
    { consistent: true, linked_alerts: -1, missing_from_investigation: [], stale_in_investigation: [] },
    { consistent: true, linked_alerts: 1.5, missing_from_investigation: [], stale_in_investigation: [] },
    { consistent: true, linked_alerts: NaN, missing_from_investigation: [], stale_in_investigation: [] },
    { consistent: "true", linked_alerts: 1, missing_from_investigation: [], stale_in_investigation: [] },
    { consistent: true, linked_alerts: 1, missing_from_investigation: [null], stale_in_investigation: [] },
    { consistent: true, linked_alerts: 1, missing_from_investigation: [], stale_in_investigation: [" "] },
  ])("rejects malformed integrity data: %p", (value) => {
    expect(() => summarizeInvestigationLinkHealth(value)).toThrow(
      "Invalid investigation link-health response");
  });

  test.each([null, {}, { consistent: true, linked_alerts: 1 },
    { consistent: true, linked_alerts: "1",
      missing_from_investigation: [], stale_in_investigation: [] }])(
    "rejects invalid responses: %p", (value) => {
      expect(() => summarizeInvestigationLinkHealth(value)).toThrow(
        "Invalid investigation link-health response");
    });
});
