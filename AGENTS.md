# Parents Companion

Read DEVELOPMENT_PLAN.md, STATUS.md, docs/REVIEW.md, and relevant test reports first.
Use this existing checkout; cloud tasks are isolated. Do not create worktrees unless asked.
Preserve the intentional deletion of the previous LLM book project.

Architecture: FastAPI owns SQLite writes and atomic durable events. Browser text uses
textContent. Synthetic mode must never open audio hardware or call a paid API.
Never let caregiver actions clear local mute. Keep production state, credentials,
transcripts, and audio out of Git and reports. Do not print access tokens.

Commands (from repository root):
- `UV_CACHE_DIR=/workspace/.uv-cache uv sync --frozen --extra dev`
- `.venv/bin/pytest -q`
- `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`
- `.venv/bin/python tests/run_browser.py` (free port 8765, Node Playwright and Chromium)
- `.venv/bin/parents-companion serve`

Run meaningful integration/browser checks. Hardware and network tests remain pending
until actually observed. Record stage evidence and limitations; never report synthetic
results as physical device success. Commit verified local milestones using existing
Git identity; do not push or publish without explicit user authorization.
