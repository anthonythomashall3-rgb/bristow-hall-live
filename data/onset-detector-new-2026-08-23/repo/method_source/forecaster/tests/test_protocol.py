import hashlib
import json
from pathlib import Path
import unittest

from forecaster.protocol import load_protocol, validate_protocol


ROOT = Path(__file__).resolve().parents[2]


class ProtocolTests(unittest.TestCase):
    def test_registered_protocol_has_required_claim_boundaries(self):
        protocol = load_protocol()
        validate_protocol(protocol)
        self.assertEqual(protocol["schema"], "bh.forecaster.protocol.v2")
        self.assertEqual(protocol["target"]["label_source"], "NBER")
        self.assertEqual(protocol["target"]["onset_boundary"], "first_day_of_peak_month")
        self.assertEqual(protocol["horizons_months"], [1, 3, 6, 9, 12, 18, 24])
        self.assertEqual(protocol["historical_evidence_status"], "contaminated_nested_oos")
        self.assertEqual(protocol["untouched_evidence"], "prospective_only")
        self.assertFalse(protocol["claims"]["allow_perfect_forecaster"])
        self.assertEqual(protocol["success"]["episode_recall_target"], 0.95)
        self.assertIn("false_alarm_episodes", protocol["metrics"]["primary"])
        self.assertIn("time_under_warning", protocol["metrics"]["primary"])
        self.assertIn("brier", protocol["metrics"]["secondary"])

    def test_registration_manifest_pins_authority_and_protocol(self):
        manifest_path = ROOT / "forecaster" / "artifacts" / "registration_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for relative in manifest["pinned_files"]:
            expected = manifest["pinned_files"][relative]
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)


if __name__ == "__main__":
    unittest.main()
