"""B-UNBLOCK-3 item 1 — the Philadelphia Fed ADS Business Conditions Index
current-vintage workbook parser.

The ADS index is a nowcast/COMPARATOR of real business conditions. This lane is
landed under its own source id and MUST NEVER be a channel member (§10, §22.4).
The parser proves it drops the NBER RECBARS recession-LABEL column, copies
ADS_Index values verbatim, and rejects malformed workbooks.

The fixture is a synthetic minimal xlsx built in-memory (no third-party writer),
plus a round-trip assertion against the real raw-captured bytes when present.
"""
from __future__ import absolute_import

import io
import sys
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.philadelphia_ads import (  # noqa: E402
    PhiladelphiaAdsDataError,
    parse_philadelphia_ads_workbook,
)

SERIES = {
    "series_id": "PHILADELPHIA_ADS_BUSINESS_CONDITIONS_INDEX",
    "unit": "Index (standardized, mean zero)",
    "label": "ADS Business Conditions Index (current vintage)",
}

# The real raw-captured object, byte-identical to what the store holds.
REAL_BLOB = (
    PROJECT_ROOT
    / "live_data/store/objects/sha256/d0"
    / "d05bbdda18fc2b36aa85eb6453bba0d391556abe656cc7bdeaa7503433141473.bin"
)


def _cell(ref, value, is_str, style=""):
    if is_str:
        return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, value)
    return '<c r="%s"><v>%s</v></c>' % (ref, value)


def _build_xlsx(rows):
    """rows: list of (date, ads_value, recbars); row 0 is treated as header."""
    sheet_rows = []
    for i, (a, b, c) in enumerate(rows, start=1):
        is_header = i == 1
        cells = "".join([
            _cell("A%d" % i, a, is_header),
            _cell("B%d" % i, b, is_header),
            _cell("C%d" % i, c, is_header),
        ])
        sheet_rows.append('<row r="%d">%s</row>' % (i, cells))
    sheet = (
        '<?xml version="1.0"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
        '2006/main"><sheetData>%s</sheetData></worksheet>' % "".join(sheet_rows)
    )
    workbook = (
        '<?xml version="1.0"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
        '2006/main"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/>'
        '</sheets></workbook>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


class AdsParserTests(unittest.TestCase):
    def test_parses_values_and_dates(self):
        body = _build_xlsx([
            ("Date", "ADS_Index", "RECBARS"),
            ("1960:03:01", "-0.57562521951981016", "0"),
            ("2026:07:18", "4.8022917043689495E-2", "0"),
        ])
        obs = parse_philadelphia_ads_workbook(SERIES, body)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0]["observation_period"], "1960-03-01")
        self.assertEqual(obs[0]["value"], "-0.57562521951981016")
        self.assertEqual(obs[0]["series_id"], SERIES["series_id"])
        self.assertEqual(obs[0]["unit"], SERIES["unit"])
        # scientific notation round-trips to a plain decimal, no rounding.
        self.assertEqual(obs[1]["observation_period"], "2026-07-18")
        self.assertEqual(obs[1]["value"], "0.048022917043689495")

    def test_recbars_column_never_emitted(self):
        body = _build_xlsx([
            ("Date", "ADS_Index", "RECBARS"),
            ("1980:01:01", "-1.5", "1"),
        ])
        obs = parse_philadelphia_ads_workbook(SERIES, body)
        self.assertEqual({o["series_id"] for o in obs}, {SERIES["series_id"]})
        for o in obs:
            self.assertNotIn("RECBARS", o["series_id"])
            self.assertNotIn("recbars", str(o).lower())

    def test_rejects_wrong_header(self):
        body = _build_xlsx([
            ("Date", "SOMETHING_ELSE", "RECBARS"),
            ("1980:01:01", "-1.5", "0"),
        ])
        with self.assertRaises(PhiladelphiaAdsDataError):
            parse_philadelphia_ads_workbook(SERIES, body)

    def test_rejects_bad_recbars(self):
        body = _build_xlsx([
            ("Date", "ADS_Index", "RECBARS"),
            ("1980:01:01", "-1.5", "2"),
        ])
        with self.assertRaises(PhiladelphiaAdsDataError):
            parse_philadelphia_ads_workbook(SERIES, body)

    def test_rejects_bad_date(self):
        body = _build_xlsx([
            ("Date", "ADS_Index", "RECBARS"),
            ("03/01/1960", "-1.5", "0"),
        ])
        with self.assertRaises(PhiladelphiaAdsDataError):
            parse_philadelphia_ads_workbook(SERIES, body)

    def test_rejects_non_xlsx(self):
        with self.assertRaises(PhiladelphiaAdsDataError):
            parse_philadelphia_ads_workbook(SERIES, b"not a zip")

    def test_round_trip_against_real_blob(self):
        if not REAL_BLOB.is_file():
            self.skipTest("real ADS raw-captured blob not present")
        body = REAL_BLOB.read_bytes()
        obs = parse_philadelphia_ads_workbook(SERIES, body)
        # measured 2026-08-08: 24246 daily rows, 1960-03-01 .. 2026-07-18.
        self.assertEqual(len(obs), 24246)
        self.assertEqual(obs[0]["observation_period"], "1960-03-01")
        self.assertEqual(obs[0]["value"], "-0.57562521951981016")
        self.assertEqual(obs[-1]["observation_period"], "2026-07-18")
        self.assertEqual(obs[-1]["value"], "0.048022917043689495")


if __name__ == "__main__":
    unittest.main()
