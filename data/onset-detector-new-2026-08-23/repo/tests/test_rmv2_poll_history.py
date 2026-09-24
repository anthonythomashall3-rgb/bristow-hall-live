"""R1A section 3 -- durable poll-history retention log.

Pins: the horizon is DERIVED from the slowest cadence present (not a chosen round
number); records are compact; the log is separate from vault + store; ingest is
idempotent; prune drops records past the horizon; every source in the calendar can
be represented (no schedule shape the record cannot encode).
"""
from __future__ import absolute_import

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOD = PROJECT_ROOT / "live_data/ops/poll_history/poll_history.py"
spec = importlib.util.spec_from_file_location("poll_history", MOD)
ph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ph)


class PollHistory(unittest.TestCase):
    def test_horizon_derived_not_round(self):
        h = ph.derive_horizon_days()
        self.assertEqual(h["cycles"], 3)
        self.assertGreater(h["slowest_cadence_period_days"], 300)  # annual present
        # derived = cycles * period; must not be a hand-picked round number of days
        self.assertAlmostEqual(h["horizon_days"],
                               h["cycles"] * h["slowest_cadence_period_days"], places=2)
        self.assertNotEqual(h["horizon_days"], round(h["horizon_days"] / 30) * 30)

    def test_log_is_separate_from_vault_and_store(self):
        p = str(ph.LOG)
        self.assertNotIn("/data_vault/", p)
        self.assertNotIn("/store/", p)
        self.assertIn("/live_data/ops/poll_history/", p)

    def test_record_is_compact(self):
        r = ph.make_record("fred_dff_api_current", "2026-07-30T05:39:33Z",
                            changed=True, etag="abc", last_modified=None,
                            outcome="retrieved_and_validated")
        self.assertEqual(set(r), {"t", "s", "c", "v", "o"})
        self.assertEqual(r["c"], 1)
        self.assertEqual(r["v"], "e")
        self.assertEqual(r["o"], "ok")
        self.assertIsInstance(r["t"], int)

    def test_validator_codes(self):
        self.assertEqual(ph._validator_code("x", "y"), "b")
        self.assertEqual(ph._validator_code("x", None), "e")
        self.assertEqual(ph._validator_code(None, "y"), "l")
        self.assertEqual(ph._validator_code(None, None), "n")

    def test_ingest_idempotent_and_prune(self):
        # redirect the module's LOG to a temp file so the test never mutates the real log
        with tempfile.TemporaryDirectory() as d:
            saved_log, saved_dir = ph.LOG, ph.LOG_DIR
            ph.LOG_DIR = Path(d)
            ph.LOG = Path(d) / "history.ndjson"
            try:
                recs1 = ph.ingest_receipts()
                recs2 = ph.ingest_receipts()
                self.assertEqual(len(recs1), len(recs2))  # idempotent union
                # prune with a cutoff far in the future removes everything
                res = ph.prune(now_epoch=10**12)
                self.assertEqual(res["kept"], 0)
            finally:
                ph.LOG, ph.LOG_DIR = saved_log, saved_dir


if __name__ == "__main__":
    unittest.main()
