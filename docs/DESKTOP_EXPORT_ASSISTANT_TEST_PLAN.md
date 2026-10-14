# SentinelLab desktop export + assistant regression test

Status: **manual Windows runtime verification pending**. The desktop-export-checks CI workflow compiles the frontend and checks Windows Rust code; it does **not** package a working installer. Its sidecar executable and app icon are CI-only placeholders.

## Build a real Windows test installer
Use the repository's existing Windows packaging workflow, which creates the actual FastAPI sidecar and bundles genuine application assets. Build it from the **fix/desktop-event-export-search** branch, not from main. Do not distribute the CI placeholder as an installer.

## Controlled test procedure
Use the Training Lab / Synthetic workspace only. Do not delete or reset MongoDB or the WebView2 profile.

1. Record installed application version and exact source commit. Back up any investigation evidence.
2. Open **Events Explorer**; set search to a known synthetic IP, e.g. `185.220.101.5`, and note the visible event count.
3. Click **Export JSON**. Confirm native Windows Save As dialog appears; cancel and verify no file was created.
4. Repeat JSON export, save to a writable folder, and confirm JSON parses and matches the active workspace, category, severity, date range and search.
5. Repeat CSV export; check header fields, row count, quoting and UTF-8 text.
6. Verify that a denied WebView2 automatic-download permission no longer blocks the native dialog.
7. Try saving to a location without write permission. Expect a visible failure notification, not a silent no-op.
8. Open the AI assistant via the slim bottom-right edge arrow; close and reopen it. Verify the conversation remains intact.
9. Navigate Events, Alerts, Investigations, Reports, Settings and narrow-window layouts. Verify the collapsed arrow does not cover controls.
10. Confirm browser/web export still works and does not invoke the desktop native command.
11. Check the app's normal backend startup/shutdown and MongoDB persistence after restart.

## Acceptance criteria
- Both export formats work in installed Windows Tauri app without WebView2 automatic-download permission.
- Exported rows match the active filters; no cross-workspace data.
- Native save cancellation is harmless; write errors are visible.
- Assistant can be hidden to a slim arrow and reopened without losing chat history.
- No regressions in authentication, data persistence or existing desktop lifecycle.

Record screenshot/video, exact installer SHA-256 and result for each step. Do not mark runtime PASS until the actual installed app is exercised.
