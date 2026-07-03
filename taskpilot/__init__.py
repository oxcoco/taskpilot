"""Runtime package shim for environments where the repository root is not named `taskpilot`.

This package lets imports like `taskpilot.app.api` resolve even when the checkout
folder has a different name (for example Render's default `/opt/render/project/src`).
"""

from pathlib import Path

# Include the repository root in package search paths so subpackages like
# `taskpilot.app` map to `<repo_root>/app`, `taskpilot.agents` to `<repo_root>/agents`, etc.
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in __path__:
    __path__.append(str(_repo_root))
