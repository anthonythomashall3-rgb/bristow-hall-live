from __future__ import absolute_import

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.rt_intake_validator import (
    PLANNED_SOURCE_FIELDS,
    RESERVATION_REQUIRED_ENTRY_FIELDS,
    IntakeRejection,
    classify_entry,
    reservation_draft,
    run_intake,
)


# A minimal registry entry with every field the validator requires present.
def _entry(**overrides):
    base = {
        "name": "Example RT Source",
        "publisher": "Example Publisher",
        "url": "https://example.org/data",
        "cadence": "weekly",
        "publication_lag": "~5 days",
        "real_time_class": "rt_by_construction",
        "rights_class": "free_with_attribution",
        "rights_evidence": "public page, attribution requested",
        "alive_evidence": "footer Updated 2026-08-03",
        "latest_observation_seen": "2026-07-25",
        "family_mapping": "NEW:example_rt_family",
        "information_set_modes": ["current_revised"],
        "access_method": "csv_download",
        "endpoint_hint": "https://example.org/data.csv",
        "geography": "US",
        "history_start": "2010",
        "sa_status": "SA",
        "revision_policy_claim": "first print revised next period",
        "vintage_archive": "our weekly snapshots",
        "value_hypothesis": "leading",
        "assumptions": "none",
        "domain": "labor_highfreq",
        "candidate_id": "example_rt_source",
        "checked_utc": "2026-08-06T19:00:00Z",
        "verification_tier": "spot_confirmed",
    }
    base.update(overrides)
    return base


class ClassifyEntryTest(unittest.TestCase):
    def test_missing_required_field_is_rejected(self):
        entry = _entry()
        del entry["alive_evidence"]
        verdict = classify_entry(entry, {"example_rt_source": "NEW_FAMILY"})
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason_code, "MISSING_FIELD")
        self.assertIn("alive_evidence", verdict.detail)

    def test_dupe_verdict_from_xcheck_is_rejected(self):
        entry = _entry(candidate_id="freddie_mac_pmms")
        verdict = classify_entry(entry, {"freddie_mac_pmms": "DUPE_EXACT_FAMILY"})
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason_code, "DUPE")
        self.assertIn("DUPE_EXACT_FAMILY", verdict.detail)

    def test_new_family_entry_is_accepted(self):
        entry = _entry()
        verdict = classify_entry(entry, {"example_rt_source": "NEW_FAMILY"})
        self.assertTrue(verdict.accepted)
        self.assertEqual(verdict.dedup_verdict, "NEW_FAMILY")

    def test_entry_not_in_xcheck_map_is_rejected(self):
        entry = _entry()
        verdict = classify_entry(entry, {})
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason_code, "UNXCHECKED")


class ReservationDraftTest(unittest.TestCase):
    def test_draft_has_exact_planned_source_field_order(self):
        entry = _entry()
        draft = reservation_draft(entry, dedup_verdict="NEW_FAMILY",
                                  eligible=True, flagged_rights=False)
        self.assertEqual(tuple(draft), PLANNED_SOURCE_FIELDS)

    def test_draft_is_disabled_and_unparsed(self):
        draft = reservation_draft(_entry(), dedup_verdict="NEW_FAMILY",
                                 eligible=True, flagged_rights=False)
        self.assertFalse(draft["enabled"])
        self.assertIsNone(draft["parser_version"])

    def test_family_id_is_the_only_coverage_and_matches_candidate(self):
        draft = reservation_draft(_entry(candidate_id="example_rt_source"),
                                 dedup_verdict="NEW_FAMILY",
                                 eligible=True, flagged_rights=False)
        self.assertEqual(draft["coverage_source_family_ids"], ["example_rt_source"])
        self.assertEqual(draft["source_id"], "example_rt_source")

    def test_comparator_domain_gets_comparator_role_and_firewall_note(self):
        entry = _entry(domain="nowcasts_composites",
                       candidate_id="conference_board_lei")
        draft = reservation_draft(entry, dedup_verdict="NEW_FAMILY",
                                 eligible=False, flagged_rights=False)
        self.assertEqual(draft["role"], "external_comparator")
        self.assertIn("comparator", draft["split_or_bias_guard"].lower())
        self.assertIn("firewall", draft["split_or_bias_guard"].lower())

    def test_flagged_rights_reservation_carries_lower_priority_status(self):
        draft = reservation_draft(_entry(), dedup_verdict="NEW_FAMILY",
                                 eligible=False, flagged_rights=True)
        self.assertEqual(draft["registry_status"],
                         "RESERVED_LOWER_PRIORITY_NOT_ENABLED")

    def test_plain_new_reservation_is_reserved_not_enabled(self):
        draft = reservation_draft(_entry(), dedup_verdict="NEW_FAMILY",
                                 eligible=True, flagged_rights=False)
        self.assertEqual(draft["registry_status"], "RESERVED_NOT_ENABLED")


class RunIntakeTest(unittest.TestCase):
    def test_run_intake_partitions_and_counts(self):
        entries = [
            _entry(candidate_id="a_new", family_mapping="NEW:a"),
            _entry(candidate_id="b_dupe"),
            _entry(candidate_id="c_missing"),
        ]
        del entries[2]["rights_evidence"]
        verdict_map = {
            "a_new": {"dedup": "NEW_FAMILY", "eligible": True, "flagged": False},
            "b_dupe": {"dedup": "DUPE_EXACT_FAMILY", "eligible": False,
                       "flagged": False},
            "c_missing": {"dedup": "NEW_FAMILY", "eligible": True,
                          "flagged": False},
        }
        result = run_intake(entries, verdict_map)
        self.assertEqual(len(result.reservations), 1)
        self.assertEqual(result.reservations[0]["source_id"], "a_new")
        self.assertEqual(result.counts["rejected_dupe"], 1)
        self.assertEqual(result.counts["rejected_missing_field"], 1)
        self.assertEqual(result.counts["reserved"], 1)

    def test_duplicate_candidate_ids_raise(self):
        entries = [_entry(candidate_id="x"), _entry(candidate_id="x")]
        vm = {"x": {"dedup": "NEW_FAMILY", "eligible": True, "flagged": False}}
        with self.assertRaises(IntakeRejection):
            run_intake(entries, vm)


if __name__ == "__main__":
    unittest.main()
