import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data-manifest.json"
RECEIPT = ROOT / "source-receipt.json"
SUMS = ROOT / "DATA_SHA256SUMS"
INTEGRITY_DOCUMENTATION_EXCLUSIONS = {"data_archive/README.md"}

# Permanent archive ignore-list: macOS Finder artifacts are non-scientific junk
# and must never be blessed into the integrity chain. Excluded from both the lane
# tree counts and the sha256 closure so Finder re-creating one cannot re-poison the
# asserts. See DS_STORE_INTEGRITY_PURGE.v1.json (owner decision, continuation #12).
#
# B-HOUSE-2 (2026-08-06): also exclude Python bytecode. Importing any module
# under method_source (e.g. index_v1.py, pulled in transitively by nowcast_live)
# writes a __pycache__/*.pyc into a payload root. Because these counted as
# payload, the lane-count and sha256-closure asserts passed only when this test
# ran before the first such import and flaked to a spurious 2-fail on any re-run
# or reordered run. Bytecode is never scientific payload; verify_data_vault's own
# is_tree_noise already ignores it. Suffix match catches every __pycache__ member.
def is_integrity_junk(name):
    return (
        name == ".DS_Store"
        or name.startswith("._")
        or name.endswith((".pyc", ".pyo"))
    )


def sha256_path(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_stats(path):
    files = [
        item
        for item in path.rglob("*")
        if item.is_file() and not is_integrity_junk(item.name)
    ]
    return len(files), sum(item.stat().st_size for item in files)


class DataArchiveTests(unittest.TestCase):
    def test_manifested_lane_counts_and_bytes_are_exact(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["schema_version"],
            "recession_monitor_v2.data_manifest.v1",
        )
        for lane in manifest["lanes"]:
            path = ROOT / lane["path"]
            self.assertTrue(path.is_dir(), lane["path"])
            self.assertEqual(
                tree_stats(path),
                (lane["file_count"], lane["byte_count"]),
                lane["lane_id"],
            )

    def test_integrity_manifest_has_exact_set_closure(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        expected = manifest["integrity_manifest"]
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        package = receipt["data_package"]
        self.assertEqual(sha256_path(MANIFEST), package["manifest_sha256"])
        self.assertEqual(expected["sha256"], package["sha256sums_sha256"])
        self.assertEqual(expected["record_count"], package["sha256sums_record_count"])
        self.assertEqual(SUMS.stat().st_size, expected["byte_count"])
        self.assertEqual(sha256_path(SUMS), expected["sha256"])

        rows = SUMS.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), expected["record_count"])
        parsed = {}
        for row in rows:
            digest, rel = row.split("  ", 1)
            self.assertEqual(len(digest), 64)
            self.assertNotIn(rel, parsed)
            self.assertFalse(Path(rel).is_absolute())
            parsed[rel] = digest

        actual = set()
        for dirname in ("data", "data_archive", "method_source"):
            for path in (ROOT / dirname).rglob("*"):
                if path.is_file() and not is_integrity_junk(path.name):
                    relative = path.relative_to(ROOT).as_posix()
                    if relative not in INTEGRITY_DOCUMENTATION_EXCLUSIONS:
                        actual.add(relative)
        self.assertEqual(set(parsed), actual)

    def test_every_included_data_and_method_file_matches_sha256(self):
        for row in SUMS.read_text(encoding="utf-8").splitlines():
            expected, rel = row.split("  ", 1)
            self.assertEqual(sha256_path(ROOT / rel), expected, rel)

    def test_information_lanes_cannot_be_conflated(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        coverage = manifest["information_set_coverage"]
        self.assertEqual(
            [lane["mode"] for lane in coverage["lanes"]],
            [
                "real_time_live_capture",
                "current_revised",
                "archive_snapshot_asof_and_named_provider_vintages",
                "publisher_release_archive_candidates",
                "derived_nowcast_forecast_chronology_and_diagnostic_outputs",
            ],
        )
        rules = manifest["rules"]
        self.assertTrue(
            rules["current_revised_vintage_and_derived_lanes_remain_distinct"]
        )
        self.assertTrue(
            rules["missing_vintage_never_falls_back_silently_to_revised"]
        )
        self.assertTrue(
            rules["provider_vintage_is_not_automatically_strict_first_release"]
        )
        self.assertTrue(
            rules["monthly_or_quarterly_carry_is_not_a_daily_actual"]
        )
        self.assertTrue(rules["quarantined_sources_remain_quarantined"])
        self.assertTrue(
            rules["publication_and_redistribution_rights_not_inferred"]
        )

    def test_independently_downloaded_live_asset_is_present(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        live = manifest["live_asset_verification"]
        path = ROOT / live["path"]
        self.assertTrue(live["exact_live_match"])
        self.assertEqual(sha256_path(path), live["sha256"])


if __name__ == "__main__":
    unittest.main()
