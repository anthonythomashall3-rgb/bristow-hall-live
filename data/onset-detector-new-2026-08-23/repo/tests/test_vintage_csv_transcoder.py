"""B-LAND-1 §2.4 — the ONE counted new shape: a deterministic transcoder that
turns on-disk ALFRED long-CSV as-of vintages into the FRED output_type=2 wide
matrix the EXISTING deep parser (adapters.parse_fred_json_api_vintages_deep)
already admits. No network, no AI, source bytes untouched.

Round-trip invariant (owner's condition): for each in-window vintage file, the
number of landed observations for its .DEEPASOF series equals the file's data
row count. Out-of-window vintages contribute zero (the deep window owns
[2000-01-01, 2019-12-31]; 2020+ is the shallow .ASOF lane's).
"""
from __future__ import absolute_import

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters  # noqa: E402
from live_data.rmv2_live.adapters import normalize  # noqa: E402
from live_data.rmv2_live import vintage_csv_transcoder as vct  # noqa: E402

RETRIEVED_AT = "2026-07-30T05:33:00Z"

# in-window vintages (kept) + one out-of-window (2025 -> dropped by deep parser)
VINTAGE_FILES = {
    "UNRATE_2001-01-15.csv": [("1948-01-01", "3.4"), ("1948-02-01", "3.8")],
    "UNRATE_2009-12-31.csv": [("1948-01-01", "3.4"), ("1948-02-01", "3.9"),
                              ("2009-11-01", "9.9")],
    "UNRATE_2025-07-01.csv": [("1948-01-01", "3.4")],  # out of deep window
}


def _write_corpus(dirpath):
    paths = []
    for name, rows in VINTAGE_FILES.items():
        base, vintage = name[:-4].split("_")  # UNRATE, 2001-01-15
        col = "%s_%s" % (base, vintage.replace("-", ""))
        text = "observation_date,%s\n" % col
        text += "".join("%s,%s\n" % (d, v) for d, v in rows)
        p = Path(dirpath) / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return paths


def unrate_deep_source():
    return {
        "adapter": "fred_json_api_vintages_deep",
        "endpoint": "local-transcode://unrate",
        "information_set_mode": "archive_snapshot_asof",
        "method_version": "unrate_csv_transcode.v1",
        "publisher_release_clock": "irregular America/Chicago",
        "rights_status": "public_government_source_with_attribution",
        "series": {"label": "Unemployment Rate", "series_id": "UNRATE", "unit": "Percent"},
        "source_id": "fred_unrate_api_vintages_deep",
        "value_status": "actual",
    }


class TranscoderTests(unittest.TestCase):
    def test_parse_vintage_csv_reads_base_vintage_rows_and_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _write_corpus(tmp)
            p = next(p for p in paths if p.name == "UNRATE_2009-12-31.csv")
            base, vintage, rows, sha = vct.parse_vintage_csv(p)
            self.assertEqual(base, "UNRATE")
            self.assertEqual(vintage, "20091231")
            self.assertEqual(rows, [("1948-01-01", "3.4"), ("1948-02-01", "3.9"),
                                    ("2009-11-01", "9.9")])
            self.assertEqual(sha, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_round_trip_per_file_rows_equal_landed_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _write_corpus(tmp)
            body, provenance = vct.transcode_base(paths)
            records = normalize(unrate_deep_source(), vct.body_bytes(body), RETRIEVED_AT)
            counts = {}
            for r in records:
                counts[r["series_id"]] = counts.get(r["series_id"], 0) + 1
            # in-window files: landed observations == data row count
            self.assertEqual(counts.get("UNRATE.DEEPASOF20010115"), 2)
            self.assertEqual(counts.get("UNRATE.DEEPASOF20091231"), 3)
            # out-of-window vintage contributes zero landed observations
            self.assertNotIn("UNRATE.DEEPASOF20250701", counts)
            self.assertEqual(sum(counts.values()), 5)  # 2 + 3

    def test_provenance_records_source_sha_and_parser_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _write_corpus(tmp)
            _, provenance = vct.transcode_base(paths)
            self.assertEqual(len(provenance), 3)
            for entry in provenance:
                self.assertEqual(len(entry["source_sha256"]), 64)
                self.assertIn("row_count", entry)
                self.assertEqual(entry["base"], "UNRATE")
            self.assertTrue(vct.TRANSCODER_PARSER_VERSION.startswith("rmv2-live/"))

    def test_mixed_bases_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "UNRATE_2001-01-15.csv").write_text(
                "observation_date,UNRATE_20010115\n1948-01-01,3.4\n", encoding="utf-8")
            (Path(tmp) / "INDPRO_2001-01-15.csv").write_text(
                "observation_date,INDPRO_20010115\n1948-01-01,3.4\n", encoding="utf-8")
            with self.assertRaises(vct.TranscodeError):
                vct.transcode_base(sorted(Path(tmp).glob("*.csv")))


if __name__ == "__main__":
    unittest.main()
