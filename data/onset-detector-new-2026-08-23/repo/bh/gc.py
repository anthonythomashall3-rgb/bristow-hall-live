"""bh gc — purge macOS/Python tree cruft (B-SAFE-1 §3.2/§3.3/§4.3).

Removes `.DS_Store` files, `__pycache__` directories, and `*.pyc` files from the
repo tree. It is deterministic and byte-derived (no AI, no network, no store
mutation), so it is legal for an unattended runbook under §1.1a.

SAFETY — basename match ONLY. The store holds content-addressed blobs whose
names are 64-hex sha256 digests; a glob like ``*.store`` or a substring match
could delete one. This module matches only the exact basename ``.DS_Store``, the
exact directory name ``__pycache__``, and the ``.pyc`` suffix — none of which a
real payload byte can ever carry. ``.git`` is never traversed.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import paths

SKIP_DIRS = {".git"}


def purge(root=None, dry_run: bool = False) -> dict:
    """Remove tree cruft under ``root`` (default: the resolved repo). Returns a
    dict of the relative paths removed, grouped by kind. ``dry_run`` reports
    what would be removed without touching disk."""
    base = Path(root).resolve() if root else paths.resolve_repo()
    removed = {"ds_store": [], "pycache": [], "pyc": []}

    for dirpath, dirnames, filenames in os.walk(base, topdown=True):
        # Never descend into skipped roots (.git).
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        # __pycache__ directories: remove whole, do not descend.
        for name in list(dirnames):
            if name == "__pycache__":
                full = Path(dirpath) / name
                rel = full.relative_to(base).as_posix()
                if not dry_run:
                    shutil.rmtree(full)
                removed["pycache"].append(rel)
                dirnames.remove(name)

        for name in filenames:
            full = Path(dirpath) / name
            if name == ".DS_Store":
                rel = full.relative_to(base).as_posix()
                if not dry_run:
                    full.unlink()
                removed["ds_store"].append(rel)
            elif name.endswith(".pyc"):
                rel = full.relative_to(base).as_posix()
                if not dry_run:
                    full.unlink()
                removed["pyc"].append(rel)

    for key in removed:
        removed[key].sort()
    return removed


def cli(args) -> int:
    removed = purge(dry_run=getattr(args, "dry_run", False))
    verb = "would remove" if getattr(args, "dry_run", False) else "removed"
    n_ds = len(removed["ds_store"])
    n_pc = len(removed["pycache"])
    n_pyc = len(removed["pyc"])
    if getattr(args, "json", False):
        import json

        print(json.dumps(removed, indent=2, sort_keys=True))
        return 0
    print("bh gc — %s: %d .DS_Store, %d __pycache__ dirs, %d .pyc" % (verb, n_ds, n_pc, n_pyc))
    for kind, label in (("ds_store", ".DS_Store"), ("pycache", "__pycache__"), ("pyc", ".pyc")):
        for rel in removed[kind]:
            print("  %s  %s" % (label, rel))
    return 0
