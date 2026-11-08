#!/usr/bin/env bash
set -euo pipefail
cd /workspace/LLMs-from-scratch
export UV_CACHE_DIR=/workspace/.uv-cache
uv sync --frozen --extra dev
npm ci --ignore-scripts --cache /workspace/.npm-cache
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
