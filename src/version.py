"""Version + GitHub release info for the auto-updater.

Bump `__version__` BEFORE pushing a new release tag. The tag must match the
format `vX.Y.Z` (e.g. `v0.2.0`) — see GitHub Actions workflow.
"""
from __future__ import annotations

__version__ = "0.1.0"

# GitHub repo to check for new releases. Format: "owner/repo".
# Set this once your code is on GitHub. Leave as None to disable update checks.
GITHUB_REPO: str | None = "website-boost/Lohnbuero-Tool"

# Filename of the EXE asset attached to each release (set in build-windows.yml).
RELEASE_ASSET_NAME = "Lohnbuero-Tool.exe"
