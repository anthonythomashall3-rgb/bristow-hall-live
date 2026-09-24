"""Staged tests for parse_census_eits — copy to tests/test_rmv2_census_api.py in
the pause-block AFTER the real fixture is captured. Fixture-driven: the asserts read
the fixture header/rows so they hold against the REAL bytes, not synthetic assumptions.
"""
import json
import os
import unittest
from datetime import datetime, timezone

from live_data.rmv2_live import adapters

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "census_api")
EITS = os.path.join(FIXTURE_DIR, "eits_resconst.json")
RETRIEVED = datetime(2026, 8, 2, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source(items):
    return {
        "adapter": "census_api",
        "source_id": "census_eits_resconst_current",
        "endpoint": "https://api.census.gov/data/timeseries/eits/resconst",
        "method_version": "census_eits_current.v1",
        "information_set_mode": "current_revised",
        "publisher_release_clock": "census EITS release schedule; exact clock null unless proven",
        "rights_status": "government_data_public_domain_cc0",
        "value_status": "actual",
        "series": {
            "dataset": "resconst",
            "unit": "index_or_count",
            "items": items,
        },
    }


@unittest.skipUnless(os.path.exists(EITS), "real EITS fixture not yet captured")
class CensusEitsParserTest(unittest.TestCase):
    def setUp(self):
        self.body = open(EITS, "rb").read()
        rows = json.loads(self.body)
        self.header = rows[0]
        # enumerate the declared identity set the parser will emit
        idx = {n: i for i, n in enumerate(self.header)}
        ds = "RESCONST"
        self.declared = sorted({
            "CENSUS.EITS.%s.%s.%s.G%s.%s" % (
                ds, r[idx["category_code"]], r[idx["data_type_code"]],
                r[idx["geo_level_code"]],
                "SA" if r[idx["seasonally_adj"]].lower() == "yes" else "NSA",
            ) for r in rows[1:]
        })

    def test_parses_declared_identities_only(self):
        items = [{"series_id": sid} for sid in self.declared]
        records = adapters.parse_census_eits(_source(items), self.body, RETRIEVED)
        self.assertTrue(records)
        got = {r["series_id"] for r in records}
        self.assertTrue(got.issubset(set(self.declared)))
        for r in records:
            self.assertTrue(r["series_id"].startswith("CENSUS.EITS.RESCONST."))
            self.assertIn("category_code", r)
            self.assertIn("data_type_code", r)

    def test_undeclared_identity_is_refused(self):
        # declare a set missing at least one returned combo -> refuse
        items = [{"series_id": "CENSUS.EITS.RESCONST.__none__.__none__.GUS.SA"}]
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_census_eits(_source(items), self.body, RETRIEVED)

    def test_missing_sentinel_is_unavailable(self):
        header = [
            "cell_value", "category_code", "data_type_code",
            "seasonally_adj", "geo_level_code", "time",
        ]
        rows = [
            header,
            ["-666666666", "TOTAL", "TOTAL", "yes", "US", "2024-01"],
            ["1500", "TOTAL", "TOTAL", "yes", "US", "2024-02"],
        ]
        body = json.dumps(rows).encode()
        items = [{"series_id": "CENSUS.EITS.RESCONST.TOTAL.TOTAL.GUS.SA"}]
        records = adapters.parse_census_eits(_source(items), body, RETRIEVED)
        by_period = {r["observation_period"]: r for r in records}
        self.assertEqual(by_period["2024-01"]["value_status"], "unavailable")
        self.assertIsNone(by_period["2024-01"]["value"])
        self.assertEqual(by_period["2024-02"]["value"], "1500")

    def test_census_Z_flag_is_unavailable(self):
        # "Z" is a Census EITS availability flag ("< half the unit shown"), not a
        # number; it appears in marts/mtis/m3. It must map to unavailable, never a 0.
        header = [
            "cell_value", "category_code", "data_type_code",
            "seasonally_adj", "geo_level_code", "time",
        ]
        rows = [
            header,
            ["Z", "TOTAL", "TOTAL", "yes", "US", "2024-01"],
            ["42", "TOTAL", "TOTAL", "yes", "US", "2024-02"],
        ]
        body = json.dumps(rows).encode()
        items = [{"series_id": "CENSUS.EITS.RESCONST.TOTAL.TOTAL.GUS.SA"}]
        records = adapters.parse_census_eits(_source(items), body, RETRIEVED)
        by_period = {r["observation_period"]: r for r in records}
        self.assertEqual(by_period["2024-01"]["value_status"], "unavailable")
        self.assertIsNone(by_period["2024-01"]["value"])
        self.assertEqual(by_period["2024-02"]["value"], "42")

    def test_rejects_non_2d_array(self):
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_census_eits(_source([]), b'{"observations":[]}', RETRIEVED)


if __name__ == "__main__":
    unittest.main()
