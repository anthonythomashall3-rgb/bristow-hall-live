"""`bh queue run <queuefile>` — the serialized, fail-closed unattended runbook
runner (B-AUTO-1 §1).

A queuefile is plain text: one promoted-runbook path per line, `#` comments and
blank lines ignored, executed strictly in order. The whole run holds the single
writer lock (A2 §37); each entry passes eight fail-closed gates in order:

  1. promoted `unattended: true` in the ledger AND current sha256 matches
     (edited-since-promotion == demoted == refused, before anything else)
  2. `bh quiesce` proven (the B-LAND-1 impl; hold not proven -> STOP)
  3. catalog verify PASS at entry start
  4. runbook subprocess exits 0 (existing timeout budgets, PYTHONDONTWRITEBYTECODE=1)
  5. catalog verify PASS at entry end  (--full once at queue end if payload moved)
  6. suite green -> chained receipt (queue entries chain like batches, linear)
  7. git commit, store heads before/after recorded
  8. next entry

Any gate STOPs the whole run: restore the agents, write the queue receipt naming
the failed entry+gate, exit nonzero, run NOTHING further. Never a retry loop
(A2 §1.7). Deterministic CLI only — no AI, no network.

The side-effecting operations are injected (`QueueOps`), mirroring the
`LaunchctlOps` seam in quiesce.py, so the gate logic is unit-testable without
touching launchd, the store, git, or the suite.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import paths, promotion, quiesce, receipts, writer_lock

# §18.4 — reuse existing subprocess budgets; invent no new numbers.
CATALOG_VERIFY_TIMEOUT_S = quiesce.BOOTOUT_BUDGET_S        # 120 (existing)
FULL_VERIFY_TIMEOUT_S = 600                                 # existing install_launchd budget
RUNBOOK_TIMEOUT_S = 300                                     # existing install_watchdog budget
SUITE_TIMEOUT_S = 600                                       # existing max subprocess budget

# The suite carries pre-existing, out-of-scope breakage that this batch neither
# caused nor may fix: 12 collection errors (RTDSM rights-blocked + cloudflare
# connector import errors) and one deterministic failure (forecaster protocol
# manifest points at a file that is simply not on disk). "green" is defined
# against that MEASURED baseline — never a raw count that could hide a NEW
# failure: every FAILED node id must be in the known set, and no more collection
# errors than baseline. The set is named here, not silently dropped (§18.1).
BASELINE_COLLECTION_ERRORS = 12
BASELINE_KNOWN_FAILURES = frozenset({
    "method_source/forecaster/tests/test_protocol.py::ProtocolTests::"
    "test_registration_manifest_pins_authority_and_protocol",
})


class GateStop(Exception):
    """A gate refused. Names the entry, the gate, and why (fail closed)."""

    def __init__(self, entry: str, gate: str, detail: str):
        super().__init__(f"entry={entry} gate={gate}: {detail}")
        self.entry = entry
        self.gate = gate
        self.detail = detail


def parse_queuefile(text: str) -> list[str]:
    entries = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def _slug(path: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in Path(path).name).strip("-")


class QueueOps:
    """Real side effects for a live queue run. Injected so the gates are testable."""

    def __init__(self, repo: Path):
        self.repo = Path(repo)
        self._ql = quiesce.LaunchctlOps(self.repo)
        self._state = quiesce.state_path(self.repo)

    def writer_lock(self, label: str):
        return writer_lock.writer_lock(label, repo=self.repo)

    def quiesce(self) -> bool:
        try:
            quiesce.quiesce(self._ql, self._state)
            return True
        except quiesce.QuiesceError:
            return False

    def restore(self) -> bool:
        try:
            quiesce.restore(self._ql, self._state)
            return True
        except quiesce.RestoreError:
            return False

    def verify(self, mode: str) -> bool:
        script = self.repo / "data_vault" / "scripts" / "verify_data_vault.py"
        cmd = [sys.executable, str(script)]
        timeout = CATALOG_VERIFY_TIMEOUT_S
        if mode == "full":
            cmd.append("--full")
            timeout = FULL_VERIFY_TIMEOUT_S
        proc = subprocess.run(
            cmd, cwd=str(self.repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout,
        )
        return proc.returncode == 0

    def _subenv(self) -> dict:
        return {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PATH": "/usr/bin:/bin",
            "HOME": os.environ.get("HOME", ""),
            "BH_REPO": str(self.repo),
        }

    def run_runbook(self, path: str) -> int:
        env = self._subenv()
        proc = subprocess.run(
            ["/bin/sh", path], cwd=str(self.repo),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=RUNBOOK_TIMEOUT_S, env=env,
        )
        return proc.returncode

    def suite(self) -> bool:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "-rfE", "--continue-on-collection-errors"],
            cwd=str(self.repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=SUITE_TIMEOUT_S, env=self._subenv(),
        )
        return suite_is_green(proc.stdout)

    def store_head(self) -> str:
        return receipts.store_generation_sha(self.repo)

    def emit_receipt(self, record: dict, filename: str) -> str:
        receipts.emit_receipt(record, filename, repo=self.repo)
        return filename

    def git_commit(self, message: str) -> None:
        subprocess.run(["git", "add", "-A"], cwd=str(self.repo), check=False, timeout=120)
        subprocess.run(["git", "commit", "-m", message], cwd=str(self.repo), check=False, timeout=120)

    def save_ledger(self, ledger: dict) -> None:
        promotion.save_ledger(ledger, self.repo)


def suite_is_green(stdout: str) -> bool:
    """Green iff every FAILED node id is in the known pre-existing set and the
    collection-error count does not exceed baseline. A NEW failure (any node id
    not in the baseline set) is red — the count never hides it."""
    failed_ids = []
    errors = 0
    for raw in stdout.splitlines():
        s = raw.strip()
        if s.startswith("FAILED "):
            failed_ids.append(s.split()[1])
        elif s.startswith("ERROR "):
            errors += 1
        elif " error" in s and (" passed" in s or " failed" in s):
            # summary line fallback for the error count (e.g. "... 12 errors ...")
            toks = s.replace(",", "").split()
            for i, t in enumerate(toks):
                if t.startswith("error") and i > 0 and toks[i - 1].isdigit():
                    errors = max(errors, int(toks[i - 1]))
    new_failures = [f for f in failed_ids if f not in BASELINE_KNOWN_FAILURES]
    return not new_failures and errors <= BASELINE_COLLECTION_ERRORS


def _entry_receipt(batch_id, predecessor, store_before, store_after, path) -> dict:
    return receipts.build_receipt(
        batch_id=batch_id,
        predecessor_receipt=predecessor,
        store_start_sha=store_before,
        store_end_sha=store_after,
        generation_id_in=store_before,
        generation_id_out=store_after,
        body={
            "kind": "queue-entry",
            "runbook": path,
            "gates_passed": ["1-promotion", "2-quiesce", "3-verify-start",
                             "4-runbook", "5-verify-end", "6-suite"],
            "payload_changed": store_before != store_after,
        },
    )


def _queue_receipt(batch_id, predecessor, store_before, store_after, result) -> dict:
    body = {
        "kind": "queue-summary",
        "stop": bool(result["stopped"]),
        "entries_completed": [e["path"] for e in result["entries"]],
        "receipts": result["receipts"],
        "suite_baseline": {
            "known_failures": sorted(BASELINE_KNOWN_FAILURES),
            "collection_errors": BASELINE_COLLECTION_ERRORS,
        },
    }
    if result["stopped"]:
        body["stop_entry"] = result.get("stop_entry")
        body["stop_gate"] = result.get("stop_gate")
        body["stop_detail"] = result.get("stop_detail")
    return receipts.build_receipt(
        batch_id=batch_id, predecessor_receipt=predecessor,
        store_start_sha=store_before, store_end_sha=store_after,
        generation_id_in=store_before, generation_id_out=store_after,
        body=body,
    )


def _run_entry(ops, path, ledger, predecessor, batch_id) -> dict:
    p = Path(path)
    # gate 1 — promotion + sha (BEFORE quiesce; edited runbook is demoted here)
    verdict = promotion.check_promotion(ledger, p)
    if not verdict["ok"]:
        if verdict.get("sha_mismatch") and verdict.get("entry"):
            promotion.demote(ledger, verdict["entry"]["runbook_id"])
            ops.save_ledger(ledger)
        raise GateStop(path, "1-promotion", verdict["reason"])
    # gate 2 — quiesce proven
    if not ops.quiesce():
        raise GateStop(path, "2-quiesce", "quiesce hold not proven (agent survived bootout)")
    # gate 3 — verify start
    if not ops.verify("catalog"):
        raise GateStop(path, "3-verify-start", "catalog verify failed at entry start")
    store_before = ops.store_head()
    # gate 4 — runbook
    rc = ops.run_runbook(path)
    if rc != 0:
        raise GateStop(path, "4-runbook", f"runbook exited {rc}")
    # gate 5 — verify end
    if not ops.verify("catalog"):
        raise GateStop(path, "5-verify-end", "catalog verify failed at entry end")
    store_after = ops.store_head()
    # gate 6 — suite green + chained receipt
    if not ops.suite():
        raise GateStop(path, "6-suite", "suite not green vs measured baseline")
    receipt_name = f"{batch_id}.queue-entry.{_slug(path)}.v1.json"
    ops.emit_receipt(_entry_receipt(batch_id, predecessor, store_before, store_after, path), receipt_name)
    # gate 7 — commit + store heads
    ops.git_commit(
        f"chore(queue): {batch_id} entry {p.name} "
        f"(store {store_before[:12]}->{store_after[:12]})"
    )
    return {
        "path": path, "receipt_name": receipt_name,
        "store_before": store_before, "store_after": store_after,
        "payload_changed": store_before != store_after,
    }


def run_queue(ops, entries, ledger, *, batch_id, chain_head, store_head_start) -> dict:
    """Run every entry through the eight gates under one held writer lock.
    Restores agents and writes the linear-chain queue receipt in all exits."""
    result = {"stopped": False, "entries": [], "receipts": []}
    head = chain_head
    with ops.writer_lock(f"bh-queue:{batch_id}"):
        try:
            payload_moved = False
            for path in entries:
                rec = _run_entry(ops, path, ledger, head, batch_id)
                head = rec["receipt_name"]
                result["entries"].append(rec)
                result["receipts"].append(rec["receipt_name"])
                payload_moved = payload_moved or rec["payload_changed"]
                last_store = rec["store_after"]
            # queue end — one --full if any payload moved (§17.1)
            if payload_moved and not ops.verify("full"):
                raise GateStop("<queue-end>", "5-final-full", "final --full verify failed")
        except GateStop as stop:
            result.update(
                stopped=True, stop_entry=stop.entry, stop_gate=stop.gate, stop_detail=stop.detail
            )
        finally:
            result["restored"] = ops.restore()
            store_end = ops.store_head()
            summary = _queue_receipt(batch_id, head, store_head_start, store_end, result)
            result["queue_receipt"] = ops.emit_receipt(
                summary, f"{batch_id}.queue-summary.v1.json"
            )
    return result


def cli(args) -> int:
    repo = paths.resolve_repo()
    queuefile = Path(args.queuefile)
    if not queuefile.exists():
        print(f"bh queue: queuefile not found: {queuefile}")
        return 2
    entries = parse_queuefile(queuefile.read_text(encoding="utf-8"))
    if not entries:
        print(f"bh queue: no entries in {queuefile}")
        return 2
    ledger = promotion.load_ledger(repo)
    ops = QueueOps(repo)
    chain_head = receipts.latest_receipt_name(repo)
    store_start = receipts.store_generation_sha(repo)
    result = run_queue(
        ops, entries, ledger,
        batch_id=args.batch_id, chain_head=chain_head, store_head_start=store_start,
    )
    if result["stopped"]:
        print(
            f"bh queue STOP: entry={result.get('stop_entry')} "
            f"gate={result.get('stop_gate')} — {result.get('stop_detail')}"
        )
        print(f"  restored={result.get('restored')} queue_receipt={result.get('queue_receipt')}")
        return 1
    print(f"bh queue: {len(result['entries'])} entries completed, receipts chained")
    for r in result["receipts"]:
        print(f"  receipt: {r}")
    print(f"  queue_receipt: {result.get('queue_receipt')} restored={result.get('restored')}")
    return 0
