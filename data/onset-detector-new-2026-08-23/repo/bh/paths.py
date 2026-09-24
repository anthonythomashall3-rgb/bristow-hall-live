"""Resolution of repo root, support dir, and interpreter — A2 §35.2/§35.3.

Every path here is absolute. Nothing is ever derived from the current working
directory, and the interpreter is never `whatever python3 is first on PATH`.
These functions must behave identically in an interactive shell, a
non-interactive `bash -lc`, and a launchd context (A2 §35.4) — so they read
only from the environment (`$BH_REPO`, `$HOME`) and from files under the
support dir, never from a login profile.
"""

from __future__ import annotations

import os
from pathlib import Path


class ResolutionError(RuntimeError):
    """A required path could not be resolved. Named, never silent (A2 §35.2)."""


def support_dir() -> Path:
    """`~/Library/Application Support/bristow-hall` — created on demand.

    Uses $HOME, which launchd sets for a per-user agent. Never the cwd.
    """
    home = os.environ.get("HOME")
    if not home:
        raise ResolutionError("bh: $HOME is unset; cannot locate support dir")
    return Path(home) / "Library" / "Application Support" / "bristow-hall"


def _read_line(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def resolve_repo(explicit: str | None = None) -> Path:
    """Repo root. Order (A2 §35.2): explicit arg, $BH_REPO, support/repo.path.

    Never falls back to a relative path or an assumed cwd. Failure is a named
    error, not a guess.
    """
    for candidate in (explicit, os.environ.get("BH_REPO"), _read_line(support_dir() / "repo.path")):
        if candidate:
            root = Path(candidate).expanduser()
            if (root / "live_data").is_dir() and (root / "data_vault").is_dir():
                return root.resolve()
    raise ResolutionError(
        "bh: repo not resolved. Set $BH_REPO or write the absolute repo path to "
        f"{support_dir() / 'repo.path'}"
    )


def resolve_interpreter() -> Path:
    """The project interpreter (A2 §35.3).

    Recorded at install from the interpreter that ran the install (the pyenv
    3.8.10 python the launchd plists already pin). Never `python3` off PATH.
    """
    recorded = _read_line(support_dir() / "interpreter.path")
    if recorded and Path(recorded).is_file() and os.access(recorded, os.X_OK):
        return Path(recorded)
    raise ResolutionError(
        "bh: interpreter not resolved. Run `python3 -m bh install` from the repo "
        f"to record it at {support_dir() / 'interpreter.path'}"
    )


def bh_bin_path() -> Path:
    """The installed shim location — a fixed absolute path outside ~/Desktop.

    A2 §35.1: the watchdog exit 126 proved TCC denies launchd execution under
    ~/Desktop, so the shim must live elsewhere.
    """
    home = os.environ.get("HOME")
    if not home:
        raise ResolutionError("bh: $HOME is unset; cannot locate bin path")
    return Path(home) / ".local" / "bin" / "bh"
