"""bh queue — the four required gate proofs (B-AUTO-1 §1.40):

(a) clean 2-entry queue runs both, chains receipts
(b) gate failure at entry 2 stops, restores, entry 3 never runs
(c) sha-mismatch runbook refused BEFORE quiesce
(d) writer lock held across the whole run, released on STOP

Uses an injected fake ops seam (the LaunchctlOps pattern) so no launchd, store,
git, or suite is touched.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from bh import promotion, queue


class FakeOps:
    def __init__(self, *, quiesce_ok=True, verify_ok=True, runbook_rc=0, suite_ok=True,
                 store_seq=None):
        self.quiesce_ok = quiesce_ok
        self.verify_ok = verify_ok
        self.runbook_rc = runbook_rc
        self.suite_ok = suite_ok
        self.calls = []
        self.lock_held = False
        self.lock_events = []
        self.receipts = []
        self.commits = []
        self.restored_count = 0
        self._store = iter(store_seq or [])
        self._store_last = "store0000"

    @contextmanager
    def writer_lock(self, label):
        self.lock_held = True
        self.lock_events.append(("acquire", label))
        try:
            yield label
        finally:
            self.lock_held = False
            self.lock_events.append(("release", label))

    def quiesce(self):
        self.calls.append("quiesce")
        return self.quiesce_ok

    def restore(self):
        self.calls.append("restore")
        self.restored_count += 1
        return True

    def verify(self, mode):
        self.calls.append(f"verify:{mode}")
        return self.verify_ok

    def run_runbook(self, path):
        self.calls.append(f"runbook:{Path(path).name}")
        return self.runbook_rc

    def suite(self):
        self.calls.append("suite")
        return self.suite_ok

    def store_head(self):
        try:
            self._store_last = next(self._store)
        except StopIteration:
            pass
        return self._store_last

    def emit_receipt(self, record, filename):
        # assert the writer lock is held whenever we persist (case d)
        assert self.lock_held, "receipt emitted without the writer lock held"
        self.receipts.append((filename, record["chain"]["predecessor_receipt"]))
        return filename

    def git_commit(self, message):
        assert self.lock_held, "git commit without the writer lock held"
        self.commits.append(message)

    def save_ledger(self, ledger):
        self.calls.append("save_ledger")


def _promoted_ledger(paths_):
    ledger = promotion.default_ledger()
    for i, p in enumerate(paths_):
        rid = f"rb{i}"
        promotion.register_runbook(ledger, rid, str(p), read_only=True)
        sha = promotion.sha256_file(Path(p))
        for _ in range(promotion.PROMOTION_CRITERION):
            promotion.record_clean_run(ledger, rid, sha)
    return ledger


def _mk(tmp_path, n):
    out = []
    for i in range(n):
        p = tmp_path / f"chore{i}.sh"
        p.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        out.append(p)
    return out


def test_a_clean_two_entry_queue_chains_receipts(tmp_path):
    rbs = _mk(tmp_path, 2)
    ledger = _promoted_ledger(rbs)
    ops = FakeOps()
    result = queue.run_queue(
        ops, [str(p) for p in rbs], ledger,
        batch_id="B-AUTO-1", chain_head="B-LAND-1_ONDISK_CORPORA.v1.json", store_head_start="s0",
    )
    assert not result["stopped"], result
    assert len(result["entries"]) == 2
    # linear chain: entry0 <- B-LAND-1, entry1 <- entry0, summary <- entry1
    preds = [pred for (_, pred) in ops.receipts]
    assert preds[0] == "B-LAND-1_ONDISK_CORPORA.v1.json"
    assert preds[1] == result["entries"][0]["receipt_name"]
    assert preds[2] == result["entries"][1]["receipt_name"]  # summary
    assert len(ops.commits) == 2


def test_b_gate_fail_entry2_stops_restores_entry3_never_runs(tmp_path):
    rbs = _mk(tmp_path, 3)
    ledger = _promoted_ledger(rbs)
    # runbook exits nonzero -> gate 4 fails on the FIRST entry it reaches;
    # to fail specifically at entry 2 make suite fail only there: use a counter.
    ops = FakeOps()
    calls = {"n": 0}
    real_suite = ops.suite

    def suite_fail_second():
        calls["n"] += 1
        real_suite()
        return calls["n"] != 2  # fail on the 2nd entry's suite gate

    ops.suite = suite_fail_second
    result = queue.run_queue(
        ops, [str(p) for p in rbs], ledger,
        batch_id="B-AUTO-1", chain_head="head.v1.json", store_head_start="s0",
    )
    assert result["stopped"]
    assert result["stop_gate"] == "6-suite"
    assert result["stop_entry"] == str(rbs[1])
    assert len(result["entries"]) == 1  # only entry 1 completed
    assert f"runbook:{rbs[2].name}" not in ops.calls  # entry 3 never ran
    assert ops.restored_count == 1  # restored on STOP


def test_c_sha_mismatch_refused_before_quiesce(tmp_path):
    rbs = _mk(tmp_path, 1)
    ledger = _promoted_ledger(rbs)
    rbs[0].write_text("#!/bin/sh\necho edited\nexit 0\n", encoding="utf-8")  # change bytes
    ops = FakeOps()
    result = queue.run_queue(
        ops, [str(rbs[0])], ledger,
        batch_id="B-AUTO-1", chain_head="head.v1.json", store_head_start="s0",
    )
    assert result["stopped"]
    assert result["stop_gate"] == "1-promotion"
    assert "quiesce" not in ops.calls, "quiesce must not run for a demoted runbook"
    assert "save_ledger" in ops.calls  # demotion persisted


def test_suite_green_predicate_tolerates_only_known_failures():
    known = next(iter(queue.BASELINE_KNOWN_FAILURES))
    # only the known pre-existing failure + baseline errors -> green
    out_ok = f"FAILED {known}\n1 failed, 640 passed, 12 errors in 39s\n"
    assert queue.suite_is_green(out_ok)
    # a NEW failure -> red, even though the count would look the same shape
    out_new = "FAILED tests/test_something_new.py::test_x\n1 failed, 640 passed in 39s\n"
    assert not queue.suite_is_green(out_new)
    # more collection errors than baseline -> red
    out_err = f"FAILED {known}\n1 failed, 600 passed, 13 errors in 39s\n"
    assert not queue.suite_is_green(out_err)
    # fully clean -> green
    assert queue.suite_is_green("650 passed in 40s\n")


def test_d_writer_lock_held_whole_run_released_on_stop(tmp_path):
    rbs = _mk(tmp_path, 2)
    ledger = _promoted_ledger(rbs)
    ops = FakeOps(runbook_rc=1)  # gate 4 fails on entry 1 -> STOP
    result = queue.run_queue(
        ops, [str(p) for p in rbs], ledger,
        batch_id="B-AUTO-1", chain_head="head.v1.json", store_head_start="s0",
    )
    assert result["stopped"]
    # exactly one acquire then one release, in order (held across the whole run)
    assert [e[0] for e in ops.lock_events] == ["acquire", "release"]
    assert not ops.lock_held  # released after STOP
    assert ops.restored_count == 1  # restored while still under the lock
