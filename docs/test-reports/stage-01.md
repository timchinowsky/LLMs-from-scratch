# Stage 1 — synthetic persistent transcript workflow

Real FastAPI/SQLite backend and Chromium browser; no simulated audio hardware claim.

Automated suite: 16 passed. Covers out-of-order capture completion, duplicate stable
IDs, conflicting repeats, snapshot/replay race, resync, bounded event pagination,
search, Unicode/HTML-like data, history pagination, acknowledgement, local mute and
capture generation, restart persistence, session invalidation, ephemeral partials,
invalid configuration/payloads, unauthorized access, forged identity headers,
CSRF/origin/host rejection, low-disk and failed writes, NDJSON export, SQLite backup
integrity and restore instance identity. One upstream Starlette/AnyIO deprecation
warning; it does not fail the suite.

Browser: successful first run against running server at 1280x1000 and 390x844,
including login, final fixture through API/UI, safe text rendering, acknowledgement,
mute, search, phone overflow check, offline/reconnect, reload without duplicate
entries, caregiver/local separation and no JavaScript errors. Phone screenshot was
visually inspected. Reusable isolated browser runner includes provisional-text and
keyboard-focus assertions and is re-run for the final milestone.

Limitations: propagation uses 2-second polling; the <=1-second target is unmeasured
and not met by design yet. No measured 30-event latency distribution, recognition,
continuous audio, real network or hardware qualification. No second schema exists,
so previous-schema migration testing is not applicable yet. Current partial slot is
in memory only and never promoted to final without a separate final submission.

Reproduce from repository root: `.venv/bin/pytest -q`, `.venv/bin/ruff check .`,
`.venv/bin/ruff format --check .`, `.venv/bin/python tests/run_browser.py`.

Final isolated browser rerun passed, including the added provisional-text and explicit
keyboard-focus assertions. Final backend rerun: 16 passed in under one second; Ruff
lint and all seven Python files' formatting pass. `git diff --check` passes. No real
hardware/network acceptance outcome is implied. State: software_verified_hardware_pending.
