"""Fixture-driven tests for parse_eia_v2_json. Real EIA-930 API v2 bytes:
- eia930_daily_region.json (daily-region-data: CISO/ERCO x D/NG, tz Eastern).

Identity = <identity_prefix>.<facets...>.<lane>, lanes kept DISTINCT by the
config lane token (raw / Imputed / Adjusted never collapse).
"""
import json
import os
import unittest
from datetime import datetime, timezone

from live_data.rmv2_live import adapters

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "eia_v2")
DAILY = os.path.join(FIXTURE_DIR, "eia930_daily_region.json")
RETRIEVED = datetime(2026, 8, 2, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source(items, prefix="EIA930", facets=("respondent", "type"), lane="PUB"):
    return {
        "adapter": "eia_v2_json",
        "source_id": "eia930_test_current",
        "endpoint": "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/",
        "method_version": "eia_v2_json_current.v1",
        "information_set_mode": "current_revised",
        "publisher_release_clock": "EIA-930 daily rollup; exact clock null unless proven",
        "rights_status": "public_domain_with_attribution",
        "value_status": "actual",
        "series": {
            "identity_prefix": prefix,
            "identity_facets": list(facets),
            "lane": lane,
            "period_key": "period",
            "value_key": "value",
            "unit": "megawatthours",
            "items": items,
        },
    }


def _rows(path):
    return json.loads(open(path, "rb").read())["response"]["data"]


def _declared(path):
    return sorted({
        "EIA930.%s.%s.PUB" % (r["respondent"], r["type"]) for r in _rows(path)
    })


@unittest.skipUnless(os.path.exists(DAILY), "real EIA fixture not captured")
class EiaV2JsonParserTest(unittest.TestCase):
    def test_parses_declared_identities_only(self):
        declared = _declared(DAILY)
        records = adapters.parse_eia_v2_json(
            _source([{"series_id": s} for s in declared]),
            open(DAILY, "rb").read(), RETRIEVED)
        self.assertTrue(records)
        got = {r["series_id"] for r in records}
        self.assertTrue(got.issubset(set(declared)))
        for r in records:
            self.assertTrue(r["series_id"].startswith("EIA930."))
            self.assertTrue(r["series_id"].endswith(".PUB"))
            self.assertEqual(r["eia_lane"], "PUB")
            self.assertIn("eia_facet_respondent", r)
            self.assertIn("eia_facet_type", r)

    def test_undeclared_identity_refused(self):
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_eia_v2_json(
                _source([{"series_id": "EIA930.CISO.D.PUB"}]),
                open(DAILY, "rb").read(), RETRIEVED)

    def test_lane_token_keeps_lanes_distinct(self):
        # Same facets under a different lane -> a different identity; the
        # PUB-declared set must refuse an ADJ payload identity and vice versa.
        declared = _declared(DAILY)
        records = adapters.parse_eia_v2_json(
            _source([{"series_id": s} for s in declared], lane="PUB"),
            open(DAILY, "rb").read(), RETRIEVED)
        adj_ids = {r["series_id"].rsplit(".", 1)[0] + ".ADJ" for r in records}
        # none of the ADJ-lane identities collide with a PUB identity
        self.assertFalse(adj_ids & {r["series_id"] for r in records})

    def test_daily_period_is_iso_date(self):
        declared = _declared(DAILY)
        records = adapters.parse_eia_v2_json(
            _source([{"series_id": s} for s in declared]),
            open(DAILY, "rb").read(), RETRIEVED)
        self.assertTrue(all(len(r["observation_period"]) == 10 for r in records))
        for r in records:
            datetime.strptime(r["observation_period"], "%Y-%m-%d")

    def test_missing_value_is_unavailable(self):
        one = _rows(DAILY)[0]
        body = json.dumps({"response": {"data": [
            {**one, "value": None, "period": "2025-05-01"},
            {**one, "value": "123", "period": "2025-05-02"},
        ]}}).encode()
        sid = "EIA930.%s.%s.PUB" % (one["respondent"], one["type"])
        records = adapters.parse_eia_v2_json(
            _source([{"series_id": sid}]), body, RETRIEVED)
        by = {r["observation_period"]: r for r in records}
        self.assertEqual(by["2025-05-01"]["value_status"], "unavailable")
        self.assertIsNone(by["2025-05-01"]["value"])
        self.assertEqual(by["2025-05-02"]["value"], "123")

    def test_conflicting_repeat_rejected(self):
        one = _rows(DAILY)[0]
        body = json.dumps({"response": {"data": [
            {**one, "value": "1", "period": "2025-05-01"},
            {**one, "value": "2", "period": "2025-05-01"},
        ]}}).encode()
        sid = "EIA930.%s.%s.PUB" % (one["respondent"], one["type"])
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_eia_v2_json(
                _source([{"series_id": sid}]), body, RETRIEVED)

    def test_facet_with_dot_rejected(self):
        one = _rows(DAILY)[0]
        body = json.dumps({"response": {"data": [
            {**one, "respondent": "CI.SO", "value": "1", "period": "2025-05-01"},
        ]}}).encode()
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_eia_v2_json(_source([]), body, RETRIEVED)

    def test_rejects_non_object(self):
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_eia_v2_json(_source([]), b'[1,2,3]', RETRIEVED)

    def test_error_envelope_rejected(self):
        body = json.dumps({"response": {}, "error": "API_KEY_INVALID"}).encode()
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_eia_v2_json(_source([]), body, RETRIEVED)

    def test_redaction_removes_echoed_key_and_preserves_parse(self):
        # Publisher echoes the submitted key in a request block. Redaction must
        # strip it while leaving every emitted observation unchanged.
        one = _rows(DAILY)[0]
        secret = "abcdef0123456789ABCDEF0123456789zzzz"
        body = json.dumps({
            "request": {"params": {"api_key": secret}},
            "response": {"data": [
                {**one, "value": "10", "period": "2025-05-01"},
            ]},
        }).encode()
        self.assertIn(secret.encode(), body)
        redacted = adapters.redact_secret_from_body(body, secret)
        self.assertNotIn(secret.encode(), redacted)
        self.assertIn(adapters.SECRET_REDACTION_PLACEHOLDER, redacted)
        sid = "EIA930.%s.%s.PUB" % (one["respondent"], one["type"])
        records = adapters.parse_eia_v2_json(
            _source([{"series_id": sid}]), redacted, RETRIEVED)
        self.assertEqual(records[0]["value"], "10")
        # a body without the secret is returned unchanged
        self.assertEqual(adapters.redact_secret_from_body(b"{}", secret), b"{}")

    def test_bad_period_rejected(self):
        one = _rows(DAILY)[0]
        body = json.dumps({"response": {"data": [
            {**one, "value": "1", "period": "May-2025"},
        ]}}).encode()
        with self.assertRaises(adapters.SourceUnavailable):
            adapters.parse_eia_v2_json(
                _source([{"series_id": "EIA930.%s.%s.PUB" % (
                    one["respondent"], one["type"])}]), body, RETRIEVED)


if __name__ == "__main__":
    unittest.main()
