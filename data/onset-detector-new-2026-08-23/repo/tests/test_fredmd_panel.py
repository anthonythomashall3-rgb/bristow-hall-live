"""B-LAND-3C-R2 §1 — FRED-MD monthly panel -> output_type=2 transcoder tests.

The proven deep parser (adapters.parse_fred_json_api_vintages_deep) already owns
.DEEPASOF naming, the 2000-2019 deep-window gate and mode tagging. This module's
only job is to reshape ONE requested base column out of the multi-series FRED-MD
panel into the exact wide matrix that parser accepts, tracing provenance to the
ORIGINAL panel bytes. These fixtures pin that reshape and the owner's identity
rule (2026-08-05): a base is matched by EXACT column name; a suffix/alias is a
different id and is never silently mapped onto a canonical name.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live_data"))

from rmv2_live import fredmd_panel as fp  # noqa: E402
from rmv2_live import adapters  # noqa: E402


PANEL_1999_08 = (
    "sasdate,RPI,W875RX1,CMRMTSPLx,CLAIMSx\n"
    "Transform:,5,5,5,5\n"
    "01/01/1999,1000.5,900.1,200000.0,300.0\n"
    "02/01/1999,1001.5,901.1,201000.0,.\n"       # '.' CLAIMSx cell -> skipped
    "03/01/1999,1002.5,,202000.0,302.0\n"        # empty W875RX1 cell -> skipped
)

PANEL_2001_06 = (
    "sasdate,RPI,W875RX1,CMRMTSPLx,CLAIMSx\n"
    "Transform:,5,5,5,5\n"
    "01/01/1999,1000.7,900.3,200010.0,300.5\n"   # same period, later vintage
    "01/01/2001,1100.0,950.0,210000.0,320.0\n"
)


def _write(dirpath, name, text):
    p = Path(dirpath) / name
    p.write_text(text, encoding="utf-8")
    return str(p)


class TestVintageDate(unittest.TestCase):
    def test_extracts_yyyymm_from_varied_filenames(self):
        self.assertEqual(fp.vintage_yyyymmdd("1999-08.csv"), "19990801")
        self.assertEqual(fp.vintage_yyyymmdd("FRED-MD_2024m12.csv"), "20241201")
        self.assertEqual(fp.vintage_yyyymmdd("fred_md_2026-06.csv"), "20260601")

    def test_rejects_filename_without_month(self):
        with self.assertRaises(fp.PanelTranscodeError):
            fp.vintage_yyyymmdd("not_a_vintage.csv")


class TestTranscodeBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.f99 = _write(self.tmp, "1999-08.csv", PANEL_1999_08)
        self.f01 = _write(self.tmp, "2001-06.csv", PANEL_2001_06)
        self.source_w875 = {"series": {"series_id": "W875RX1"}}
        self.source_claims = {"series": {"series_id": "CLAIMSx"}}

    def test_selects_only_requested_base_column(self):
        body, prov = fp.transcode_base([self.f99], source=self.source_w875)
        # only W875RX1_<vintage> columns appear, never RPI/CLAIMSx/CMRMTSPLx
        cols = set()
        for row in body["observations"]:
            cols.update(k for k in row if k != "date")
        self.assertEqual(cols, {"W875RX1_19990801"})

    def test_sasdate_converted_to_iso_and_transform_row_skipped(self):
        body, _ = fp.transcode_base([self.f99], source=self.source_w875)
        dates = [r["date"] for r in body["observations"]]
        # 03/01/1999 W875RX1 empty -> that date absent for W875RX1
        self.assertEqual(dates, ["1999-01-01", "1999-02-01"])
        self.assertNotIn("Transform:", dates)

    def test_dot_and_empty_cells_skipped(self):
        body, _ = fp.transcode_base([self.f99], source=self.source_claims)
        # CLAIMSx: 01/1999 present, 02/1999 '.', 03/1999 present
        pairs = {r["date"]: r["CLAIMSx_19990801"] for r in body["observations"]}
        self.assertEqual(pairs, {"1999-01-01": "300.0", "1999-03-01": "302.0"})

    def test_provenance_traces_original_panel_bytes(self):
        import hashlib
        body, prov = fp.transcode_base([self.f99], source=self.source_w875)
        self.assertEqual(len(prov), 1)
        entry = prov[0]
        self.assertEqual(entry["base"], "W875RX1")
        self.assertEqual(entry["vintage"], "19990801")
        self.assertEqual(entry["source_path"], self.f99)
        expect = hashlib.sha256(Path(self.f99).read_bytes()).hexdigest()
        self.assertEqual(entry["source_sha256"], expect)
        self.assertEqual(entry["transform_code"], "5")

    def test_multi_vintage_wide_matrix_and_deep_parser_roundtrip(self):
        body, prov = fp.transcode_base(
            [self.f99, self.f01], source=self.source_w875
        )
        # two vintage columns for the shared 1999-01 period
        row99 = next(r for r in body["observations"] if r["date"] == "1999-01-01")
        self.assertEqual(row99["W875RX1_19990801"], "900.1")
        self.assertEqual(row99["W875RX1_20010601"], "900.3")
        # feed the proven deep parser: emits W875RX1.DEEPASOF<vintage>, 2000-2019
        source = {
            "adapter": "fred_json_api_vintages_deep",
            "information_set_mode": "archive_snapshot_asof",
            "endpoint": "offline://fred_md_official_panels",
            "method_version": "fredmd_w875rx1_panel_vintages_deep.v1",
            "publisher_release_clock": "named panel monthly release",
            "rights_status": "FRED_terms_and_underlying_publisher_rights_control",
            "source_id": "fred_w875rx1_fredmd_panel_vintages_deep",
            "value_status": "actual",
            "series": {
                "series_id": "W875RX1",
                "label": "Real personal income ex current transfer receipts",
                "unit": "Billions of Chained 2017 Dollars",
            },
        }
        records = adapters.parse_fred_json_api_vintages_deep(
            source, fp.body_bytes(body), "2026-08-05T00:00:00Z"
        )
        series = {r["series_id"] for r in records}
        # DEFINITION CHANGE (B-LAND-5-R2, owner-ruled 2026-08-06,
        # _mailbox/answers/20260805T235206Z_B-LAND-5_ALFRED_DEEP_RELAND.md):
        # the deep floor was widened below 2000, so the 1999-08 vintage is now
        # ADMITTED alongside 2001-06 (was dropped under the old [2000,2019]
        # proven-scope artifact). See deep_vintage_window.v1.json.
        self.assertEqual(
            series,
            {"W875RX1.DEEPASOF19990801", "W875RX1.DEEPASOF20010601"},
        )

    def test_duplicate_vintage_cell_rejected(self):
        dup = _write(self.tmp, "dup-1999-08.csv", PANEL_1999_08)
        # same YYYY-MM vintage -> same column -> duplicate cell must be refused
        os.rename(dup, str(Path(self.tmp) / "other_1999-08.csv"))
        with self.assertRaises(fp.PanelTranscodeError):
            fp.transcode_base(
                [self.f99, str(Path(self.tmp) / "other_1999-08.csv")],
                source=self.source_w875,
            )

    def test_missing_base_column_rejected(self):
        with self.assertRaises(fp.PanelTranscodeError):
            fp.transcode_base(
                [self.f99], source={"series": {"series_id": "NOPE"}}
            )

    def test_source_without_base_rejected(self):
        with self.assertRaises(fp.PanelTranscodeError):
            fp.transcode_base([self.f99], source=None)

    def test_parser_version_names_the_fredmd_shape(self):
        self.assertIn("fredmd_panel", fp.TRANSCODER_PARSER_VERSION)


if __name__ == "__main__":
    unittest.main()
