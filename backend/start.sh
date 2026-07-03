#!/usr/bin/env bash
set -euo pipefail

# The Python package `taskpilot` lives one level above this repo root,
# so include the repo parent on PYTHONPATH when Render starts from `backend/`.
export PYTHONPATH="$(cd ../.. && pwd)"

exec gunicorn --bind 0.0.0.0:${PORT:-10000} taskpilot.app.api:app
