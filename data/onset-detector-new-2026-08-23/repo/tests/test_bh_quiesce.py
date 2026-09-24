"""B-SAFE-1 §4.1 — bh quiesce / bh restore contract.

Hermetic: a fake ops object records the call order, so these never touch
launchd. Two invariants the batch names explicitly:

  * quiesce RECORDS the measured prior state of every agent BEFORE it boots
    anything out, and writes it to the state file first.
  * restore REFUSES when the state file is missing (it must not guess a prior
    state), and on a start failure it leaves things down and raises without a
    retry loop.
"""

from __future__ import absolute_import

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bh import quiesce  # noqa: E402
from live_data.rmv2_admission.runner import AGENT_LABELS  # noqa: E402

LIVE_DATA, WATCHDOG, AUTOPILOT = AGENT_LABELS


class FakeOps:
    """Hermetic launchd stand-in with an injected monotonic clock.

    leave_delay models the measured B-SAFE-1 race: `launchctl bootout` returns
    while the SIGTERM'd process is still tearing down, so the label stays
    'loaded' for a short window (same pid), then goes. With leave_delay=0
    bootout removes the label immediately (backward-compatible default).
    """

    def __init__(self, loaded=True, fail_start=None, leave_delay=0.0):
        self.calls = []
        self._loaded = {label: loaded for label in AGENT_LABELS}
        self._fail_start = fail_start
        self._leave_delay = leave_delay
        self._leaves_at = {}   # label -> monotonic time at which bootout completes
        self._clock = 0.0

    def now(self):
        return self._clock

    def sleep(self, seconds):
        self._clock += seconds

    def measure(self, label):
        self.calls.append(("measure", label))
        leaves_at = self._leaves_at.get(label)
        if leaves_at is not None and self._clock >= leaves_at:
            self._loaded[label] = False
        return {"loaded": self._loaded[label], "pid": 100 if self._loaded[label] else None, "last_exit": 0}

    def bootout(self, label):
        self.calls.append(("bootout", label))
        if self._leave_delay <= 0:
            self._loaded[label] = False
        elif label not in self._leaves_at:
            # Teardown is initiated once; re-booting a job that is already tearing
            # down is a no-op and does NOT reset its clock (faithful to launchd).
            self._leaves_at[label] = self._clock + self._leave_delay

    def start(self, label):
        self.calls.append(("start", label))
        if label != self._fail_start:
            self._loaded[label] = True


class QuiesceTests(unittest.TestCase):
    def test_records_prior_state_before_any_bootout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            ops = FakeOps(loaded=True)
            quiesce.quiesce(ops, path)
            # state file exists and captured all three agents as loaded
            self.assertTrue(path.exists())
            prior = json.loads(path.read_text())["prior"]
            self.assertEqual(set(prior), set(AGENT_LABELS))
            self.assertTrue(all(prior[l]["loaded"] for l in AGENT_LABELS))
            # every measure came before the first bootout
            first_bootout = next(i for i, c in enumerate(ops.calls) if c[0] == "bootout")
            measures_before = [c for c in ops.calls[:first_bootout] if c[0] == "measure"]
            self.assertEqual(len(measures_before), len(AGENT_LABELS))

    def test_watchdog_booted_out_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            ops = FakeOps(loaded=True)
            quiesce.quiesce(ops, Path(tmp) / "s.json")
            bootouts = [c[1] for c in ops.calls if c[0] == "bootout"]
            self.assertEqual(bootouts[0], WATCHDOG)
            self.assertEqual(bootouts[-1], LIVE_DATA)

    def test_quiesce_raises_if_agent_survives(self):
        class Stubborn(FakeOps):
            def bootout(self, label):
                self.calls.append(("bootout", label))  # never marks down
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(quiesce.QuiesceError):
                quiesce.quiesce(Stubborn(loaded=True), Path(tmp) / "s.json")

    def test_quiesce_tolerates_async_bootout_teardown(self):
        # The measured B-SAFE-1 race: bootout returns while the process is still
        # tearing down; the label lingers 'loaded' (same pid) briefly, then goes.
        # quiesce must poll until gone and NOT raise a false survivor.
        with tempfile.TemporaryDirectory() as tmp:
            ops = FakeOps(loaded=True, leave_delay=1.5)
            result = quiesce.quiesce(ops, Path(tmp) / "s.json")  # must not raise
            self.assertEqual(set(result["booted_out"]), set(AGENT_LABELS))

    def test_quiesce_fails_closed_and_bounded_when_never_leaves(self):
        # A label that never goes must raise QuiesceError within the 120s budget,
        # never loop unboundedly (§1.7). Virtual clock advances via sleep.
        with tempfile.TemporaryDirectory() as tmp:
            ops = FakeOps(loaded=True, leave_delay=10_000)  # never within budget
            with self.assertRaises(quiesce.QuiesceError):
                quiesce.quiesce(ops, Path(tmp) / "s.json")
            self.assertLessEqual(ops.now(), quiesce.BOOTOUT_BUDGET_S * len(AGENT_LABELS) + 1)
            bootouts = sum(1 for c in ops.calls if c[0] == "bootout")
            self.assertLess(bootouts, 10_000)  # finite — no unbounded retry loop

    def test_quiesce_reboots_out_on_reappearance(self):
        # If a label reappears after leaving, quiesce boots it out again (bounded)
        # and still converges to gone.
        class Flapping(FakeOps):
            def __init__(self, **kw):
                super().__init__(**kw)
                self._first_gone = False
            def measure(self, label):
                m = super().measure(label)
                if label == LIVE_DATA and not m["loaded"] and not self._first_gone:
                    self._first_gone = True
                    self._loaded[label] = True  # reappears once
                    self._leaves_at.pop(label, None)
                    return {"loaded": True, "pid": 100, "last_exit": 0}
                return m
        with tempfile.TemporaryDirectory() as tmp:
            ops = Flapping(loaded=True, leave_delay=0.5)
            quiesce.quiesce(ops, Path(tmp) / "s.json")  # must not raise
            self.assertGreaterEqual(sum(1 for c in ops.calls if c == ("bootout", LIVE_DATA)), 2)


class RestoreTests(unittest.TestCase):
    def test_refuses_when_state_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(quiesce.RestoreError):
                quiesce.restore(FakeOps(), Path(tmp) / "absent.json")

    def test_restores_live_data_first_watchdog_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            quiesce.quiesce(FakeOps(loaded=True), path)
            ops = FakeOps(loaded=False)
            quiesce.restore(ops, path)
            starts = [c[1] for c in ops.calls if c[0] == "start"]
            self.assertEqual(starts[0], LIVE_DATA)
            self.assertEqual(starts[-1], WATCHDOG)

    def test_restore_raises_without_retry_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            quiesce.quiesce(FakeOps(loaded=True), path)
            ops = FakeOps(loaded=False, fail_start=LIVE_DATA)
            with self.assertRaises(quiesce.RestoreError):
                quiesce.restore(ops, path)
            # exactly one start attempt for the failing label — no retry loop
            self.assertEqual(sum(1 for c in ops.calls if c == ("start", LIVE_DATA)), 1)

    def test_outermost_restore_clears_state_file(self):
        # After the only holder releases, the state file is removed so a stale
        # token can never turn the next fresh quiesce into a spurious nested one.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            quiesce.quiesce(FakeOps(loaded=True), path)
            quiesce.restore(FakeOps(loaded=False), path)
            self.assertFalse(path.exists())

    def test_failed_restore_leaves_state_file_for_retry(self):
        # A start failure must NOT delete the token — the operator has to be able
        # to re-run `bh restore` against the recorded prior.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            quiesce.quiesce(FakeOps(loaded=True), path)
            with self.assertRaises(quiesce.RestoreError):
                quiesce.restore(FakeOps(loaded=False, fail_start=LIVE_DATA), path)
            self.assertTrue(path.exists())


class NestedAcquireTests(unittest.TestCase):
    """B-ARCH-1 — idempotent acquire + nested-caller safety (DECISION
    bh-queue-nested-quiesce-state-clobber). A second quiesce against an existing
    hold must PRESERVE the recorded prior (never overwrite the true all-up prior
    with the now-down measurement) and must count the nesting so the inner
    restore does not thaw what the outer caller froze."""

    def test_nested_quiesce_preserves_prior_and_counts_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            quiesce.quiesce(FakeOps(loaded=True), path)  # outer: prior all-up
            # inner caller measures agents already DOWN — must not clobber prior
            result = quiesce.quiesce(FakeOps(loaded=False), path)
            self.assertTrue(result["nested"])
            self.assertEqual(result["depth"], 2)
            prior = json.loads(path.read_text())["prior"]
            self.assertTrue(all(prior[l]["loaded"] for l in AGENT_LABELS))

    def test_regression_manual_prequiesce_then_queue_cycle(self):
        # The exact B-AUTO-1 failure: operator quiesces manually (prior all-up,
        # agents now down), then the queue's gate-2 quiesce + finally-restore run
        # as a NESTED caller. The nested restore must leave agents DOWN (the
        # operator still holds the freeze) while preserving the all-up prior, so
        # the operator's later restore brings all three back.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            quiesce.quiesce(FakeOps(loaded=True), path)      # operator, agents up->down
            quiesce.quiesce(FakeOps(loaded=False), path)     # queue gate-2 (nested)
            inner = FakeOps(loaded=False)
            r_inner = quiesce.restore(inner, path)           # queue finally-restore
            self.assertFalse(r_inner["released"])            # outer still holds
            self.assertEqual([c for c in inner.calls if c[0] == "start"], [])
            self.assertTrue(path.exists())
            outer = FakeOps(loaded=False)
            r_outer = quiesce.restore(outer, path)           # operator restore
            self.assertTrue(r_outer["released"])
            self.assertEqual({l for l in AGENT_LABELS if outer._loaded[l]}, set(AGENT_LABELS))

    def test_nested_quiesce_still_proves_hold_on_revived_agent(self):
        # Idempotent acquire is not a no-op: if an agent revived under the outer
        # hold, the nested acquire must boot it out again and fail closed if it
        # cannot — the freeze is only as good as the last proof.
        class Stubborn(FakeOps):
            def bootout(self, label):
                self.calls.append(("bootout", label))  # never marks down
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            quiesce.quiesce(FakeOps(loaded=True), path)
            with self.assertRaises(quiesce.QuiesceError):
                quiesce.quiesce(Stubborn(loaded=True), path)


class TypedStateTests(unittest.TestCase):
    """B-ARCH-1 — typed quiesce state: a first-class value that round-trips and
    reads legacy v1 (no depth) files as depth 1."""

    def test_state_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            prior = {l: {"loaded": True, "pid": 1, "last_exit": 0} for l in AGENT_LABELS}
            quiesce.QuiesceState(prior=prior, depth=2).dump(path)
            loaded = quiesce.QuiesceState.load(path)
            self.assertEqual(loaded.depth, 2)
            self.assertEqual(loaded.prior, prior)

    def test_legacy_v1_file_loads_as_depth_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            prior = {l: {"loaded": True, "pid": 1, "last_exit": 0} for l in AGENT_LABELS}
            path.write_text(json.dumps({"schema": "bh.quiesce_state.v1", "prior": prior}))
            loaded = quiesce.QuiesceState.load(path)
            self.assertEqual(loaded.depth, 1)

    def test_load_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(quiesce.QuiesceState.load(Path(tmp) / "absent.json"))


if __name__ == "__main__":
    unittest.main()
