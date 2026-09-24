"""B-LAND-3D — provider-tagged deep lane (Option 2, director ruling
_mailbox/answers/20260805T220347Z_B-LAND-3C-R2.md).

The append-only one-`.DEEPASOF`-lane-per-base invariant blocked a SECOND
provider (FRED-MD) from landing a deep vintage lane on a base ALFRED already
owns (W875RX1). Option 2 makes the invariant one-per-base-PER-PROVIDER,
ADDITIVELY, by having a non-primary provider's deep lane carry a provider tag
in its emitted series ids:

    primary (ALFRED):     <BASE>.DEEPASOF<YYYYMMDD>            (UNCHANGED)
    second provider:      <BASE>.<TAG>.DEEPASOF<YYYYMMDD>      (new, opt-in)

The tag is inserted BEFORE the `.DEEPASOF` token so the two providers' family
prefixes are disjoint in BOTH directions: the tagged prefix never startswith the
bare `<BASE>.DEEPASOF`, and the bare deep prefix never startswith the tagged one.
`.ASOFDEEP` remains prohibited (§7.2). Tags that would re-introduce an `.ASOF`
or `.DEEPASOF` prefix collision are refused at config load.
"""
from __future__ import absolute_import

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters, feed_factory
from live_data.rmv2_live.adapters import normalize
from live_data.rmv2_live.canonical import CanonicalDataError

RETRIEVED_AT = "2026-07-30T05:33:00Z"


def _deep_source(tag=None):
    source = {
        "adapter": "fred_json_api_vintages_deep",
        "allowed_hosts": ["api.stlouisfed.org"],
        "coverage_source_ids": ["fred_md_official_panels"],
        "enabled": True,
        "endpoint": (
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=W875RX1&file_type=json&output_type=2"
            "&realtime_start=2000-01-01&realtime_end=2019-12-31"
        ),
        "expected_content_types": ["application/json"],
        "frequency": "monthly",
        "information_set_mode": "archive_snapshot_asof",
        "label": "FRED-MD reconstructed DEEP vintage lane",
        "max_bytes": 8000000,
        "method_version": "fred_w875rx1_fredmd_panel_vintages_deep.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Bank of St. Louis (McCracken FRED-MD)",
        "publisher_release_clock": "named monthly FRED-MD panel release",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": "FRED_API_KEY",
        "secret_required": True,
        "series": {
            "label": "Real personal income excluding current transfer receipts",
            "series_id": "W875RX1",
            "unit": "Billions of Chained 2017 Dollars",
        },
        "source_id": "fred_w875rx1_fredmd_panel_vintages_deep",
        "value_status": "actual",
    }
    if tag is not None:
        source["vintage_provider_tag"] = tag
    return source


def _deep_payload():
    return json.dumps({
        "file_type": "json",
        "output_type": "2",
        "observations": [
            {"date": "2001-01-01", "W875RX1_20010115": "90.2",
             "W875RX1_20091231": "91.0"},
        ],
    }).encode("utf-8")


class ParserTaggingTests(unittest.TestCase):
    def test_untagged_source_emits_bare_deepasof(self):
        records = normalize(_deep_source(), _deep_payload(), RETRIEVED_AT)
        for r in records:
            self.assertRegex(r["series_id"], r"^W875RX1\.DEEPASOF\d{8}$")

    def test_tagged_source_emits_provider_tagged_family(self):
        records = normalize(_deep_source(tag="FREDMD"), _deep_payload(),
                            RETRIEVED_AT)
        self.assertTrue(records)
        for r in records:
            self.assertRegex(r["series_id"],
                             r"^W875RX1\.FREDMD\.DEEPASOF\d{8}$")

    def test_tagged_ids_never_collide_with_bare_deep_family(self):
        # tagged ids must NOT be captured by the bare <BASE>.DEEPASOF prefix
        records = normalize(_deep_source(tag="FREDMD"), _deep_payload(),
                            RETRIEVED_AT)
        for r in records:
            self.assertFalse(r["series_id"].startswith("W875RX1.DEEPASOF"))
            self.assertFalse(r["series_id"].startswith("W875RX1.ASOF"))


class SuffixGateTests(unittest.TestCase):
    def test_untagged_deep_suffix_unchanged(self):
        self.assertEqual(
            feed_factory._fred_vintage_family_suffix(_deep_source()),
            ".DEEPASOF",
        )

    def test_tagged_deep_suffix_is_provider_scoped(self):
        self.assertEqual(
            feed_factory._fred_vintage_family_suffix(_deep_source(tag="FREDMD")),
            ".FREDMD.DEEPASOF",
        )

    def test_prefixes_are_disjoint_both_directions(self):
        base = "W875RX1"
        alfred = base + feed_factory._fred_vintage_family_suffix(_deep_source())
        fredmd = base + feed_factory._fred_vintage_family_suffix(
            _deep_source(tag="FREDMD"))
        # a realized ALFRED id is NOT captured by the FRED-MD prefix ...
        self.assertFalse(("W875RX1.DEEPASOF20080215").startswith(fredmd))
        # ... and a realized FRED-MD id is NOT captured by the ALFRED prefix.
        self.assertFalse(("W875RX1.FREDMD.DEEPASOF20080101").startswith(alfred))


class ConfigValidationTests(unittest.TestCase):
    import tempfile

    def _load(self, source):
        import tempfile
        from live_data.rmv2_live.config import load_config
        from live_data.rmv2_live.store import canonical_json_bytes
        config = {
            "api": {"host": "127.0.0.1", "port": 8792,
                    "website_poll_seconds": 60},
            "catalog_registry": "registry.csv",
            "schema_version": "recession-monitor-v2.live-data-config.v1",
            "service": {"refresh_tick_seconds": 60},
            "sources": [source],
            "store": {"public": "public", "root": "store", "runtime": "runtime"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            path.write_bytes(canonical_json_bytes(config))
            return load_config(path)

    def test_valid_tag_accepted(self):
        cfg = self._load(_deep_source(tag="FREDMD"))
        self.assertEqual(cfg["sources"][0]["vintage_provider_tag"], "FREDMD")

    def test_absent_tag_still_valid(self):
        cfg = self._load(_deep_source())
        self.assertNotIn("vintage_provider_tag", cfg["sources"][0])

    def test_lowercase_tag_refused(self):
        with self.assertRaises(CanonicalDataError):
            self._load(_deep_source(tag="fredmd"))

    def test_tag_that_would_prefix_collide_refused(self):
        # "ASOF..." or "DEEP..." would re-open the very collision the tag exists
        # to avoid.
        with self.assertRaises(CanonicalDataError):
            self._load(_deep_source(tag="ASOFX"))
        with self.assertRaises(CanonicalDataError):
            self._load(_deep_source(tag="DEEPX"))


if __name__ == "__main__":
    unittest.main()
