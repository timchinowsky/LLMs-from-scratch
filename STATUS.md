# Current status

Stage: 0 foundation and 1 synthetic transcript pipeline.
State: `software_verified_hardware_pending` for the implemented development workflow.
Branch: `work`. Current milestone commit: `git rev-parse HEAD` after the local milestone
commit; original base was fd8d77a79dd16e7223c94fd7287421085d1fc6c0.

| Stage | State | Notes |
|---|---|---|
| 0 | passed | Locked packaging, configuration, protected state, documents, clean wheel install |
| 1 | software_verified_hardware_pending | Real backend/browser synthetic pipeline; 2-second polling target exception recorded |
| 2 | not_started | Capture, segmentation, pre-transcription segment state and isolated recognizer worker needed |
| 3 | not_started | Optional cloud backend deferred; no benchmark or explicit cloud selection |
| 4 | in_progress | Application sessions/CSRF/origin/replay tested; private HTTPS, Tailscale and real-network gates pending |
| 5 | not_started | No mpv or media command execution |
| 6 | not_started | No echo routing or real audio |
| 7 | in_progress | Backup/export/fault tests done; services, real recovery and operational log rotation pending |
| 8 | not_started | No release tag, physical acceptance or long-run qualification |

Implemented: caregiver/local login, clear synthetic banner, persistent finals, UTC
capture times with Los Angeles display, ephemeral provisional text, search, pagination,
acknowledgement, event replay/resync, local mute with cancellation generation,
streaming export, consistent SQLite backup with new restore instance identity.

Verification: 16 backend/integration tests pass; Ruff lint/format pass; real Chromium
browser suite passes at 1280x1000 and 390x844 with no JS errors. Tests cover provisional
versus final, safe text, offline/reconnect, duplicate prevention, local mute, caregiver
boundary and keyboard navigation. Clean wheel built/installed separately and assets
verified. A restored server authenticated and returned its preserved synthetic record.
One upstream Starlette/AnyIO deprecation warning is non-failing. No real microphone,
speaker, recognition provider, echo cancellation, remote-network, reboot or long-run
hardware tests were performed.

Known limits: only synthetic manual producer/API input; no continuous capture/recognizer.
One provisional slot, no real model; no bounded audio pipeline yet. Live history refresh
returns to newest page. Polling does not satisfy the proposed <=1-second propagation
target. Development loopback HTTP only; no remote deployment. No release readiness claim.

Run from /workspace/LLMs-from-scratch:
`UV_CACHE_DIR=/workspace/.uv-cache uv sync --frozen --extra dev`
`.venv/bin/parents-companion serve`
Use the generated private local token on the local login view for fictional input;
caregiver token permits history and acknowledgement. Stop with Ctrl-C.
For tests: `.venv/bin/pytest -q`; `.venv/bin/python tests/run_browser.py` (free port 8765).
Full reusable setup commands: `bash docs/setup-cloud.sh`.

Exact next task: implement Stage 2's stable microphone adapter, bounded segmentation
and isolated transcription worker with synthetic labeled fixtures, then validate on
the target laptop. Capture must run independently of the dashboard. Do not install
system audio routing, a VPN client, auto-login or services on this cloud host as a
substitute for target-laptop validation. Follow docs/HARDWARE_TESTS.md.

Rollback checkpoint: this local milestone plus SQLite backup; no older app release.
Original repository archive: /workspace/repository-backups/LLMs-from-scratch-before-new-app.tar.gz.
Old book files intentionally deleted at the user's request; Git history retained.
No push or external publication occurred.

Cloud configuration: read/save calls fail INVALID_ARGUMENT; reusable install_script and
start_skill persistence is unconfirmed. The same setup/start instructions are retained
in this repository. Publication/new-task snapshot restoration has not been verified.
