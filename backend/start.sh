#!/usr/bin/env bash
set -euo pipefail

# Render starts in `backend/`; add repository root so module imports resolve.
export PYTHONPATH="$(cd .. && pwd)"

exec gunicorn --bind 0.0.0.0:${PORT:-10000} taskpilot.app.api:app
