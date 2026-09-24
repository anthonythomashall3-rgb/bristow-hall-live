"""`python3 -m bh.cli` must not be a silent no-op (B-AUTO-1 director addendum).

Before this guard, importing bh.cli as __main__ ran to the bottom doing nothing
and exited 0 — a fail-open trap caught only because the receipt-chain head never
advanced. These tests pin that the wrong invocation fails LOUDLY and that the
canonical `python3 -m bh` entry point is unaffected.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _run(module_args):
    return subprocess.run(
        [sys.executable, "-m", *module_args],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )


def test_dash_m_bh_cli_does_not_silently_succeed():
    """`python3 -m bh.cli` must exit nonzero and say something — never a silent 0."""
    result = _run(["bh.cli"])
    assert result.returncode != 0, (
        "`python3 -m bh.cli` returned 0 (silent no-op fail-open): "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "bh" in combined and combined.strip(), "guard produced no message"


def test_dash_m_bh_still_works():
    """The canonical entry point is unaffected by the guard."""
    result = _run(["bh", "--version"])
    assert result.returncode == 0, f"`python3 -m bh --version` broke: {result.stderr!r}"
    assert "bh version:" in result.stdout
