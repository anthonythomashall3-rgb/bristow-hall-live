import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from forecaster.api import api_resource
from forecaster.dashboard import render_dashboard
from forecaster.prospective import ForecastLedger


class ApiDashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.ledger_path = root / "ledger.jsonl"
        self.artifact_root = root / "artifacts"
        self.artifact_root.mkdir()
        ForecastLedger(self.ledger_path).append(
            dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
            {
                "status": "experimental_shadow_forecast",
                "issued_at": "2026-01-01T00:00:00+00:00",
                "horizon_probabilities": {"12": 0.2},
                "policy_states": {"12": {"state": "watch"}},
            },
        )
        score = {
            "selection": {"12": "term_spread_logit"},
            "horizons": {
                "12": {
                    "term_spread_logit": {
                        "joint_gate_pass": False,
                        "episode_metrics": {
                            "episode_recall": 0.5,
                            "episode_precision": 0.25,
                        },
                    }
                }
            },
            "historical_joint_gate_pass": False,
            "prospective_confirmation_complete": False,
            "deployment_eligible": False,
        }
        (self.artifact_root / "scorecard_approximate.json").write_text(
            json.dumps(score), encoding="utf-8"
        )
        (self.artifact_root / "manifest.json").write_text(
            json.dumps({"run_id": "test"}), encoding="utf-8"
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_read_only_api_resources(self):
        status, health = api_resource(
            "/health", self.ledger_path, self.artifact_root
        )
        self.assertEqual(status, 200)
        self.assertTrue(health["ok"])
        status, forecast = api_resource(
            "/forecast", self.ledger_path, self.artifact_root
        )
        self.assertEqual(status, 200)
        self.assertEqual(forecast["forecast"]["sequence"], 0)
        status, evidence = api_resource(
            "/evidence", self.ledger_path, self.artifact_root
        )
        self.assertEqual(status, 200)
        self.assertFalse(evidence["deployment_eligible"])

    def test_dashboard_is_explicitly_nonproduction(self):
        page = render_dashboard(self.ledger_path, self.artifact_root)
        self.assertIn("NO ADOPTION", page)
        self.assertIn("20.0%", page)
        self.assertIn("Ledger integrity", page)


if __name__ == "__main__":
    unittest.main()
