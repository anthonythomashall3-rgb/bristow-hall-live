"""RED spec for the DEEP ALFRED vintage lane (B1.3b Item 3).

parse_fred_json_api_vintages_deep mirrors parse_fred_json_api_vintages but:
  * adapter "fred_json_api_vintages_deep"
  * emits "<BASE>.DEEPASOF<YYYYMMDD>" (NOT ".ASOFDEEP", which starts with
    ".ASOF" and would collide with the append-only .ASOF family prefix gate in
    feed_factory._validate_source_candidate)
  * keeps ONLY vintages whose as-of date is in the deep window
    [DEEP_VINTAGE_MIN, DEEP_VINTAGE_MAX]; vintages after MAX belong to the
    shallow ".ASOF" lane and are SKIPPED so the two lanes never overlap
  * same output_type=2 requirement, same "." = not-yet-existent -> SKIP rule

DEFINITION CHANGE (B-LAND-5-R2, OWNER RULED 2026-08-06 —
_mailbox/answers/20260805T235206Z_B-LAND-5_ALFRED_DEEP_RELAND.md, Option 2):
The deep lane's lower boundary was widened below 2000 to each source's TRUE
earliest vintage. The old [2000-01-01, 2019-12-31] floor was a proven-scope
artifact, not a scientific boundary. DEEP_VINTAGE_MIN/MAX are now DECLARED,
provenance-tagged parameters in live_data/config/deep_vintage_window.v1.json
(NOT the module-level scientific parameter_registry.v1.json, which is scoped to
method_source/* science constants and pins every entry `inherited` — see that
file's and source_registry_growth_floors.v1.json's `not_the_parameter_registry`
notes). A per-source vintage CAP (earliest-prioritized) guards store growth.
This test is the sanctioned cited pin of that widened definition.
"""
from __future__ import absolute_import

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable, normalize

RETRIEVED_AT = "2026-07-30T05:33:00Z"

# Single source of truth: the declared window parameters the adapter reads.
_WINDOW_CFG = json.loads(
    (PROJECT_ROOT / "live_data" / "config" / "deep_vintage_window.v1.json")
    .read_text(encoding="utf-8")
)
DEEP_MIN = _WINDOW_CFG["deep_vintage_min"]
DEEP_MAX = _WINDOW_CFG["deep_vintage_max"]


def deep_source():
    return {
        "adapter": "fred_json_api_vintages_deep",
        "allowed_hosts": ["api.stlouisfed.org"],
        "coverage_source_ids": ["alfred_provider_reconstructed_vintages"],
        "enabled": True,
        "endpoint": (
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=INDPRO&file_type=json&output_type=2"
            "&realtime_start=2000-01-01&realtime_end=2019-12-31"
        ),
        "expected_content_types": ["application/json"],
        "frequency": "monthly",
        "information_set_mode": "archive_snapshot_asof",
        "label": "FRED keyed API ALFRED DEEP vintage lane",
        "max_bytes": 8000000,
        "method_version": "fred_indpro_api_vintages_deep.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Bank of St. Louis (FRED)",
        "publisher_release_clock": "irregular America/Chicago",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": "FRED_API_KEY",
        "secret_required": True,
        "series": {
            "label": "Industrial Production: Total Index",
            "series_id": "INDPRO",
            "unit": "Index 2017=100",
        },
        "source_id": "fred_indpro_api_vintages_deep",
        "value_status": "actual",
    }


def deep_payload():
    # date rows carry base_<vintage> columns spanning below/in/above the window.
    return json.dumps({
        "file_type": "json",
        "output_type": "2",
        "observations": [
            {
                "date": "2001-01-01",
                "INDPRO_19991231": "90.1",   # below window -> skip
                "INDPRO_20010115": "90.2",    # in window
                "INDPRO_20091231": "91.0",    # in window
                "INDPRO_20191231": "92.5",    # in-window edge (kept)
                "INDPRO_20200101": "93.0",    # shallow lane territory -> skip
            },
            {
                "date": "2005-06-01",
                "INDPRO_20010115": ".",       # not-yet-existent -> skip
                "INDPRO_20091231": "95.4",
                "INDPRO_20200101": "96.1",    # skip (out of window)
            },
        ],
    }).encode("utf-8")


class DeepVintageParserTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            hasattr(adapters, "parse_fred_json_api_vintages_deep"),
            "parse_fred_json_api_vintages_deep is not implemented yet",
        )

    def _records(self):
        return normalize(deep_source(), deep_payload(), RETRIEVED_AT)

    def test_every_record_is_deepasof_typed(self):
        for r in self._records():
            self.assertRegex(r["series_id"], r"^INDPRO\.DEEPASOF\d{8}$")

    def test_only_in_window_vintages_are_emitted(self):
        # DEFINITION CHANGE (B-LAND-5-R2): the pre-2000 vintage 19991231 is now
        # ADMITTED (deep floor widened below 2000); 20200101 stays SKIPPED (it
        # is shallow-lane territory, MAX unchanged).
        vintages = sorted({
            r["series_id"].split(".DEEPASOF")[1] for r in self._records()
        })
        self.assertEqual(
            vintages, ["19991231", "20010115", "20091231", "20191231"]
        )
        for v in vintages:
            self.assertTrue(DEEP_MIN <= v <= DEEP_MAX)

    def test_window_bounds_are_declared_in_config_and_widened(self):
        # The adapter reads its window from the declared parameter file, and the
        # floor was widened below the old [2000,2019] proven-scope artifact.
        self.assertEqual(adapters.DEEP_VINTAGE_MIN, DEEP_MIN)
        self.assertEqual(adapters.DEEP_VINTAGE_MAX, DEEP_MAX)
        self.assertLess(DEEP_MIN, "20000101")
        self.assertEqual(_WINDOW_CFG["provenance"], "chosen")

    def test_pre_2000_vintage_is_admitted(self):
        vintages = {
            r["series_id"].split(".DEEPASOF")[1] for r in self._records()
        }
        self.assertIn("19991231", vintages)

    def test_per_source_cap_keeps_the_earliest_vintages(self):
        # When in-window vintages exceed the source's cap, only the EARLIEST cap
        # vintages are landed (depth beats density pre-2000).
        src = deep_source()
        src["deep_vintage_cap"] = 2
        records = normalize(src, deep_payload(), RETRIEVED_AT)
        vintages = sorted({
            r["series_id"].split(".DEEPASOF")[1] for r in records
        })
        self.assertEqual(vintages, ["19991231", "20010115"])

    def test_dot_cell_is_skipped_not_a_hole(self):
        ids = {(r["series_id"], r["observation_period"]) for r in self._records()}
        # 2005-06-01 @ 20010115 was "." -> must be absent
        self.assertNotIn(("INDPRO.DEEPASOF20010115", "2005-06-01"), ids)
        self.assertIn(("INDPRO.DEEPASOF20091231", "2005-06-01"), ids)

    def test_shallow_asof_prefix_is_never_emitted(self):
        # Guards the collision that forced .DEEPASOF over .ASOFDEEP.
        for r in self._records():
            self.assertFalse(r["series_id"].startswith("INDPRO.ASOF"))

    def test_refuses_output_type_1(self):
        payload = json.loads(deep_payload())
        payload["output_type"] = "1"
        with self.assertRaises(SourceUnavailable):
            normalize(
                deep_source(), json.dumps(payload).encode("utf-8"), RETRIEVED_AT
            )


if __name__ == "__main__":
    unittest.main()
