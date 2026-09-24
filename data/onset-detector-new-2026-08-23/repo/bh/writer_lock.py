"""The single writer lock, enforced and instrumented — A2 §37 / rulebook §1.5/§1.7.

The store serializes behind `live_data/runtime/refresh.lock`: the pipeline and
batch tooling hold the same fd path, and both write the same holder-identity
sidecar. Admission's `runner.lock` and autopilot's `cycle.lock` are deliberately
separate at-most-once coordinator locks; they protect scheduler journals and
must not be confused with, or held across a child process acquiring, the store
writer barrier. A2 §37 formalizes refresh.lock as THE named writer lock and
adds a stale horizon DERIVED from measured holds (never chosen, never
auto-broken), plus `bh lock status` / `bh lock break`.

Stale horizon derivation (A2 §37.3):
  longest legitimate hold measured across receipts = 1722s
  (B2L: `autopilot verify_live` held the publication barrier ~28.7min/cycle;
   cross-checks: F1 publish 0.029s, oracle read 205.7s, B1.2 per-source
   rebuild ~1200s). Horizon = 1722 * 2 (stated 2x headroom) = 3444s. A lock
   older than this raises a blocker; it is NEVER auto-broken.
"""

from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import paths

LONGEST_MEASURED_HOLD_SECONDS = 1722  # B2L verify_live barrier hold
STALE_HEADROOM_FACTOR = 2
STALE_HORIZON_SECONDS = LONGEST_MEASURED_HOLD_SECONDS * STALE_HEADROOM_FACTOR  # 3444
STALE_HORIZON_DERIVATION = (
    "max measured legitimate hold 1722s (B2L verify_live barrier) x 2 headroom = 3444s; "
    "cross-checks: publish 0.029s, oracle 205.7s, per-source rebuild ~1200s"
)


class WriterLockHeld(RuntimeError):
    """A second writer was refused. Names the holder (A2 §37.1)."""


def lock_path(repo: Path | None = None) -> Path:
    root = paths.resolve_repo(str(repo) if repo else None)
    return root / "live_data" / "runtime" / "refresh.lock"


def _holder_path(repo: Path | None = None) -> Path:
    lp = lock_path(repo)
    return lp.parent / "refresh.lock.holder.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_holder(repo: Path | None, label: str) -> None:
    record = {"pid": os.getpid(), "label": label, "acquired_at": _now()}
    path = _holder_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_holder(repo: Path | None = None) -> dict | None:
    try:
        return json.loads(_holder_path(repo).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@contextmanager
def writer_lock(label: str, repo: Path | None = None):
    """Acquire the named writer lock or ABORT naming the holder (A2 §37.1)."""
    lp = lock_path(repo)
    lp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lp), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            holder = read_holder(repo) or {}
            os.close(fd)
            raise WriterLockHeld(
                "writer lock held; refusing second writer (rulebook §1.5). holder "
                f"pid={holder.get('pid', '?')} label={holder.get('label', '?')} "
                f"acquired_at={holder.get('acquired_at', '?')}"
            )
        _write_holder(repo, label)
        try:
            yield lp
        finally:
            try:
                _holder_path(repo).unlink()
            except OSError:
                pass
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def status(repo: Path | None = None) -> dict:
    """Held-or-free plus holder + staleness. Never auto-breaks (A2 §37.3)."""
    lp = lock_path(repo)
    held = False
    # A read-only probe must never be able to REFUSE a legitimate writer.
    # This used to take LOCK_EX: `bh doctor` (and any other status caller) won the
    # exclusive lock for the instant between acquire and release, so a
    # `bh commit-staged` / `bh queue run` starting in that window got EWOULDBLOCK
    # and aborted reporting `pid=? label=? acquired_at=?` (no sidecar exists yet)
    # — a health check able to kill a commit and strand staged drafts. LOCK_SH
    # detects an exclusive holder exactly as well and excludes nobody.
    # mkdir: status() lacked the parent-dir creation writer_lock() does, so on a
    # tree where live_data/runtime/ does not yet exist `bh doctor` died with a
    # FileNotFoundError traceback instead of printing a verdict.
    lp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lp), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)  # was free; release immediately
        except OSError:
            held = True
    finally:
        os.close(fd)
    holder = read_holder(repo)
    stale = False
    age_s = None
    if holder and holder.get("acquired_at"):
        try:
            acq = datetime.strptime(holder["acquired_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            age_s = (datetime.now(timezone.utc) - acq).total_seconds()
            stale = age_s > STALE_HORIZON_SECONDS
        except ValueError:
            pass
    return {
        "held": held,
        "holder": holder,
        "age_seconds": age_s,
        "stale_horizon_seconds": STALE_HORIZON_SECONDS,
        "stale": stale,
    }


def cli(args) -> int:
    action = args.lock_action
    if action == "status":
        st = status()
        print(f"writer lock: {'HELD' if st['held'] else 'free'}")
        if st["holder"]:
            h = st["holder"]
            print(f"  holder: pid={h.get('pid')} label={h.get('label')} acquired_at={h.get('acquired_at')}")
            if st["age_seconds"] is not None:
                print(f"  age: {st['age_seconds']:.0f}s (stale horizon {st['stale_horizon_seconds']}s)")
            if st["stale"]:
                print("  STALE: exceeds derived horizon — file a blocker; NEVER auto-broken (A2 §37.3)")
        else:
            print("  holder: unknown (no bh sidecar; may be held by store.refresh_lock)")
        return 0
    if action == "break":
        if not args.confirm:
            print("bh lock break requires --confirm (A2 §37.5). Refusing.")
            return 2
        from . import blockers

        holder = read_holder()
        reason = args.reason or "unspecified"
        # Record who broke it and why (A2 §37.5). Quiesce first (rulebook §1.8).
        blockers.write_blocker(
            "DECISION",
            "writer-lock-break",
            {"broke_holder": holder, "reason": reason, "warning": "quiesce writers first (rulebook §1.8)"},
            "confirm no live writer remains, then clear",
        )
        try:
            _holder_path().unlink()
        except OSError:
            pass
        print(f"writer lock: break recorded (reason={reason}). Holder sidecar cleared.")
        print("NOTE: a live fd-holder is not force-released; quiesce it (bh quiesce / rulebook §1.8).")
        return 0
    print(f"unknown lock action {action!r}")
    return 2
