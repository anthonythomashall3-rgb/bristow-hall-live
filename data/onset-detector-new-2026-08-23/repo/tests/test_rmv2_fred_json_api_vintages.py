from __future__ import absolute_import

import re
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable, normalize


RETRIEVED_AT = "2026-07-30T05:33:00Z"
FIX = PROJECT_ROOT / "tests" / "fixtures" / "fred_json_api"

# This is the RED SPEC for the ALFRED vintage lane. It is dormant (skipped)
# until `parse_fred_json_api_vintages` exists, so the green suite stays green.
# The contract it pins:
#   * adapter "fred_json_api_vintages", method_version "*_api_vintages.v1"
#   * accepts ONLY output_type=2 (wide vintage matrix); refuses output_type=1
#   * columns are "date" + one "<BASE>_<YYYYMMDD>" column per vintage date
#   * emits one record per (observation_period, vintage) where the cell is present
#   * a "." cell means the observation did NOT yet exist as-of that vintage ->
#     SKIP it (do not emit an "unavailable" record; absence is not a hole)
#   * vintage is encoded into the record series_id: "<BASE>.ASOF<YYYYMMDD>"
#   * information_set_mode / provider_vintage_kind = archive_snapshot_asof
_VINTAGE_LANE_READY = hasattr(adapters, "parse_fred_json_api_vintages")
_COL_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.-]*)_(\d{8})$")


def vintages_source():
    return {
        "adapter": "fred_json_api_vintages",
        "allowed_hosts": ["api.stlouisfed.org"],
        "coverage_source_ids": ["alfred_provider_reconstructed_vintages"],
        "enabled": True,
        "endpoint": (
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=GDPC1&file_type=json&output_type=2"
        ),
        "expected_content_types": ["application/json"],
        "frequency": "quarterly",
        "information_set_mode": "archive_snapshot_asof",
        "label": "FRED keyed API ALFRED vintage lane",
        "max_bytes": 8000000,
        "method_version": "fred_gdpc1_api_vintages.v1",
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
        "source_id": "fred_gdpc1_api_vintages",
        "value_status": "actual",
    }


def read_fixture(name):
    return (FIX / name).read_bytes()


def _expected_cells(body, base):
    """Independently recompute expected (series_id, obs, value) from the wide matrix."""
    payload = json.loads(body)
    out = {}
    for row in payload["observations"]:
        obs = row["date"]
        for key, value in row.items():
            if key == "date":
                continue
            m = _COL_RE.match(key)
            assert m and m.group(1) == base, "unexpected column %r" % key
            if value in (".", "", None):
                continue
            out[("%s.ASOF%s" % (base, m.group(2)), obs)] = value
    return out


@unittest.skipUnless(_VINTAGE_LANE_READY, "ALFRED vintage lane parser not yet built")
class FredJsonVintageLaneTest(unittest.TestCase):
    def test_matches_independent_wide_matrix_expansion(self):
        body = read_fixture("gdpc1_alfred_output2.json")
        expected = _expected_cells(body, "GDPC1")
        records = normalize(vintages_source(), body, RETRIEVED_AT)
        got = {(r["series_id"], r["observation_period"]): r["value"] for r in records}
        self.assertEqual(len(records), len(got), "duplicate (series_id, obs) emitted")
        self.assertEqual(got, expected)

    def test_every_record_is_asof_typed(self):
        records = normalize(vintages_source(), read_fixture("gdpc1_alfred_output2.json"), RETRIEVED_AT)
        for r in records:
            self.assertEqual(r["information_set_mode"], "archive_snapshot_asof")
            self.assertEqual(r["provider_vintage_kind"], "archive_snapshot_asof")
            self.assertRegex(r["series_id"], r"^GDPC1\.ASOF\d{8}$")
            self.assertNotIn("api_key", r["provenance_url"])

    def test_refuses_current_lane_output_type_1(self):
        with self.assertRaises(SourceUnavailable):
            normalize(vintages_source(), read_fixture("gdpc1_observations.json"), RETRIEVED_AT)

    def test_refuses_column_not_matching_base_series(self):
        payload = json.loads(read_fixture("gdpc1_alfred_output2.json"))
        payload["observations"][0]["INDPRO_20210101"] = "1.0"
        with self.assertRaises(SourceUnavailable):
            normalize(vintages_source(), json.dumps(payload).encode("utf-8"), RETRIEVED_AT)


if __name__ == "__main__":
    unittest.main()
