"""B-REG-GEO — RED-first tests for the axis-aligned geo-grid adapter.

ONE NEW parser shape (§6.1): `geo_grid_json`. It normalizes the explicit-axis
cross-section shape shared by state_metrics.json (metric-level, monthly axis),
county_hist.json (no metric level, one annual + two monthly blocks) and
county_industry.json (metric-level = NAICS supersectors, annual axis) into
per-(unit, metric) series. Distinct from geo_panel_json (which is dense
offset+values); here each block carries an EXPLICIT period-label axis list that
is zipped positionally with each unit's aligned value list.

Written BEFORE the parser exists in `adapters.normalize` (§5.3).
"""
from __future__ import absolute_import

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import normalize

AS_OF = "2026-08-07T00:00:00Z"


def _src(id_prefix, blocks):
    return {
        "adapter": "geo_grid_json",
        "source_id": "geo_grid_test_current",
        "endpoint": "https://example.gov/geo",
        "information_set_mode": "current_revised",
        "method_version": "geo_grid_offline.v1",
        "publisher_release_clock": "no live release clock; frozen offline snapshot",
        "rights_status": "public_government_data_with_attribution",
        "value_status": "actual",
        "series": {"id_prefix": id_prefix, "blocks": blocks},
    }


class GeoGridAdapterTests(unittest.TestCase):
    def test_metric_level_monthly_axis_with_nulls(self):
        body = json.dumps({
            "months": ["1976-01", "1976-02", "1976-03"],
            "states": {
                "AL": {"iclaims": [59, None, 8], "sahm": [None, None, None]},
                "AK": {"iclaims": [10, 11, 12]},
            },
        }).encode("utf-8")
        src = _src("GEO_STATE_METRICS", [{
            "axis_key": "months",
            "container_key": "states",
            "metric_level": True,
            "metrics": {
                "iclaims": {"unit": "z iclaims"},
                "sahm": {"unit": "z sahm"},
            },
        }])
        recs = normalize(src, body, AS_OF)
        by = {}
        for r in recs:
            by.setdefault(r["series_id"], []).append(
                (r["observation_period"], r["value"])
            )
        # null holes dropped; monthly axis -> YYYY-MM-01
        self.assertEqual(
            by["GEO_STATE_METRICS.AL.iclaims"],
            [("1976-01-01", "59"), ("1976-03-01", "8")],
        )
        # all-null metric emits nothing
        self.assertNotIn("GEO_STATE_METRICS.AL.sahm", by)
        self.assertEqual(
            by["GEO_STATE_METRICS.AK.iclaims"],
            [("1976-01-01", "10"), ("1976-02-01", "11"), ("1976-03-01", "12")],
        )
        self.assertEqual(by["GEO_STATE_METRICS.AL.iclaims"][0], ("1976-01-01", "59"))
        r0 = recs[0]
        self.assertEqual(r0["source_id"], "geo_grid_test_current")
        self.assertEqual(r0["information_set_mode"], "current_revised")

    def test_no_metric_level_multi_block_annual_and_monthly(self):
        body = json.dumps({
            "years": [1990, 1991],
            "mkeys": ["2025-04", "2025-05"],
            "annual": {"01001": [65, 67]},
            "lfm": {"01001": [28911, 29000]},
        }).encode("utf-8")
        src = _src("GEO_COUNTY_HIST", [
            {"axis_key": "years", "container_key": "annual",
             "metric_level": False, "metric_suffix": "ur", "unit": "UR x10 annual"},
            {"axis_key": "mkeys", "container_key": "lfm",
             "metric_level": False, "metric_suffix": "lf_m", "unit": "labor force"},
        ])
        recs = normalize(src, body, AS_OF)
        by = {}
        for r in recs:
            by.setdefault(r["series_id"], []).append(
                (r["observation_period"], r["value"], r["unit"])
            )
        self.assertEqual(
            by["GEO_COUNTY_HIST.01001.ur"],
            [("1990-01-01", "65", "UR x10 annual"),
             ("1991-01-01", "67", "UR x10 annual")],
        )
        self.assertEqual(
            by["GEO_COUNTY_HIST.01001.lf_m"],
            [("2025-04-01", "28911", "labor force"),
             ("2025-05-01", "29000", "labor force")],
        )

    def test_values_preserved_as_strings_and_length_mismatch_zips_overlap(self):
        # a unit whose value list is shorter than the axis zips the overlap only
        body = json.dumps({
            "years": [2014, 2015, 2016],
            "data": {"01001": {"1011": ["199.5", "194"]}},
        }).encode("utf-8")
        src = _src("GEO_COUNTY_INDUSTRY", [{
            "axis_key": "years", "container_key": "data", "metric_level": True,
            "metrics": {"1011": {"unit": "QCEW mining & logging"}},
        }])
        recs = normalize(src, body, AS_OF)
        self.assertEqual(
            [(r["observation_period"], r["value"]) for r in recs],
            [("2014-01-01", "199.5"), ("2015-01-01", "194")],
        )
        self.assertTrue(all(isinstance(r["value"], str) for r in recs))


if __name__ == "__main__":
    unittest.main()
