# Parents Companion

A local-first caregiver dashboard for a Linux laptop. This first development milestone
runs a real, persistent transcript pipeline with **synthetic data only**. It does not
capture a microphone, recognize speech, play media, or provide remote access yet.

Read [the specification review](docs/REVIEW.md), [status](STATUS.md), and the preserved
[development plan](DEVELOPMENT_PLAN.md). Hardware and deployment gates remain open.

## Install and run

Tested with Python 3.12.14 on Debian 13. From this checkout:

```sh
cd /workspace/LLMs-from-scratch
UV_CACHE_DIR=/workspace/.uv-cache uv sync --frozen --extra dev
.venv/bin/parents-companion serve
```

Open `http://127.0.0.1:8765` **on the machine running the app**. Cloud onboarding does
not provide a localhost preview. A target laptop or an independently configured
local development session is needed for interactive access. No public hosting is set up.

On first start, role access tokens are generated in `state/credentials.json` with
owner-only permissions. Open that file privately on the machine. Use the `local`
token for the parent/synthetic-input session or `caregiver` for history access.
Do not share the local token with remote caregivers or paste either token into chat.
Tokens are entered once into the login form; the browser receives an eight-hour
HttpOnly session. Server restart requires signing in again. Sign out when finished.

The local view offers **Save synthetic speech**, **Mute listening**, and **Resume
synthetic listening**. Fictional entries appear in persistent, searchable history.
Caregivers can mark entries acknowledged or handled and export NDJSON. A caregiver
cannot clear local mute. The two roles are development credentials, not production
Tailscale authentication. Do not expose this server through a reverse proxy yet.

Stop with Ctrl-C (or SIGTERM). Start it again using the same command to retain history
and local mute. Configuration is optional:

```sh
cp config.example.toml config.toml
.venv/bin/parents-companion --config config.toml serve
```

Every current setting and its default/units is documented in `config.example.toml`.
Start commands resolve data paths relative to the working directory.

## Verify

```sh
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
npm ci --ignore-scripts --cache /workspace/.npm-cache
.venv/bin/python tests/run_browser.py
```

Browser tests need a free port 8765, Node, Playwright, and Chromium at
`/usr/bin/chromium`. The cloud image already supplies Chromium; no sandbox flag should
be copied into a normal user browser. The test runner uses temporary synthetic state,
starts/stops its own server, and never touches the normal state directory. Its
headless launch uses `--no-sandbox` for the container test environment. For a clean
machine without Chromium, install a maintained distro Chromium package first.
Normal tests require no microphone, GUI session, paid API, or private recordings.

`POST /api/synthetic/partial` supplies a visibly provisional, ephemeral text slot.
`POST /api/synthetic/segments` commits a final fixture. These are local-role-only
development interfaces; inspect the tested payloads in `tests/test_pipeline.py`.

## Recovery and next work

[Operations](docs/OPERATIONS.md) covers backup/restore, token rotation, export and
rollback. [Hardware tests](docs/HARDWARE_TESTS.md) lists target-laptop gates.
Systemd install/start/status, Tailscale/Serve, real audio, mpv, log rotation and tagged
release installation are **not implemented**. Do not install this as unattended care
infrastructure. The next stage is the capture/segmentation/isolated transcription
worker, followed by target-laptop validation. Cloud transcription remains deferred.
