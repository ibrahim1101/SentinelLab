# Testing History

## 2026-10-09 — Iteration 1 (testing agent)
- **Backend:** 26/26 pytest passed — auth, RBAC, dashboard, events, rules, backtest, alerts (status/comment/assign), threat hunting, source create+ingest+detection, investigations (notes/tasks/SHA256 evidence chain), reports generate+download JSON/CSV, notifications, global search, settings, admin RBAC.
- **Frontend:** ~98% — login, overview (KPIs + synthetic banner), events + 4-tab detail modal, alerts + detail (ai-explain/status/assign/comment), rules (toggles + new rule), hunting (query+run), sources (add), investigations, reports (generate + history + JSON/CSV download), settings (6 tabs + demo toggle + reset), topbar (global search, workspace selector Production/Training Lab, notifications). Workspace switch verified.
- **Detection validated as genuine:** engine produced 8 alerts (brute force, password spraying, port scan, suspicious PowerShell, IOC match) from seeded synthetic telemetry — not hardcoded.
- **Issues:** 1 LOW — dev-only React console warning `<span> child of <option>` from platform instrumentation (not app code; harmless in prod). No critical/minor backend issues.
- **Artifacts:** /app/backend/tests/test_sentinellab_api.py, /app/test_reports/iteration_1.json.
- **Result:** retest_needed = false.
