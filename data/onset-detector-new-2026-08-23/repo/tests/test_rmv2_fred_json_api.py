from __future__ import absolute_import

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import (
    PublisherHttpClient,
    SourceUnavailable,
    normalize,
)


RETRIEVED_AT = "2026-07-30T05:33:00Z"
FIX = PROJECT_ROOT / "tests" / "fixtures" / "fred_json_api"
# A deliberately fake sentinel key — the real FRED_API_KEY is never used in tests.
FAKE_KEY = "TESTONLYFAKEKEY0000000000000000z"


def json_source():
    return {
        "adapter": "fred_json_api",
        "allowed_hosts": ["api.stlouisfed.org"],
        "coverage_source_ids": ["fred_current_api"],
        "enabled": True,
        "endpoint": (
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=GDPC1&file_type=json"
        ),
        "expected_content_types": ["application/json"],
        "frequency": "quarterly",
        "information_set_mode": "current_revised",
        "label": "FRED keyed API current lane",
        "max_bytes": 5000000,
        "method_version": "fred_gdpc1_api_current.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Bank of St. Louis (FRED)",
        "publisher_release_clock": "irregular America/Chicago",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": "FRED_API_KEY",
        "secret_required": True,
        "series": {
            "label": "Real Gross Domestic Product",
            "series_id": "GDPC1",
            "unit": "USD billions chained 2017",
        },
        "source_id": "fred_gdpc1_api_current",
        "value_status": "actual",
    }


def graph_source():
    src = json_source()
    src["adapter"] = "fred_graph_csv"
    src["endpoint"] = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPC1"
    src["allowed_hosts"] = ["fred.stlouisfed.org"]
    src["expected_content_types"] = ["text/csv"]
    src["secret_env"] = None
    src["secret_required"] = False
    return src


def read_fixture(name):
    return (FIX / name).read_bytes()


class _FakeHeaders(object):
    def __init__(self, mapping):
        self._m = dict(mapping)

    def items(self):
        return self._m.items()

    def get(self, key, default=None):
        return self._m.get(key, default)


class _FakeResponse(object):
    def __init__(self, url, body):
        self._url = url
        self._body = body
        self.status = 200
        self.headers = _FakeHeaders({"Content-Type": "application/json"})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def geturl(self):
        return self._url

    def getcode(self):
        return 200

    def read(self, n=-1):
        return self._body


class _CaptureOpener(object):
    """Records the exact wire URL the client would open, returns a canned body."""

    def __init__(self, body):
        self._body = body
        self.captured_full_url = None

    def open(self, request, timeout=None):
        self.captured_full_url = request.full_url
        return _FakeResponse(request.full_url, self._body)


class FredJsonCurrentLaneTest(unittest.TestCase):
    def test_current_lane_parses_all_observations(self):
        records = normalize(json_source(), read_fixture("gdpc1_observations.json"), RETRIEVED_AT)
        self.assertEqual(len(records), 318)
        self.assertTrue(all(r["series_id"] == "GDPC1" for r in records))
        self.assertTrue(all(r["source_id"] == "fred_gdpc1_api_current" for r in records))
        self.assertTrue(all(r["provider_vintage_kind"] == "current_revised" for r in records))
        self.assertTrue(all(r["strict_publisher_first_release_proven"] is False for r in records))
        first = records[0]
        self.assertEqual(first["observation_period"], "1947-01-01")
        self.assertEqual(first["value"], "2182.681")
        self.assertEqual(records[-1]["value"], "24270.599")

    def test_provenance_url_carries_no_key(self):
        # The stored endpoint is keyless; provenance must never leak a secret.
        records = normalize(json_source(), read_fixture("gdpc1_observations.json"), RETRIEVED_AT)
        for r in records:
            self.assertNotIn("api_key", r["provenance_url"])

    def test_missing_value_becomes_unavailable(self):
        payload = json.loads(read_fixture("gdpc1_observations.json"))
        payload["observations"][5]["value"] = "."
        body = json.dumps(payload).encode("utf-8")
        records = normalize(json_source(), body, RETRIEVED_AT)
        holed = [r for r in records if r["observation_period"] == payload["observations"][5]["date"]][0]
        self.assertIsNone(holed["value"])
        self.assertEqual(holed["value_status"], "unavailable")

    def test_refuses_to_splice_vintages(self):
        # ALFRED output_type=2 is a multi-vintage payload; the current lane must reject it.
        with self.assertRaises(SourceUnavailable):
            normalize(json_source(), read_fixture("gdpc1_alfred_output2.json"), RETRIEVED_AT)

    @unittest.skipUnless(
        (FIX / "gdpc1_fredgraph.csv").exists(),
        "fredgraph.csv fixture absent (fred.stlouisfed.org host was unreachable at capture)",
    )
    def test_value_parity_with_fredgraph_csv(self):
        json_recs = normalize(json_source(), read_fixture("gdpc1_observations.json"), RETRIEVED_AT)
        csv_recs = normalize(graph_source(), read_fixture("gdpc1_fredgraph.csv"), RETRIEVED_AT)
        json_map = {r["observation_period"]: r["value"] for r in json_recs}
        csv_map = {r["observation_period"]: r["value"] for r in csv_recs}
        common = set(json_map) & set(csv_map)
        self.assertGreater(len(common), 300)
        mismatches = {d: (json_map[d], csv_map[d]) for d in common if json_map[d] != csv_map[d]}
        self.assertEqual(mismatches, {})

    def test_value_parity_with_fred_xml(self):
        # Independent parity: parse the provider's XML serialization here (not via
        # the adapter under test) and require value equality on every common date.
        import xml.etree.ElementTree as ET

        json_recs = normalize(json_source(), read_fixture("gdpc1_observations.json"), RETRIEVED_AT)
        json_map = {r["observation_period"]: r["value"] for r in json_recs if r["value"] is not None}
        root = ET.fromstring(read_fixture("gdpc1_observations.xml"))
        xml_map = {}
        for obs in root.findall("observation"):
            value = obs.get("value")
            if value not in (".", "", None):
                xml_map[obs.get("date")] = value
        common = set(json_map) & set(xml_map)
        self.assertGreater(len(common), 300)
        mismatches = {d: (json_map[d], xml_map[d]) for d in common if json_map[d] != xml_map[d]}
        self.assertEqual(mismatches, {})


class FredJsonSecretHygieneTest(unittest.TestCase):
    def setUp(self):
        self._prev = adapters.os.environ.get("FRED_API_KEY")
        adapters.os.environ["FRED_API_KEY"] = FAKE_KEY

    def tearDown(self):
        if self._prev is None:
            adapters.os.environ.pop("FRED_API_KEY", None)
        else:
            adapters.os.environ["FRED_API_KEY"] = self._prev

    def _fetch_with_capture(self):
        opener = _CaptureOpener(read_fixture("gdpc1_observations.json"))
        orig = adapters.build_opener
        adapters.build_opener = lambda *a, **k: opener
        try:
            client = PublisherHttpClient()
            response = client.fetch(json_source(), now=None)
        finally:
            adapters.build_opener = orig
        return opener, response

    def test_key_reaches_wire_url_but_not_persisted_url(self):
        opener, response = self._fetch_with_capture()
        # The key MUST be present on the wire so the request authenticates,
        self.assertIn("api_key=%s" % FAKE_KEY, opener.captured_full_url)
        # but MUST NOT appear in the persisted response URL (-> provenance/receipts).
        self.assertNotIn("api_key", response.url)
        self.assertNotIn(FAKE_KEY, response.url)
        self.assertEqual(
            response.url,
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=GDPC1&file_type=json",
        )

    def test_request_parameters_hold_no_secret(self):
        _opener, response = self._fetch_with_capture()
        self.assertNotIn(FAKE_KEY, json.dumps(response.request_parameters))
        self.assertNotIn("api_key", json.dumps(response.request_parameters))


if __name__ == "__main__":
    unittest.main()
