"""DONE-ledger consistency lint — B-HOUSE-3 Defect 1.

The mailbox close-out ledger (`_mailbox/state/DONE.md`) is one row per batch:

    <batch_id>  <utc-stamp>  <STATUS>

`CH-R49` and `CH-R51` both wrote `20260806T063500Z` while their briefs' real
mtimes were `06:48:44Z`/`06:48:19Z` — a rounded stamp taken at *dispatch*, not at
*close-out*, so the ledger reads ~13 min in the past. A close-out stamp can never
precede the brief it closes; this linter flags any row whose stamp does.

Pure functions (path-injected) so the check is testable without the live mailbox
and reusable by any window's runner. History is never rewritten here — the caller
appends a correction note (see BOOTSTRAP_MAILBOX.md close-out step).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

STAMP_RE = re.compile(r"^(\d{8}T\d{6}Z)$")


def parse_stamp(stamp: str) -> datetime:
    """Parse a `YYYYMMDDThhmmssZ` UTC stamp to an aware datetime. Raises ValueError."""
    dt = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ")
    return dt.replace(tzinfo=timezone.utc)


def parse_done_rows(text: str) -> list[dict]:
    """Rows of `<batch_id>  <stamp>  <STATUS>`. Non-conforming / note lines skipped."""
    rows: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 3:
            continue
        batch_id, stamp = parts[0], parts[1]
        if not STAMP_RE.match(stamp):
            continue
        rows.append({"batch_id": batch_id, "stamp": stamp, "status": parts[2]})
    return rows


def find_backdated(rows: list[dict], brief_mtimes: dict) -> list[dict]:
    """Rows whose close-out stamp precedes their own brief's mtime.

    `brief_mtimes` maps batch_id -> POSIX mtime (float). Rows with no matching
    brief are not judged (IDLE markers, external batches). Returns violation dicts
    with the measured gap in seconds.
    """
    violations: list[dict] = []
    for row in rows:
        bid = row["batch_id"]
        if bid not in brief_mtimes:
            continue
        try:
            stamp_dt = parse_stamp(row["stamp"])
        except ValueError:
            continue
        brief_dt = datetime.fromtimestamp(brief_mtimes[bid], tz=timezone.utc)
        if stamp_dt < brief_dt:
            violations.append({
                "batch_id": bid,
                "stamp": row["stamp"],
                "brief_mtime": brief_dt.strftime("%Y%m%dT%H%M%SZ"),
                "backdated_seconds": (brief_dt - stamp_dt).total_seconds(),
            })
    return violations


def lint_done_file(done_path: Path, briefs_dir: Path) -> list[dict]:
    """Load DONE.md + briefs/<batch_id>.md mtimes, return backdated violations."""
    done_path, briefs_dir = Path(done_path), Path(briefs_dir)
    rows = parse_done_rows(done_path.read_text(encoding="utf-8"))
    brief_mtimes: dict = {}
    for row in rows:
        bp = briefs_dir / f"{row['batch_id']}.md"
        if bp.exists():
            brief_mtimes[row["batch_id"]] = bp.stat().st_mtime
    return find_backdated(rows, brief_mtimes)


def now_stamp() -> str:
    """Canonical close-out UTC stamp — call at ACTUAL close-out, never at dispatch."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
