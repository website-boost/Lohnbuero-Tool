"""Auto-updater for the Windows EXE distribution.

Strategy: check GitHub Releases API for a newer tag, download the new EXE
next to the running one as `<name>.new.exe`, then spawn a small batch script
that waits for the current process to exit, swaps the EXE, and relaunches.
This works because Windows can't overwrite a running EXE — but it can rename
it, and a script started from the EXE outlives it.

Update checks degrade gracefully: any network/parse error is reported as
"keine Updates verfügbar" — never blocks the app from starting.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .version import GITHUB_REPO, RELEASE_ASSET_NAME, __version__


@dataclass
class UpdateInfo:
    latest_version: str
    download_url: str
    release_notes: str = ""
    release_url: str = ""


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse 'v1.2.3' or '1.2.3' → (1, 2, 3). Non-numeric parts → 0."""
    v = v.lstrip("vV").strip()
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p.split("-")[0]))  # strip pre-release suffixes
        except ValueError:
            parts.append(0)
    return tuple(parts) or (0,)


def check_for_update(timeout: float = 5.0) -> UpdateInfo | None:
    """Query GitHub Releases. Returns UpdateInfo if newer is available, else None."""
    if not GITHUB_REPO:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"Lohnbuero-Tool/{__version__}",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    tag = data.get("tag_name", "")
    if not tag:
        return None
    if _parse_version(tag) <= _parse_version(__version__):
        return None

    asset_url = ""
    for asset in data.get("assets", []):
        if asset.get("name") == RELEASE_ASSET_NAME:
            asset_url = asset.get("browser_download_url", "")
            break
    if not asset_url:
        return None

    return UpdateInfo(
        latest_version=tag.lstrip("vV"),
        download_url=asset_url,
        release_notes=data.get("body", "") or "",
        release_url=data.get("html_url", "") or "",
    )


def is_frozen_exe() -> bool:
    """True if running as a PyInstaller-built EXE (i.e. on the user's machine)."""
    return getattr(sys, "frozen", False) and sys.platform == "win32"


def download_and_apply_update(info: UpdateInfo, on_progress=None) -> None:
    """Download the new EXE and trigger an in-place swap + restart.

    Only safe to call when `is_frozen_exe()` is True. The current process exits
    after the swap script is launched. If the user closes the app instead, the
    `.new.exe` and update.bat just sit unused — harmless.
    """
    if not is_frozen_exe():
        raise RuntimeError("Auto-update only works on the built Windows EXE.")

    current_exe = Path(sys.executable).resolve()
    new_exe = current_exe.with_suffix(".new.exe")
    bat_path = current_exe.parent / "_lohnbuero_update.bat"

    # Download with progress
    with urllib.request.urlopen(info.download_url, timeout=30) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        with open(new_exe, "wb") as fh:
            downloaded = 0
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if on_progress and total:
                    on_progress(downloaded, total)

    # Build the swap script with retry loop so it survives:
    # - the EXE being briefly locked while PyInstaller cleans up
    # - antivirus scanning the new file before it's released
    # The loop tries every 1s until move succeeds (or 30s timeout).
    bat_content = (
        '@echo off\r\n'
        'timeout /t 3 /nobreak >nul\r\n'
        'set /a tries=0\r\n'
        ':try_move\r\n'
        f'move /y "{new_exe}" "{current_exe}" >nul 2>&1\r\n'
        'if errorlevel 1 (\r\n'
        '  set /a tries+=1\r\n'
        '  if %tries% geq 30 goto give_up\r\n'
        '  timeout /t 1 /nobreak >nul\r\n'
        '  goto try_move\r\n'
        ')\r\n'
        f'start "" "{current_exe}"\r\n'
        'del "%~f0"\r\n'
        'exit\r\n'
        ':give_up\r\n'
        'echo Update fehlgeschlagen — bitte manuell die neue EXE installieren.\r\n'
        'pause\r\n'
        'del "%~f0"\r\n'
    )
    bat_path.write_text(bat_content, encoding="utf-8")

    # Launch the script detached so it survives our exit.
    DETACHED = 0x00000008
    NEW_GROUP = 0x00000200
    subprocess.Popen(
        ["cmd.exe", "/c", str(bat_path)],
        creationflags=DETACHED | NEW_GROUP,
        close_fds=True,
    )
    # Give the spawned process a beat to fully detach, THEN exit normally
    # (sys.exit, not os._exit) so PyInstaller can clean up its MEIPASS
    # temp folder — otherwise the next launch shows a "Failed to load
    # Python DLL" warning referencing the orphaned folder.
    time.sleep(0.5)
    sys.exit(0)
