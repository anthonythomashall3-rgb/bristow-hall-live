"""B-ATTEST-REGEN: the two capture attestations must be regenerable.

`data-manifest.json` and `source-receipt.json` had NO generator (B-CTX-1
measured it). Editing any `method_source/**` byte invalidated their rolling
integrity fields with no reproducible way to close them — a §24.6 trap.

These tests pin the generator contract:
  1. It reproduces the CURRENT on-disk bytes exactly (byte-for-byte). A
     generator that cannot reproduce the existing file is a replacement, not a
     generator (brief step 3).
  2. Capture-claim fields (2026-07-29 checkout `233754a`, source capture) are
     preserved verbatim — they do NOT track edits (brief step 2).
  3. Editing a `method_source/**` byte leaves every tracking artifact
     consistent: the rolling fields recompute deterministically and the
     receipt's `manifest_sha256` tracks the regenerated manifest (brief step 6).
"""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from data_vault.scripts import build_capture_attestations as gen


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data-manifest.json"
RECEIPT = ROOT / "source-receipt.json"


class ReproductionTests(unittest.TestCase):
    def test_generator_reproduces_current_manifest_bytes(self):
        produced = gen.build_manifest_text(ROOT)
        self.assertEqual(produced, MANIFEST.read_text(encoding="utf-8"))

    def test_generator_reproduces_current_receipt_bytes(self):
        produced = gen.build_receipt_text(ROOT)
        self.assertEqual(produced, RECEIPT.read_text(encoding="utf-8"))

    def test_capture_fields_preserved_verbatim(self):
        prior = json.loads(MANIFEST.read_text(encoding="utf-8"))
        produced = json.loads(gen.build_manifest_text(ROOT))
        self.assertEqual(produced["captured_on"], prior["captured_on"])
        self.assertEqual(produced["source_checkout"], prior["source_checkout"])
        prior_r = json.loads(RECEIPT.read_text(encoding="utf-8"))
        produced_r = json.loads(gen.build_receipt_text(ROOT))
        for key in (
            "source_url",
            "source_capture_date",
            "source_bytes",
            "source_sha256",
            "transformation",
            "output_file",
            "output_bytes",
            "output_sha256",
        ):
            self.assertEqual(produced_r[key], prior_r[key], key)


class EditCascadeTests(unittest.TestCase):
    """Property test: a method_source edit closes cleanly through the pure
    assemble helpers, without needing a full fake store on disk."""

    def _measurements(self):
        return gen.measure(ROOT)

    def test_method_source_edit_updates_rolling_fields_and_stays_consistent(self):
        prior_m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        prior_r = json.loads(RECEIPT.read_text(encoding="utf-8"))
        meas = self._measurements()

        # Simulate an edit that grows a method_source file by one byte and
        # therefore rehashes DATA_SHA256SUMS.
        edited = copy.deepcopy(meas)
        edited["method_source"]["byte_count"] += 1
        for lane in edited["lanes"]:
            if lane["path"] == "method_source":
                lane["byte_count"] += 1
        edited["sums"]["byte_count"] += 40
        edited["sums"]["sha256"] = hashlib.sha256(b"edited").hexdigest()

        manifest_text = gen.assemble_manifest(prior_m, edited)
        obj = json.loads(manifest_text)
        # method_source rolling fields moved by exactly one byte.
        self.assertEqual(
            obj["method_source_totals"]["byte_count"],
            meas["method_source"]["byte_count"] + 1,
        )
        # non_overlapping (the data-only portion) is unchanged by a
        # method_source edit — it excludes method_source by construction.
        self.assertEqual(
            obj["non_overlapping_data_totals"],
            prior_m["non_overlapping_data_totals"],
        )
        # integrity_manifest tracks the rehashed sums.
        self.assertEqual(obj["integrity_manifest"]["sha256"], edited["sums"]["sha256"])

        receipt_text = gen.assemble_receipt(prior_r, manifest_text, edited)
        robj = json.loads(receipt_text)
        # The receipt's manifest_sha256 tracks the regenerated manifest bytes.
        self.assertEqual(
            robj["data_package"]["manifest_sha256"],
            hashlib.sha256(manifest_text.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            robj["data_package"]["method_source_byte_count"],
            meas["method_source"]["byte_count"] + 1,
        )
        self.assertEqual(
            robj["data_package"]["sha256sums_sha256"], edited["sums"]["sha256"]
        )
        # Capture fields untouched by the edit.
        self.assertEqual(robj["source_sha256"], prior_r["source_sha256"])


if __name__ == "__main__":
    unittest.main()
