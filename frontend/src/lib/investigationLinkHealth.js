/** Normalize the link-health response and decide whether repair actually succeeded. */
export function summarizeInvestigationLinkHealth(health) {
  if (!health || typeof health !== "object" ||
      !Array.isArray(health.missing_from_investigation) ||
      !Array.isArray(health.stale_in_investigation) ||
      typeof health.linked_alerts !== "number") {
    throw new Error("Invalid investigation link-health response");
  }
  const missing = health.missing_from_investigation.length;
  const stale = health.stale_in_investigation.length;
  // Never trust a contradictory 'consistent' flag on its own.
  const consistent = health.consistent === true && missing === 0 && stale === 0;
  return { consistent, missing, stale, linkedAlerts: health.linked_alerts };
}
