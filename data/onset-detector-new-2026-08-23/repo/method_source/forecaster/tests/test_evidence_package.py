import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class EvidencePackageTests(unittest.TestCase):
    def test_accepted_manifest_hashes_every_declared_file(self):
        artifact_root = ROOT / "forecaster" / "artifacts" / "run-p3-20260722-v3"
        manifest = json.loads(
            (artifact_root / "manifest.json").read_text(encoding="utf-8")
        )
        for filename, expected in manifest["files"].items():
            actual = hashlib.sha256((artifact_root / filename).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, filename)
        self.assertFalse(
            json.loads(
                (artifact_root / "scorecard_approximate.json").read_text(
                    encoding="utf-8"
                )
            )["deployment_eligible"]
        )

    def test_required_operator_documents_exist(self):
        for filename in [
            "README.md",
            "MODEL_CARD.md",
            "OPERATIONS.md",
            "ARCHITECTURE.md",
            "EXECUTIVE_READOUT.md",
        ]:
            self.assertTrue((ROOT / "forecaster" / filename).is_file(), filename)

    def test_invalidated_run_cannot_be_mistaken_for_accepted_evidence(self):
        invalid = (
            ROOT
            / "forecaster"
            / "artifacts"
            / "invalid-run-p3-20260722-v2-label-shift"
            / "INVALID.md"
        )
        self.assertIn("none may be used", invalid.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
