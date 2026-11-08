# Stage 0 — reproducible foundation

Environment: managed cloud development host, Debian 13 x86_64, Python 3.12.14,
33 GiB RAM, approximately 60 GiB free disk at inspection. No /dev/snd, pw-cli or mpv.
Headless Chromium exists. This is not the parents' laptop.

Pinned direct dependencies: FastAPI 0.121.1, Uvicorn 0.38.0, pytest 8.4.2,
httpx 0.28.1, Ruff 0.14.4; transitive resolutions in uv.lock. Playwright 1.62.1
is pinned in package-lock.json. No system package or audio-routing change was made.

Verification commands: README install, pytest, Ruff and isolated browser runner.
Configuration invalid-origin/timezone/backend/storage inputs are rejected. Tests use
synthetic fixtures and temporary SQLite state with no paid API or audio hardware.
FastAPI lifespan documentation was consulted through its official GitHub source:
https://raw.githubusercontent.com/fastapi/fastapi/master/docs/en/docs/advanced/events.md
The primary documentation websites for FastAPI and SQLite returned HTTP 403 under
the cloud network policy. SQLite backup API was checked against the runtime docstring.
No external SDK, model name, or Tailscale configuration was assumed.

The old project's deletions were explicitly requested. Original Git history and a
verified complete archive at /workspace/repository-backups are preserved. No push.
Reusable cloud configuration saving is independently failing with INVALID_ARGUMENT;
it is not evidence of an installation failure. Project instructions remain in Git.

Final result: stage 0 passed. `uv build --out-dir /tmp/parents-build` produced a source
archive and wheel. The wheel installed in /tmp/parents-clean and imported from /tmp,
independently of the source checkout, with packaged static assets present. The source
install uses `uv sync --frozen --extra dev`. Local backup/restore CLI steps were also
executed, and an authenticated restored server returned the original synthetic row.
