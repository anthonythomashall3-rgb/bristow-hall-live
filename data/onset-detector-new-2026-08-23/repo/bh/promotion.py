"""Promotion ledger — the single authority for which runbooks may run unattended
(B-AUTO-1 §3, one-file-one-authority per A2 §24).

A runbook is *promotable* to unattended only after it has accumulated at least
as many attended clean runs as this project has MEASURED distinct ways for a
batch run to fail. The criterion is therefore DERIVED (count the observed
failure classes), never chosen: promotion means "every known way to fail has
had the chance to fire, and did not". The derivation — class list + citations —
is recorded in the ledger itself so the number can be audited, not trusted.

Any byte change to a promoted runbook flips its recorded sha256, which this
module treats as automatic demotion (unattended -> false, clean-run counter
reset): an edited runbook is a different runbook and must earn promotion again.

Stage 1 (this batch) only ever promotes read-only chores (`read_only: true`).
Store-writing runbooks meet the same criterion per runbook — no blanket grant —
but are out of stage-1 scope here.

No AI, no network. Pure ledger arithmetic over an on-disk JSON authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import paths

LEDGER_REL = Path("live_data") / "config" / "promoted_runbooks.v1.json"
SCHEMA = "recession-monitor-v2.promoted_runbooks.v1"

# The measured failure classes for RMV2 batch runs, each with a concrete
# citation to the receipt / blocker / quarantine note where it actually fired.
# The promotion criterion is the COUNT of these — derived, not chosen (§3).
MEASURED_FAILURE_CLASSES = [
    {
        "class": "verify_fail",
        "citation": "B1.3b drain+deep STOP: pre-existing dol failure blocked inventory verify PASS",
    },
    {
        "class": "suite_fail",
        "citation": "B-AUTO-1 baseline: flaky pytest failure under a live concurrent writer (626p/1s/1f/12err)",
    },
    {
        "class": "quiesce_fail",
        "citation": "B-SAFE-1 Defect A: quiesce async-return race, survivor false positive (fixed, 9 tests, 20.22s hold)",
    },
    {
        "class": "timeout_oversize",
        "citation": "B1.4-LIVE §3 STOP: non-idle republish O(store) over >1GB weekly-vintage blobs",
    },
    {
        "class": "rogue_writer",
        "citation": "B1.3: quarantined admission-runner scheduled tick auto-drained the queue mid-batch (stale code)",
    },
    {
        "class": "store_divergence",
        "citation": "store/objects key leak (#11) and B1.3 half-admitted fred_nfci diverging the store in!=out",
    },
]
PROMOTION_CRITERION = len(MEASURED_FAILURE_CLASSES)  # derived value


class LedgerError(RuntimeError):
    """The promotion ledger is malformed or an operation is refused."""


def ledger_path(repo: Path | None = None) -> Path:
    return paths.resolve_repo(str(repo) if repo else None) / LEDGER_REL


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _derivation() -> dict:
    return {
        "value": PROMOTION_CRITERION,
        "rule": "attended_clean_runs >= count(measured distinct failure classes)",
        "measured_failure_classes": MEASURED_FAILURE_CLASSES,
        "note": "derived, not chosen: every known way to fail must have had the chance to fire",
    }


def default_ledger() -> dict:
    return {
        "schema": SCHEMA,
        "authority_note": "single promotion authority (A2 §24 / B-AUTO-1 §4: one file only)",
        "criterion": _derivation(),
        "runbooks": [],
    }


def load_ledger(repo: Path | None = None) -> dict:
    path = ledger_path(repo)
    if not path.exists():
        return default_ledger()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"promotion ledger unreadable ({path}): {exc}")
    if data.get("schema") != SCHEMA:
        raise LedgerError(f"promotion ledger schema mismatch: {data.get('schema')!r}")
    data.setdefault("runbooks", [])
    return data


def save_ledger(ledger: dict, repo: Path | None = None) -> Path:
    # Keep the derivation current even if the file was hand-edited: the criterion
    # is code-derived, the file only records it.
    ledger["schema"] = SCHEMA
    ledger["criterion"] = _derivation()
    path = ledger_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def _find(ledger: dict, runbook_id: str) -> dict | None:
    for entry in ledger["runbooks"]:
        if entry.get("runbook_id") == runbook_id:
            return entry
    return None


def register_runbook(ledger: dict, runbook_id: str, path: str, *, read_only: bool) -> dict:
    """Add a runbook, not yet promoted. Idempotent by runbook_id."""
    entry = _find(ledger, runbook_id)
    if entry is None:
        entry = {
            "runbook_id": runbook_id,
            "path": path,
            "sha256": None,
            "attended_clean_runs": 0,
            "unattended": False,
            "read_only": bool(read_only),
            "promoted_at": None,
            "criterion": PROMOTION_CRITERION,
        }
        ledger["runbooks"].append(entry)
    else:
        entry["path"] = path
        entry["read_only"] = bool(read_only)
    return entry


def record_clean_run(ledger: dict, runbook_id: str, sha256: str) -> dict:
    """Record ONE attended clean run. The sha is pinned on first run; a changed
    sha resets the counter (it is a different runbook). Auto-promotes when the
    count reaches the derived criterion AND the runbook is read-only (stage 1)."""
    entry = _find(ledger, runbook_id)
    if entry is None:
        raise LedgerError(f"runbook not registered: {runbook_id}")
    if entry.get("sha256") not in (None, sha256):
        # bytes changed mid-accumulation — demote and restart the count
        entry["attended_clean_runs"] = 0
        entry["unattended"] = False
        entry["promoted_at"] = None
    entry["sha256"] = sha256
    entry["attended_clean_runs"] = int(entry.get("attended_clean_runs", 0)) + 1
    entry["criterion"] = PROMOTION_CRITERION
    if (
        entry["attended_clean_runs"] >= PROMOTION_CRITERION
        and entry.get("read_only", False)
        and not entry["unattended"]
    ):
        entry["unattended"] = True
        entry["promoted_at"] = _now()
    return entry


def demote(ledger: dict, runbook_id: str) -> dict:
    entry = _find(ledger, runbook_id)
    if entry is None:
        raise LedgerError(f"runbook not registered: {runbook_id}")
    entry["unattended"] = False
    entry["attended_clean_runs"] = 0
    entry["promoted_at"] = None
    return entry


def check_promotion(ledger: dict, path: Path) -> dict:
    """Gate-1 verdict for a runbook path (B-AUTO-1 §1.1). Returns a dict with
    `ok` (True == may run unattended) and a human `reason`. sha mismatch or a
    missing/attended-only entry all return ok=False — fail closed."""
    resolved = str(Path(path).resolve())
    entry = None
    for cand in ledger["runbooks"]:
        if str(Path(cand["path"]).resolve()) == resolved:
            entry = cand
            break
    if entry is None:
        return {"ok": False, "reason": f"runbook not in promotion ledger: {resolved}", "entry": None}
    if not entry.get("unattended"):
        return {
            "ok": False,
            "reason": f"runbook not promoted (attended_clean_runs="
            f"{entry.get('attended_clean_runs')}/{PROMOTION_CRITERION})",
            "entry": entry,
        }
    if not Path(path).exists():
        return {"ok": False, "reason": f"runbook file missing: {resolved}", "entry": entry}
    current = sha256_file(Path(path))
    if current != entry.get("sha256"):
        return {
            "ok": False,
            "reason": "sha256 mismatch — runbook edited since promotion (demoted)",
            "entry": entry,
            "sha_mismatch": True,
        }
    return {"ok": True, "reason": "promoted, sha matches", "entry": entry}


def cli(args) -> int:
    repo = Path(args.repo) if getattr(args, "repo", None) else None
    ledger = load_ledger(repo)
    action = args.promotion_action
    if action == "list":
        crit = ledger["criterion"]
        print(f"promotion criterion: {crit['value']} (= count of measured failure classes)")
        for cls in crit["measured_failure_classes"]:
            print(f"  - {cls['class']}: {cls['citation']}")
        print(f"runbooks: {len(ledger['runbooks'])}")
        for e in ledger["runbooks"]:
            print(
                f"  {e['runbook_id']}  unattended={e['unattended']} "
                f"clean_runs={e['attended_clean_runs']}/{e['criterion']} "
                f"read_only={e.get('read_only')} path={e['path']}"
            )
        return 0
    if action == "record":
        # Record ONE attended clean run: actually execute the read-only runbook;
        # only a clean (exit 0) run counts. Ties the counter to a real run (§3).
        import subprocess

        runbook = Path(args.path)
        if not runbook.exists():
            print(f"bh promotion record: runbook not found: {runbook}")
            return 2
        entry = _find(ledger, args.runbook_id) or register_runbook(
            ledger, args.runbook_id, str(runbook), read_only=args.read_only
        )
        proc = subprocess.run(
            ["/bin/sh", str(runbook)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=300, env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
        )
        if proc.returncode != 0:
            print(f"bh promotion record: runbook exited {proc.returncode}; NOT counted")
            print(proc.stderr[-400:])
            return 1
        entry = record_clean_run(ledger, args.runbook_id, sha256_file(runbook))
        save_ledger(ledger, repo)
        print(
            f"recorded clean run: {args.runbook_id} "
            f"clean_runs={entry['attended_clean_runs']}/{entry['criterion']} "
            f"unattended={entry['unattended']}"
        )
        return 0
    print(f"unknown promotion action {action!r}")
    return 2
