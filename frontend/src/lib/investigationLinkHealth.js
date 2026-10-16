/** Normalize link-health responses; malformed data must never imply a successful repair. */
export function summarizeInvestigationLinkHealth(health) {
  if (!health || typeof health !== "object" ||
      typeof health.consistent !== "boolean" ||
      !Number.isSafeInteger(health.linked_alerts) || health.linked_alerts < 0 ||
      !Array.isArray(health.missing_from_investigation) ||
      !Array.isArray(health.stale_in_investigation) ||
      ![...health.missing_from_investigation, ...health.stale_in_investigation]
        .every((id) => typeof id === "string" && id.trim().length > 0)) {
    throw new Error("Invalid investigation link-health response");
  }
  const missing = health.missing_from_investigation.length;
  const stale = health.stale_in_investigation.length;
  // An inconsistent server flag is never upgraded to success by the client.
  const consistent = health.consistent === true && missing === 0 && stale === 0;
  return { consistent, missing, stale, linkedAlerts: health.linked_alerts };
}
