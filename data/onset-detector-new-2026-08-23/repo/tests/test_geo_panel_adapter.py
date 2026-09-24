"""B-REG-GEO — RED-first tests for the generic offline geo-panel adapter.

One NEW parser shape (§6.1): `geo_panel_json`. It normalizes the
`{container:{unit:{metric:{offset_key, v:[...]}}}}` cross-section shape shared
by metro_econ.json, state_econ.json and county_econ.json (CH-R101 measurement
of record) into per-(unit, metric) series records.

Written BEFORE the parser exists in `adapters.normalize` (§5.3): the dispatch
KeyError / missing-branch makes the parse assertions RED first.
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


def _source(container_key, metrics, id_prefix="GEO_TEST", skip=None):
    return {
        "adapter": "geo_panel_json",
        "source_id": "geo_test_current",
        "endpoint": "https://example.gov/geo",
        "information_set_mode": "current_revised",
        "method_version": "geo_panel_offline.v1",
        "publisher_release_clock": "no live release clock; frozen offline snapshot",
        "rights_status": "public_government_data_with_attribution",
        "value_status": "actual",
        "series": {
            "container_key": container_key,
            "id_prefix": id_prefix,
            "skip_scalar_keys": skip or [],
            "metrics": metrics,
        },
    }


class GeoPanelAdapterTests(unittest.TestCase):
    def test_monthly_quarterly_annual_periods_and_scalar_skip(self):
        body = json.dumps({
            "metros": {
                "AL": {
                    "hpi": {"q0": "1978-Q1", "v": ["48.47", "49.1", None, "50.0"]},
                    "gdp": {"y0": 2001, "v": ["49778", "50100"]},
                    "lf": {"m0": "1976-01", "v": ["1486509", "1485944"]},
                    "cbsa": "13820",
                },
            },
        }).encode("utf-8")
        src = _source(
            "metros",
            {
                "hpi": {"offset_key": "q0", "freq": "q", "unit": "FHFA HPI"},
                "gdp": {"offset_key": "y0", "freq": "a", "unit": "real GDP"},
                "lf": {"offset_key": "m0", "freq": "m", "unit": "labor force"},
            },
            id_prefix="GEO_METRO_ECON",
            skip=["cbsa"],
        )
        recs = normalize(src, body, AS_OF)
        by = {}
        for r in recs:
            by.setdefault(r["series_id"], []).append(r)

        # scalar cbsa never becomes a series
        self.assertNotIn("GEO_METRO_ECON.AL.cbsa", by)

        # quarterly: Q1->01, and the None hole is dropped (not carried as value)
        hpi = by["GEO_METRO_ECON.AL.hpi"]
        self.assertEqual(
            [(r["observation_period"], r["value"]) for r in hpi],
            [("1978-01-01", "48.47"), ("1978-04-01", "49.1"), ("1978-10-01", "50.0")],
        )
        # annual: year->YYYY-01-01, values preserved as source strings
        gdp = by["GEO_METRO_ECON.AL.gdp"]
        self.assertEqual(
            [(r["observation_period"], r["value"]) for r in gdp],
            [("2001-01-01", "49778"), ("2002-01-01", "50100")],
        )
        # monthly: YYYY-MM-01
        lf = by["GEO_METRO_ECON.AL.lf"]
        self.assertEqual(
            [(r["observation_period"], r["value"]) for r in lf],
            [("1976-01-01", "1486509"), ("1976-02-01", "1485944")],
        )
        # base-record fields present and sourced from the source dict
        r0 = hpi[0]
        self.assertEqual(r0["source_id"], "geo_test_current")
        self.assertEqual(r0["information_set_mode"], "current_revised")
        self.assertEqual(r0["unit"], "FHFA HPI")
        self.assertEqual(r0["observed_at"], r0["observation_period"])
        self.assertEqual(r0["value_status"], "actual")

    def test_values_preserved_as_strings_no_float_coercion(self):
        # a value whose float round-trip would change must survive verbatim
        body = json.dumps({
            "data": {"01001": {"pcpi": {"y0": 2010, "v": ["38107.0001", "38108"]}}},
        }).encode("utf-8")
        src = _source(
            "data",
            {"pcpi": {"offset_key": "y0", "freq": "a", "unit": "per-capita income"}},
            id_prefix="GEO_COUNTY_ECON",
        )
        recs = normalize(src, body, AS_OF)
        self.assertEqual([r["value"] for r in recs], ["38107.0001", "38108"])
        self.assertTrue(all(isinstance(r["value"], str) for r in recs))

    def test_empty_or_all_null_metric_emits_no_records(self):
        body = json.dumps({
            "states": {"AL": {"lf": {"m0": "1976-01", "v": [None, None]}}},
        }).encode("utf-8")
        src = _source(
            "states",
            {"lf": {"offset_key": "m0", "freq": "m", "unit": "labor force"}},
        )
        self.assertEqual(normalize(src, body, AS_OF), [])


if __name__ == "__main__":
    unittest.main()
