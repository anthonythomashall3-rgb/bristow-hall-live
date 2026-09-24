import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecaster.prospective import ForecastLedger, build_shadow_payload


UTC = dt.timezone.utc


class ProspectiveLedgerTests(unittest.TestCase):
    def test_append_is_hash_chained_idempotent_and_prefix_preserving(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ForecastLedger(Path(directory) / "ledger.jsonl")
            first = ledger.append(
                dt.datetime(2026, 1, 1, tzinfo=UTC), {"probability": 0.1}
            )
            self.assertEqual(
                first,
                ledger.append(
                    dt.datetime(2026, 1, 1, tzinfo=UTC), {"probability": 0.1}
                ),
            )
            prefix = ledger.read()
            ledger.append(
                dt.datetime(2026, 1, 2, tzinfo=UTC), {"probability": 0.2}
            )
            current = ledger.read()
            self.assertTrue(ForecastLedger.verify(current)[0])
            self.assertTrue(ForecastLedger.prefix_is_preserved(prefix, current))

    def test_same_issue_cannot_be_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ForecastLedger(Path(directory) / "ledger.jsonl")
            issue = dt.datetime(2026, 1, 1, tzinfo=UTC)
            ledger.append(issue, {"probability": 0.1})
            with self.assertRaises(RuntimeError):
                ledger.append(issue, {"probability": 0.2})

    def test_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ForecastLedger(Path(directory) / "ledger.jsonl")
            ledger.append(
                dt.datetime(2026, 1, 1, tzinfo=UTC), {"probability": 0.1}
            )
            entries = ledger.read()
            entries[0]["payload"]["probability"] = 0.9
            self.assertFalse(ForecastLedger.verify(entries)[0])

    def test_local_issue_day_can_be_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ForecastLedger(Path(directory) / "ledger.jsonl")
            first = dt.datetime(2026, 1, 2, 1, tzinfo=UTC)
            ledger.append(first, {"probability": 0.1})
            later_same_pacific_day = dt.datetime(2026, 1, 2, 7, tzinfo=UTC)
            pacific_standard = dt.timezone(dt.timedelta(hours=-8))
            self.assertEqual(
                ledger.entry_for_local_day(
                    later_same_pacific_day, local_timezone=pacific_standard
                )["sequence"],
                0,
            )

    def test_failed_critical_source_audit_abstains(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            (artifacts / "scorecard_approximate.json").write_text(
                "{}", encoding="utf-8"
            )
            (artifacts / "manifest.json").write_text("{}", encoding="utf-8")
            failed_audit = {
                "ok": False,
                "source_status": {"ICSA": {"status": "stale"}},
            }
            with mock.patch(
                "forecaster.prospective.run_audit", return_value=failed_audit
            ):
                payload = build_shadow_payload(
                    root / "raw",
                    artifacts,
                    dt.datetime(2026, 1, 2, tzinfo=UTC),
                )
        self.assertEqual(payload["status"], "abstained")
        self.assertEqual(payload["horizon_probabilities"], {})
        self.assertFalse(payload["deployment_eligible"])


if __name__ == "__main__":
    unittest.main()
