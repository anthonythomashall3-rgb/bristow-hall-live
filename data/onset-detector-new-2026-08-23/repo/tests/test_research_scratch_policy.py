"""research/ scratch policy is enforced by .gitignore (B-HOUSE-3 Defect 2)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _ignored(relpath: str) -> bool:
    # git check-ignore is read-only; exit 0 == path is ignored.
    return subprocess.run(
        ["git", "check-ignore", "-q", relpath], cwd=str(REPO)
    ).returncode == 0


@pytest.mark.parametrize("p", [
    "research/scratch/anything.txt",
    "research/scratch/sub/dump.log",
    "research/CH-R99_baseline.txt",   # legacy top-level scratch pattern
    "research/BATCH_run.log",
])
def test_scratch_paths_are_ignored(p):
    assert _ignored(p), f"{p} should be gitignored scratch"


@pytest.mark.parametrize("p", [
    "research/CH-R99.v1.json",         # durable probe receipt
    "research/lit/external_methodology_v1.md",
    "research/some_area/result.csv",
])
def test_durable_products_are_not_ignored(p):
    assert not _ignored(p), f"{p} is a durable product and must stay trackable"


def test_policy_doc_exists():
    assert (REPO / "research" / "README.md").exists()
