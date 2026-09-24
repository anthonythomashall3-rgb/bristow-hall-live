"""Typed blocker queue — A2 §5.

Canonical location is `<repo>/blockers/` (visible where the owner works,
version-controlled once git lands). The repo lives under ~/Desktop, a
TCC-protected folder, so a launchd-context write there may be denied — the
same class of failure as the watchdog exit 126. Per the preregistered branch:

  * write to `<repo>/blockers/` succeeds  -> canonical location is the repo.
  * write is denied                        -> the agent writes to the support
    inbox, and a drain step folds the inbox into `<repo>/blockers/` on demand.

The owner only ever looks in `<repo>/blockers/`. Each blocker is one JSON file,
never overwritten, cleared only by an explicit resolve. An empty directory is
the signal that the system is running itself.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import paths

# Rulebook §13 vocabulary, plus the mechanical-signal types A2 introduces.
RULEBOOK_TYPES = (
    "PREDECESSOR_ABSENT",
    "RIGHTS_UNRESOLVED",
    "CLOCK_UNRESOLVED",
    "STRICT_FIRST_RELEASE_UNPROVEN",
)
A2_TYPES = (
    "SHAPE_DRIFT",
    "SOURCE_HEALTH",
    "SOURCE_STALE",
    "RELEASE_MISS",
    "BLOCKER_AGING",
    "DISK_GROWTH",
    "REGRESSION",
    "DECISION",
    "CONTAMINATION",
    "COVERAGE_REGRESSION",
    "FABRICATION",
    "SCOPE_SUPERSEDED",
)
KNOWN_TYPES = frozenset(RULEBOOK_TYPES + A2_TYPES)


def blocker_dir(repo: Path | None = None) -> Path:
    return paths.resolve_repo(str(repo) if repo else None) / "blockers"


def inbox_dir() -> Path:
    return paths.support_dir() / "run" / "blockers-inbox"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(blocker_type: str, source: str, evidence, what_would_clear: str) -> dict:
    if blocker_type not in KNOWN_TYPES:
        raise ValueError(f"unknown blocker type {blocker_type!r}; extend KNOWN_TYPES first")
    return {
        "schema_version": "recession-monitor-v2.typed-blocker.v1",
        "type": blocker_type,
        "source": source,
        "timestamp": _now(),
        "evidence": evidence,
        "what_would_clear": what_would_clear,
        "status": "open",
    }


def _filename(record: dict) -> str:
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:12]
    safe_source = "".join(c if c.isalnum() or c in "-._" else "_" for c in record["source"])[:48]
    return f"{record['type']}__{safe_source}__{digest}.json"


def _try_write(directory: Path, record: dict) -> Path | None:
    """Write one immutable blocker file. Returns the path, or None if denied."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / _filename(record)
        if path.exists():
            return path  # identical blocker already filed; never overwrite
        tmp = directory / (path.name + ".tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return path
    except (PermissionError, OSError):
        return None


def write_blocker(
    blocker_type: str,
    source: str,
    evidence,
    what_would_clear: str,
    repo: Path | None = None,
) -> dict:
    """File a blocker. Canonical dir first; support inbox on TCC denial (A2 §5)."""
    record = _record(blocker_type, source, evidence, what_would_clear)
    path = _try_write(blocker_dir(repo), record)
    via = "repo"
    if path is None:
        path = _try_write(inbox_dir(), record)
        via = "inbox"
    if path is None:
        raise RuntimeError("bh: could not write blocker to repo or inbox")
    return {"path": str(path), "via": via, "type": blocker_type, "source": source}


def drain_inbox(repo: Path | None = None) -> list[str]:
    """Fold the support inbox into `<repo>/blockers/` (A2 §5 runbook step)."""
    moved: list[str] = []
    inbox = inbox_dir()
    if not inbox.is_dir():
        return moved
    dest = blocker_dir(repo)
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(inbox.glob("*.json")):
        target = dest / item.name
        if not target.exists():
            os.replace(item, target)
            moved.append(target.name)
        else:
            item.unlink()  # identical blocker already canonical
    return moved


def list_blockers(repo: Path | None = None, include_resolved: bool = False) -> list[dict]:
    out: list[dict] = []
    for directory, via in ((blocker_dir(repo), "repo"), (inbox_dir(), "inbox")):
        if not directory.is_dir():
            continue
        for item in sorted(directory.glob("*.json")):
            try:
                rec = json.loads(item.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not include_resolved and rec.get("status") != "open":
                continue
            rec["_file"] = item.name
            rec["_via"] = via
            out.append(rec)
    return out


def resolve_blocker(filename: str, note: str, repo: Path | None = None) -> dict:
    """Explicit resolve only (A2 §5). Marks status and moves to blockers/resolved/."""
    root = blocker_dir(repo)
    src = root / filename
    if not src.is_file():
        raise FileNotFoundError(f"bh: no open blocker named {filename}")
    rec = json.loads(src.read_text(encoding="utf-8"))
    rec["status"] = "resolved"
    rec["resolved_at"] = _now()
    rec["resolve_note"] = note
    resolved_dir = root / "resolved"
    resolved_dir.mkdir(parents=True, exist_ok=True)
    dest = resolved_dir / filename
    dest.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    src.unlink()
    return {"resolved": filename, "note": note}


def cli_list(args) -> int:
    include_resolved = getattr(args, "all", False)
    records = list_blockers(include_resolved=include_resolved)
    if not records:
        print("blockers: none open (the system is running itself)")
        return 0
    for rec in records:
        print(f"[{rec.get('type')}] {rec.get('source')}  {rec.get('timestamp')}  ({rec['_via']})")
        print(f"    clears: {rec.get('what_would_clear')}")
        print(f"    file:   {rec['_file']}")
    print(f"\n{len(records)} open blocker(s)")
    return 0
