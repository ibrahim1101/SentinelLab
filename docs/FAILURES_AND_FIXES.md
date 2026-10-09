# Failures and Fixes

Preserve history; do not delete fixed entries.

## 2026-10-09
- **server.py overwrite blocked** — create_file refused on existing file. Fix: re-ran with `overwrite=true`.
- **Detection needs timestamp diffing** — added `python-dateutil` to requirements; `detection.py` uses it for sliding-window threshold logic.
- **CORS + credentials** — wildcard origin incompatible with credentialed cookies; set `CORS_ORIGINS` to preview origin and rely on Bearer token primarily.
