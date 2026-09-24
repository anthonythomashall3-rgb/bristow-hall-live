"""R1A section 2 -- the APPLIED release calendar.

Pins the outcome of applying R1's frozen proposal to release_calendar.v1.json:
  * the file is canonical (the scheduler's read_json accepts it) and gate-loadable;
  * confidence counts equal R1's derived after-counts (no drift on apply);
  * NO source is silently scheduleless -- every source has either a derived
    next_expected_release_utc or an explicit fallback_interval_seconds (2.3);
  * cdc_resp_publication_history is the single unresolved source at its fallback (2.1);
  * biweekly/annual retain 3600s, recorded non-derivable (2.2);
  * the derived interval AND offset are preserved on every fixed-interval entry;
  * no observed-behaviour entry carries an evidence kind that reads as publisher-stated.
"""
from __future__ import absolute_import

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.canonical import read_json
from live_data.rmv2_live.pipeline import RELEASE_CALENDAR_SCHEMA, load_release_calendar

CALENDAR = PROJECT_ROOT / "live_data/config/release_calendar.v1.json"
PROPOSAL = PROJECT_ROOT / "tools/rmv2_data_cloudflare/generated_live/R1_RELEASE_CALENDAR_DEEPEN.v1.json"
KNOWN_EVIDENCE_KINDS = {
    "fred_series_release+fred_release_dates",
    "publisher_schedule_page",
    # base kinds that survive on entries the proposal did not upgrade past
    "alfred_release_downloaddates+fred_release_series",
    "config_frequency_fallback",
}


class AppliedReleaseCalendar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = read_json(CALENDAR)  # raises if not canonical -> scheduler would reject
        cls.sources = cls.doc["sources"]
        cls.proposal = json.load(open(PROPOSAL))

    def test_canonical_and_gate_loadable(self):
        self.assertEqual(self.doc["schema_version"], RELEASE_CALENDAR_SCHEMA)
        loaded = load_release_calendar(str(PROJECT_ROOT))
        self.assertEqual(len(loaded), 190)

    def test_confidence_counts_match_r1_after(self):
        after = self.proposal["summary"]["after"]
        self.assertEqual(self.doc["confidence_counts"], after)
        self.assertEqual(self.doc["confidence_counts"],
                         {"high": 90, "medium": 99, "unknown": 1})

    def test_no_source_silently_scheduleless(self):
        """2.3: every source has a derived schedule OR an explicit unknown+fallback."""
        for sid, e in self.sources.items():
            has_derived = isinstance(e.get("next_expected_release_utc"), str)
            has_fallback = isinstance(e.get("fallback_interval_seconds"), int)
            self.assertTrue(
                has_derived or has_fallback,
                "%s is silently scheduleless (no next_expected and no fallback)" % sid)
            # confidence must be an explicit tier in every case
            self.assertIn(e.get("confidence"), ("high", "medium", "unknown"), sid)

    def test_single_unresolved_source(self):
        """2.1: cdc_resp_publication_history stays unknown at its fallback."""
        self.assertEqual(self.doc["unresolved_sources"],
                         [{"reason": "publisher_schedule_page",
                           "source_id": "cdc_resp_publication_history"}])
        e = self.sources["cdc_resp_publication_history"]
        self.assertEqual(e["confidence"], "unknown")
        self.assertIsNone(e["next_expected_release_utc"])
        self.assertIsInstance(e["fallback_interval_seconds"], int)

    def test_biweekly_annual_retain_3600(self):
        """2.2: degenerate classes are non-derivable and retain 3600s."""
        pol = self.doc["fallback_class_policy"]
        for cls in ("biweekly", "annual"):
            self.assertFalse(pol[cls]["derivable"], cls)
            self.assertEqual(pol[cls]["interval_seconds"], 3600, cls)

    def test_fixed_interval_entries_preserve_interval_and_offset(self):
        for sid, e in self.sources.items():
            if e.get("scheduler_mode") == "fixed_interval_fallback":
                self.assertIsInstance(e.get("fallback_interval_seconds"), int, sid)
                self.assertIsInstance(e.get("fallback_offset_seconds"), int, sid)

    def test_no_observed_entry_reads_as_publisher_stated(self):
        for sid, e in self.sources.items():
            kind = e.get("evidence", {}).get("kind")
            self.assertIn(kind, KNOWN_EVIDENCE_KINDS, "%s kind=%r" % (sid, kind))
            self.assertNotIn("publisher_stated", (kind or "").replace("-", "_"),
                             "%s evidence.kind masquerades as publisher-stated" % sid)


if __name__ == "__main__":
    unittest.main()
