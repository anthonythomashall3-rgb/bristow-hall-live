"""Offline unit tests for the SRC1 protocol-driven discovery engine.

Every harvester takes an injectable client, so the whole engine is exercised
with a deterministic in-memory fake — no network, no flakiness, no data
download. These tests pin the invariants SRC1 depends on: metadata-only output,
deterministic measured ranking, the diff against known ids, id-collision
suppression, and the frozen-family reservation gate that makes reservation
writing a human touchpoint (SRC1 §8.4 / §8.7).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bh import discover


class FakeClient:
    """In-memory protocol client. `routes` maps url-substring -> (kind, payload).
    kind is 'json' or 'text' or 'fail'. Records contacts exactly like Fetcher."""

    def __init__(self, routes):
        self.routes = routes
        self.contacts = []

    def _match(self, url):
        for frag, spec in self.routes.items():
            if frag in url:
                return spec
        return ("fail", "NOT_FOUND")

    def get_json(self, protocol, url):
        kind, payload = self._match(url)
        if kind == "json":
            self.contacts.append(discover.Contact(protocol, url, "fake", 200, 10, "RESPONDED"))
            return payload, "RESPONDED"
        self.contacts.append(discover.Contact(protocol, url, "fake", 404, 0, "NOT_FOUND"))
        return None, "NOT_FOUND"

    def get_text(self, protocol, url):
        kind, payload = self._match(url)
        if kind == "text":
            self.contacts.append(discover.Contact(protocol, url, "fake", 200, 10, "RESPONDED"))
            return payload, "RESPONDED"
        self.contacts.append(discover.Contact(protocol, url, "fake", 404, 0, "NOT_FOUND"))
        return None, "NOT_FOUND"


class DbnomicsHarvestTests(unittest.TestCase):
    def test_enumerates_providers_and_flags_archive_route(self):
        client = FakeClient({
            "/providers": ("json", {"providers": {"docs": [
                {"code": "ILO", "name": "ILOSTAT", "region": "World"},
                {"code": "BIS", "name": "Bank for Intl Settlements"},
            ]}}),
            "/last-update": ("json", {"datasets": {"docs": []}}),
        })
        r = discover.harvest_dbnomics(client, max_providers=40)
        self.assertEqual(r.protocol, "DBNOMICS")
        self.assertEqual(len(r.candidates), 2)
        ids = {c["proposed_source_id"] for c in r.candidates}
        self.assertEqual(ids, {"dbnomics_ilo", "dbnomics_bis"})
        for c in r.candidates:
            self.assertEqual(c["asof"]["route"], "DBNOMICS_ARCHIVE")
            # Rights are never inferred from the platform (SRC1 §6.4 / §23).
            self.assertEqual(c["rights_metadata"], "UNRESOLVED")

    def test_provider_endpoint_failure_is_soft(self):
        client = FakeClient({})  # everything 404s
        r = discover.harvest_dbnomics(client)
        self.assertEqual(r.candidates, [])
        self.assertEqual(r.failed, 1)


class SdmxHarvestTests(unittest.TestCase):
    def test_counts_dataflows_and_flags_revision_route(self):
        client = FakeClient({
            "oecd": ("text", "<str:Dataflow id='A'/><str:Dataflow id='B'/>"),
        })
        r = discover.harvest_sdmx(client, endpoints={"OECD": "https://x/oecd"})
        self.assertEqual(len(r.candidates), 1)
        c = r.candidates[0]
        self.assertEqual(c["asof"]["route"], "SDMX_REVISION")
        self.assertEqual(c["series_enumeration"], "unavailable")  # never estimated
        self.assertEqual(c["provenance"]["dataflows_seen"], 2)


class CdxHarvestTests(unittest.TestCase):
    def test_snapshot_density_measured_and_distinct_lane(self):
        client = FakeClient({
            "web.archive.org": ("json", [
                ["timestamp", "statuscode", "digest"],
                ["20081001120000", "200", "AAA"],
                ["20090615120000", "200", "BBB"],
                ["20200401120000", "200", "AAA"],  # identical digest == unchanged
            ]),
        })
        r = discover.harvest_cdx(client, seed_urls=["dol.gov/ui/data.pdf"])
        self.assertEqual(len(r.candidates), 1)
        c = r.candidates[0]
        self.assertEqual(c["asof"]["route"], "CDX_SNAPSHOTS")
        self.assertTrue(c["asof"]["measured"])
        self.assertEqual(c["span"]["start"], "20081001")
        self.assertEqual(c["provenance"]["distinct_digests"], 2)
        self.assertEqual(c["cadence"], "irregular")


class DiffAndRankTests(unittest.TestCase):
    def _cand(self, sid, route="NONE", measured=False, years=0.0, cadence="unknown",
              endpoint=None):
        return discover.make_candidate(
            protocol="T", proposed_source_id=sid, publisher="p", title="t",
            endpoint=endpoint or f"https://e/{sid}", access_url="a",
            asof_route=route, asof_measured=measured, asof_evidence="e",
            cadence=cadence, span={"years": years} if years else None)

    def test_known_id_and_endpoint_are_suppressed(self):
        cands = [self._cand("new_one"), self._cand("known_id"),
                 self._cand("new_two", endpoint="https://known/ep")]
        fresh, suppressed = discover.diff_candidates(
            cands, known_ids={"known_id"}, known_endpoints={"https://known/ep"})
        self.assertEqual({c["proposed_source_id"] for c in fresh}, {"new_one"})
        self.assertEqual(len(suppressed), 2)

    def test_ranking_prefers_asof_then_measured_then_span(self):
        cands = [
            self._cand("z_none"),
            self._cand("a_asof_measured", route="DBNOMICS_ARCHIVE", measured=True, years=5),
            self._cand("b_asof_unmeasured", route="SDMX_REVISION", measured=False, years=50),
            self._cand("c_asof_measured_deep", route="CDX_SNAPSHOTS", measured=True, years=40),
        ]
        ranked = discover.rank_candidates(cands)
        order = [c["proposed_source_id"] for c in ranked]
        # measured as-of first; among measured, deeper span first; none last.
        self.assertEqual(order[0], "c_asof_measured_deep")
        self.assertEqual(order[1], "a_asof_measured")
        self.assertEqual(order[2], "b_asof_unmeasured")
        self.assertEqual(order[3], "z_none")


class ReservationGateTests(unittest.TestCase):
    def test_new_family_reservation_is_blocked_and_shaped(self):
        c = discover.make_candidate(
            protocol="DBNOMICS", proposed_source_id="dbnomics_ilo",
            publisher="ILOSTAT", title="t", endpoint="https://e", access_url="a",
            asof_route="DBNOMICS_ARCHIVE", asof_measured=True, asof_evidence="e")
        prop = discover.proposed_reservation(c, registered_ids={"bea_gdp"})
        # exact 18-field schema, in order, disabled, parser None (SRC1 §8.0)
        self.assertEqual(tuple(prop["row"]), discover.PLANNED_SOURCE_FIELDS)
        self.assertFalse(prop["row"]["enabled"])
        self.assertIsNone(prop["row"]["parser_version"])
        self.assertEqual(prop["row"]["registry_status"], "RESERVED_NOT_ENABLED")
        # blocked: new family not registered -> permanently-human handoff
        self.assertIsNotNone(prop["reservation_blocked_reason"])

    def test_registered_family_reservation_is_writable(self):
        c = discover.make_candidate(
            protocol="DBNOMICS", proposed_source_id="bea_gdp",
            publisher="BEA", title="t", endpoint="https://e", access_url="a",
            asof_route="DBNOMICS_ARCHIVE", asof_measured=True, asof_evidence="e")
        prop = discover.proposed_reservation(c, registered_ids={"bea_gdp"})
        self.assertIsNone(prop["reservation_blocked_reason"])


class OrchestrationTests(unittest.TestCase):
    def test_run_discovery_reports_totals_and_coverage_bound(self):
        client = FakeClient({
            "/providers": ("json", {"providers": {"docs": [
                {"code": "ILO", "name": "ILOSTAT"}]}}),
        })
        result = discover.run_discovery(client, PROJECT_ROOT, live=False)
        self.assertIn("coverage_bound_note", result)
        self.assertIn("asof_capable", result["totals"])
        # metadata only: no candidate carries series data
        for c in result["candidates"]:
            self.assertNotIn("observations", c)
            self.assertNotIn("data", c)
        # registry is derivable from contacts
        reg = discover.build_catalog_registry(result)
        self.assertEqual(reg["schema_version"],
                         "recession-monitor-v2.catalog-registry.v1")
        self.assertEqual(reg["endpoint_count"], len(reg["endpoints"]))


if __name__ == "__main__":
    unittest.main()
