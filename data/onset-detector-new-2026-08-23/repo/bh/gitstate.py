"""Authority-tree cleanliness — B-HOUSE-3 Defect 3.

One-committer discipline (B-PROD-1 §3) means a batch writes "brief + DONE + exit"
and the DIRECTOR commits. Nothing enforced the sweep, so git HEAD once sat at a
prior batch for ~35 min while the unattended nightly could have published over an
inconsistent tree. This module names any uncommitted change under an *authority*
path so `bh doctor` fails loudly and the nightly refuses to publish over it.

Untracked `research/` scratch is deliberately NOT authority — it never trips this
(its whole point is to be ephemeral; see .gitignore B-HOUSE-1/3).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# The dirs whose content IS published authority. An uncommitted change under any
# of these means the tree the nightly would publish is not the committed one.
AUTHORITY_PREFIXES = (
    "live_data/config",
    "live_data/catalog",
    "model_authority",
    "method_source",
    "data_vault/manifests",
    "contrib/",
)


def _is_authority(path: str) -> bool:
    for prefix in AUTHORITY_PREFIXES:
        base = prefix.rstrip("/")
        if path == base or path.startswith(base + "/"):
            return True
    return False


def parse_porcelain(text: str) -> list[str]:
    """Return the authority paths named in `git status --porcelain` output.

    Porcelain lines are `XY <path>` (or `XY <orig> -> <new>` for renames); we key
    on the destination path. Blank/short lines are skipped.
    """
    dirty: list[str] = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:  # rename/copy — the new path is what would publish
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"')
        if _is_authority(path):
            dirty.append(path)
    return sorted(set(dirty))


class GitStateUnknown(RuntimeError):
    """`git status` could not be run or did not succeed: cleanliness is UNKNOWN.

    Distinct from "clean". A caller gating a publish on cleanliness must treat
    this as a refusal, never as permission.
    """


def authority_dirty(repo: Path) -> list[str]:
    """List uncommitted authority paths in `repo`. Empty list == clean/publishable.

    Raises GitStateUnknown if git could not be run or exited non-zero.

    This used to `return []` — i.e. report CLEAN — on ANY git failure, which made
    the one gate that exists to stop the nightly publishing an uncommitted
    authority tree FAIL OPEN. Concretely: after a macOS update `/usr/bin/git`
    exits 1 with `xcrun: error: invalid active developer path`; the old code
    swallowed that, `bh nightly` step 0 logged `authority_tree: CLEAN`, and the
    run published a tree carrying uncommitted model_authority/ changes. The old
    docstring deferred to "doctor's resolution check", but
    doctor._check_resolution only calls paths.resolve_repo/resolve_interpreter —
    it never touches git, so nothing anywhere caught it. Unknown is not clean.
    """
    try:
        proc = subprocess.run(
            # -uall: list each untracked file, never collapse a wholly-new
            # authority dir to its parent (which would hide the change).
            ["git", "status", "--porcelain", "-uall"], cwd=str(repo),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitStateUnknown(f"git status could not be run in {repo}: {exc}") from exc
    if proc.returncode != 0:
        raise GitStateUnknown(
            f"git status exited {proc.returncode} in {repo}: "
            f"{(proc.stderr or '').strip()[:300]}"
        )
    return parse_porcelain(proc.stdout)
