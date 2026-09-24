"""Regression guard for the B-HOUSE-2 (2026-08-06) Finder-duplicate fix.

macOS Finder copies append " 2" (" 3", ...) before the extension, so a real
payload "DGS2.csv" spawns a junk twin "DGS2 2.csv". These twins are pinned in
the frozen payload manifest, so they stay inventoried as *file* rows, but
build_local_inventory.derive_series_id must not mint them into phantom series
("DGS2 2", "USRECD 2") that leak through local_series_inventory -> metric_catalog
-> the data-gap registry (CH-R25 finding).
"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = ROOT / "data_vault" / "scripts" / "build_local_inventory.py"
_spec = importlib.util.spec_from_file_location("build_local_inventory_under_test", _MODULE_PATH)
bli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bli)


class FinderDuplicateSeriesIdTests(unittest.TestCase):
    def test_finder_duplicate_quarantine_file_mints_no_series(self):
        for rel in (
            "data_archive/current_revised_and_spatial/quarantine/DGS2 2.csv",
            "data_archive/current_revised_and_spatial/quarantine/USRECD 2.csv",
        ):
            self.assertEqual(
                bli.derive_series_id(rel, "quarantined_source_candidate"),
                ("", ""),
                rel,
            )

    def test_finder_duplicate_reference_file_mints_no_series(self):
        self.assertEqual(
            bli.derive_series_id("data/DGS2 3.csv", "national_or_reference_series"),
            ("", ""),
        )

    def test_canonical_series_file_is_unaffected(self):
        series, vintage = bli.derive_series_id(
            "data_archive/current_revised_and_spatial/quarantine/DGS2.csv",
            "quarantined_source_candidate",
        )
        self.assertEqual((series, vintage), ("DGS2", ""))

    def test_series_id_containing_no_space_number_is_unaffected(self):
        # Real FRED identifiers never carry a " <N>" suffix; digits inside the
        # stem (no leading space) must not be mistaken for a Finder twin.
        series, _ = bli.derive_series_id(
            "data/USRECD.csv", "national_or_reference_series"
        )
        self.assertEqual(series, "USRECD")


if __name__ == "__main__":
    unittest.main()
