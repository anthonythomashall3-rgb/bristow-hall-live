from __future__ import absolute_import

import re
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable, normalize


RETRIEVED_AT = "2026-08-02T00:00:00Z"
FIX = PROJECT_ROOT / "tests" / "fixtures" / "dol_ui_archive"
FIXTURE = "report_us_2025_0701_0731.html"

# RED SPEC for the DOL/UI weekly-claims report lane. Dormant (skipped) until the
# parser exists, so the green suite stays green. Parse target is the KEYLESS
# `report.asp` POST HTML (the old page8 HTML era 404s — see ADAPTER_BRIEF CORRECTIONS).
# Contract pinned:
#   * adapter "dol_ui_weekly_claims_report_html"
#   * one record per (week-ending date, measure column) from <td headers="MM/DD/YYYY
#     <colid>">value</td>; week-ending date -> observation_period YYYY-MM-DD
#   * 11 measure columns exactly (initial/continued claims NSA/SF/SA/SA-4wk, IUR NSA/SA,
#     covered employment); any other headered measure -> raise (fail-closed)
#   * values are comma-formatted -> strip commas, canonical decimal; blank/N/A -> unavailable
#   * series_id = "DOL.UI.<COLID uppercased>"; information_set_mode from source (current_revised)
_READY = hasattr(adapters, "parse_dol_ui_weekly_claims_report_html")
_CELL_RE = re.compile(r'<td headers="(\d{2}/\d{2}/\d{4}) ([a-z0-9_]+)"[^>]*>([^<]*)</td>')
_MEASURES = {
    "nsa_initial_claims", "sf_initial_claims", "sa_initial_claims", "sa_4_week_initial_claims",
    "nsa_continued_claims", "sf_continued_claims", "sa_continued_claims", "sa_4_week_continued_claims",
    "nsa_iur", "sa_iur", "cov_employment",
}


def report_source():
    return {
        "adapter": "dol_ui_weekly_claims_report_html",
        "allowed_hosts": ["oui.doleta.gov"],
        "coverage_source_ids": ["dol_ui_national_weekly_release_archive"],
        "enabled": True,
        "endpoint": "https://oui.doleta.gov/unemploy/wkclaims/report.asp",
        "expected_content_types": ["text/html"],
        "frequency": "weekly",
        "information_set_mode": "current_revised",
        "label": "DOL UI weekly claims national report (report.asp HTML)",
        "max_bytes": 8000000,
        "method_version": "dol_ui_weekly_claims_report.v1",
        "poll_seconds": 3600,
        "publisher": "U.S. Department of Labor, Employment and Training Administration",
        "publisher_release_clock": "weekly Thursday 08:30 America/New_York",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {"unit": "count"},
        "source_id": "dol_ui_weekly_claims_report",
        "value_status": "actual",
    }


def read_fixture():
    return (FIX / FIXTURE).read_bytes()


@unittest.skipUnless(_READY, "dol_ui report parser not yet built")
class DolUiReportTest(unittest.TestCase):
    def test_matches_independent_cell_expansion(self):
        body = read_fixture()
        cells = _CELL_RE.findall(body.decode("utf-8"))
        self.assertTrue(cells)
        records = normalize(report_source(), body, RETRIEVED_AT)
        self.assertEqual(len(records), len(cells))
        weeks = {r["observation_period"] for r in records}
        measures = {r["series_id"] for r in records}
        self.assertEqual(len(measures), len(_MEASURES))
        self.assertGreaterEqual(len(weeks), 52)

    def test_series_id_and_comma_strip(self):
        records = normalize(report_source(), read_fixture(), RETRIEVED_AT)
        by = {(r["series_id"], r["observation_period"]): r["value"] for r in records}
        self.assertEqual(by[("DOL.UI.NSA_INITIAL_CLAIMS", "2025-01-04")], "306295")
        self.assertEqual(by[("DOL.UI.SA_INITIAL_CLAIMS", "2025-01-11")], "219000")
        for r in records:
            self.assertRegex(r["series_id"], r"^DOL\.UI\.[A-Z0-9_]+$")
            self.assertEqual(r["information_set_mode"], "current_revised")

    def test_unknown_measure_column_is_rejected(self):
        body = read_fixture().replace(
            b'headers="01/04/2025 nsa_initial_claims"',
            b'headers="01/04/2025 bogus_measure"',
            1,
        )
        with self.assertRaises(SourceUnavailable):
            normalize(report_source(), body, RETRIEVED_AT)


if __name__ == "__main__":
    unittest.main()
