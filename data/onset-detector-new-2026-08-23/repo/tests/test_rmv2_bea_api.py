"""Fixture-driven tests for parse_bea_api. Real BEA NIPA bytes:
- nipa_t10101_q.json (percent-change index, no commas)
- nipa_t11200_q.json (levels, thousands commas -> comma-strip path)
"""
import json
import os
import unittest
from datetime import datetime, timezone

from live_data.rmv2_live import adapters

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "bea_api")
T10101 = os.path.join(FIXTURE_DIR, "nipa_t10101_q.json")
T11200 = os.path.join(FIXTURE_DIR, "nipa_t11200_q.json")
RETRIEVED = datetime(2026, 8, 2, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source(items, dataset="NIPA"):
    return {
        "adapter": "bea_api",
        "source_id": "bea_nipa_test_current",
        "endpoint": "https://apps.bea.gov/api/data",
        "method_version": "bea_api_current.v1",
        "information_set_mode": "current_revised",
        "publisher_release_clock": "BEA NIPA release schedule; exact clock null unless proven",
        "rights_status": "public_domain_with_attribution_and_third_party",
        "value_status": "actual",
        "series": {"dataset": dataset, "unit": "current_dollars_or_index", "items": items},
    }


def _rows(path):
    results = json.loads(open(path, "rb").read())["BEAAPI"]["Results"]
    if isinstance(results, list):
        results = results[0]
    return results["Data"]


def _declared(path, dataset="NIPA"):
    return sorted({
        "BEA.%s.%s.%s" % (dataset, r["TableName"], r["SeriesCode"])
        for r in _rows(path)
    })


@unittest.skipUnless(os.path.exists(T10101), "real BEA fixture not captured")
class BeaApiParserTest(unittest.TestCase):
    def test_parses_declared_identities_only(self):
        declared = _declared(T10101)
        body = open(T10101, "rb").read()
        records = adapters.parse_bea_api(
            _source([{"series_id": s} for s in declared]), body, RETRIEVED)
        self.assertTrue(records)
        got = {r["series_id"] for r in records}
        self.assertTrue(got.issubset(set(declared)))
        for r in records:
            self.assertTrue(r["series_id"].startswith("BEA.NIPA.T10101."))
            self.assertIn("bea_series_code", r)

    def test_undeclared_identity_refused(self):
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_bea_api(
                _source([{"series_id": "BEA.NIPA.T10101.__none__"}]),
                open(T10101, "rb").read(), RETRIEVED)

    def test_comma_values_are_stripped(self):
        declared = _declared(T11200)
        body = open(T11200, "rb").read()
        records = adapters.parse_bea_api(
            _source([{"series_id": s} for s in declared]), body, RETRIEVED)
        # every available value is canonical decimal with no comma
        for r in records:
            if r["value_status"] != "unavailable":
                self.assertNotIn(",", r["value"])
                self.assertRegex(r["value"], r"^-?\d+(?:\.\d+)?$")
        # at least one row in the source truly had a comma
        self.assertTrue(any("," in str(x["DataValue"]) for x in _rows(T11200)))

    def test_quarterly_period_canonicalized(self):
        declared = _declared(T10101)
        records = adapters.parse_bea_api(
            _source([{"series_id": s} for s in declared]),
            open(T10101, "rb").read(), RETRIEVED)
        self.assertTrue(all(
            len(r["observation_period"]) == 7 and r["observation_period"][4:6] == "-Q"
            for r in records))

    def test_missing_token_is_unavailable(self):
        header_row = _rows(T10101)[0]
        body = json.dumps({"BEAAPI": {"Results": {"Data": [
            {**header_row, "DataValue": "(NA)", "TimePeriod": "2024"},
            {**header_row, "DataValue": "12.3", "TimePeriod": "2025"},
        ]}}}).encode()
        sid = "BEA.NIPA.%s.%s" % (header_row["TableName"], header_row["SeriesCode"])
        records = adapters.parse_bea_api(_source([{"series_id": sid}]), body, RETRIEVED)
        by = {r["observation_period"]: r for r in records}
        self.assertEqual(by["2024"]["value_status"], "unavailable")
        self.assertIsNone(by["2024"]["value"])
        self.assertEqual(by["2025"]["value"], "12.3")

    def test_rejects_non_object(self):
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_bea_api(_source([]), b'[1,2,3]', RETRIEVED)

    def test_envelope_error_rejected(self):
        body = json.dumps({"BEAAPI": {"Error": {"APIErrorCode": "1"}}}).encode()
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_bea_api(_source([]), body, RETRIEVED)


if __name__ == "__main__":
    unittest.main()
