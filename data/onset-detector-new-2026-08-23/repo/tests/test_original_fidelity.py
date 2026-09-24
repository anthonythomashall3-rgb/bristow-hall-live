import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
SOURCE = (
    WORKSPACE
    / "saved"
    / "Codex BHI2 Complex"
    / "payload"
    / "original-monitor"
    / "bhi2-original-live-20260729.html"
)
OUTPUT = ROOT / "index.html"
RECEIPT = ROOT / "source-receipt.json"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class OriginalFidelityTests(unittest.TestCase):
    def test_receipt_and_source_are_exact(self):
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        source = SOURCE.read_bytes()
        self.assertEqual(len(source), receipt["source_bytes"])
        self.assertEqual(sha256(source), receipt["source_sha256"])

    def test_renamed_original_baseline_still_matches_its_frozen_receipt(self):
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        source = SOURCE.read_bytes()
        old = receipt["transformation"]["old"].encode("utf-8")
        new = receipt["transformation"]["new"].encode("utf-8")
        self.assertEqual(
            source.count(old),
            receipt["transformation"]["expected_replacement_count"],
        )
        expected = source.replace(old, new)
        self.assertEqual(len(expected), receipt["output_bytes"])
        self.assertEqual(sha256(expected), receipt["output_sha256"])

    def test_v2_declares_the_original_baseline_as_its_predecessor(self):
        page = OUTPUT.read_text(encoding="utf-8")
        self.assertIn("RMV2 INDEX+WATCH PROJECTION v1", page)
        self.assertIn("The original renamed page remains the frozen predecessor", page)

    def test_visible_product_name_is_v2(self):
        page = OUTPUT.read_text(encoding="utf-8")
        self.assertIn("<title>Recession Monitor V2</title>", page)
        self.assertIn("<h1>Recession Monitor V2</h1>", page)


if __name__ == "__main__":
    unittest.main()
