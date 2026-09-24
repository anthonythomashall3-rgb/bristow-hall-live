"""B-FAST-1 §2 — per-step admission timing + store-head bounds on the journal.

The admission cost is O(store): a later batch must be able to attribute the
per-cycle cost to a *specific* step from recorded evidence, and to correlate
that cost with the store size at the cycle. Today ``steps[]`` records only
``step``/``ok``/``source_id`` and the cycle record carries neither the
before/after store-head bounds under those names. This test pins the added,
append-only instrumentation:

* every entry in ``record["steps"]`` carries ``started_at``, ``ended_at`` and a
  non-negative integer ``elapsed_ms`` (milliseconds = 3-decimal-second
  precision; the canonical journal bans floats, so seconds are stored as an
  integer millisecond count rather than a float);
* the cycle record carries ``store_heads_before`` and ``store_heads_after``.

It drives the same hermetic fake-ops harness as ``test_rmv2_admission_runner``
so it never touches launchd, the network, or the real store.
"""

from __future__ import absolute_import

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_data.rmv2_admission import runner  # noqa: E402
from test_rmv2_admission_runner import (  # noqa: E402
    FakeOps,
    source_map_for,
    write_project,
)


class AdmissionStepTimingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run_green(self, baseline_head_count=74):
        qp = write_project(self.root, ["fred_a_current", "fred_b_current"])
        ops = FakeOps(
            source_map_for(qp), baseline_head_count=baseline_head_count
        )
        return runner.run_cycle(self.root, qp, ops=ops, process_id=101)

    def test_every_step_carries_timing(self):
        record = self._run_green()
        self.assertTrue(record["steps"], "expected at least one recorded step")
        for step in record["steps"]:
            for field in ("started_at", "ended_at", "elapsed_ms"):
                self.assertIn(
                    field, step,
                    "step %r missing %s" % (step.get("step"), field),
                )
            # int, not bool (bool is an int subclass); canonical journal bans
            # floats, so the elapsed measure must be an integer millisecond.
            self.assertIsInstance(step["elapsed_ms"], int)
            self.assertNotIsInstance(step["elapsed_ms"], bool)
            self.assertGreaterEqual(step["elapsed_ms"], 0)

    def test_cycle_record_carries_store_head_bounds(self):
        record = self._run_green(baseline_head_count=74)
        self.assertIn("store_heads_before", record)
        self.assertIn("store_heads_after", record)
        self.assertEqual(record["store_heads_before"], 74)
        # Two drafts admitted -> two new heads.
        self.assertEqual(record["store_heads_after"], 76)


if __name__ == "__main__":
    unittest.main()
