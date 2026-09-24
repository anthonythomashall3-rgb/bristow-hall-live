"""B-LAND-3B §1 — archival config semantics for the enabled:False deep-vintage
class.

Owner ruling 2026-08-05 (wall 5 = FROZEN-ADMISSION): deep vintage families are
archival by nature (as-of snapshots of the past MUST never refresh). An archival
row is additive and honest:

  * config carries ONE additive optional field ``archival: true``; an archival
    row MUST be ``enabled: false`` (else the resident service would fetch and
    clobber the audited offline bytes — B-LAND-1's finding).
  * heads are config-known for snapshot building (build_snapshot includes them,
    the recovery/verify exact-set invariants accept them).
  * status honesty: a BOUND archival family surfaces as ``archival_static``
    (never degraded/failed); an UNBOUND archival family (head absent) is still a
    defect (``archival_unbound`` → service degraded). Bound vs not, never
    silenced.
  * enabled live-source semantics are byte-for-byte unchanged (the 555-test
    suite is the oracle; here we re-prove a normal source has no archival class).
"""
from __future__ import absolute_import

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from live_data.rmv2_live import config as live_config  # noqa: E402
from live_data.rmv2_live import feed_factory  # noqa: E402
from live_data.rmv2_live.canonical import CanonicalDataError  # noqa: E402
from live_data.rmv2_live.pipeline import RefreshPipeline  # noqa: E402

from test_offline_binding import (  # noqa: E402
    AS_OF,
    NFCI_IN_WINDOW_ROWS,
    SeedHttpClient,
    _config,
    _deep_source,
    _nyfed_source,
    _registry,
    _write_nfci_corpus,
)
from live_data.rmv2_live.offline_binding import bind_offline_vintage  # noqa: E402


def _archival_source(base="NFCI", suffix=""):
    """A deep-vintage source in the archival (frozen-admission) class."""
    source = _deep_source(base=base, suffix=suffix)
    source["enabled"] = False
    source["archival"] = True
    return source


class ArchivalConfigSchemaTests(unittest.TestCase):
    """§1.1 — ``archival`` is an additive OPTIONAL boolean; an archival row must
    be enabled:false; the field is truly optional (existing rows omit it)."""

    def _load(self, sources):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "sources.v1.json"
        path.write_text(json.dumps(_config(sources)), encoding="utf-8")
        return live_config.load_config(path)

    def test_archival_enabled_false_source_loads(self):
        config = self._load([_nyfed_source(), _archival_source()])
        archival = [s for s in config["sources"] if s.get("archival")]
        self.assertEqual(len(archival), 1)
        self.assertFalse(archival[0]["enabled"])

    def test_source_without_archival_key_still_loads(self):
        # additive: the 190 existing rows carry no ``archival`` key.
        config = self._load([_nyfed_source()])
        self.assertNotIn("archival", config["sources"][0])

    def test_archival_true_with_enabled_true_is_rejected(self):
        bad = _archival_source()
        bad["enabled"] = True  # a fetchable archival row is a contradiction
        with self.assertRaises(CanonicalDataError):
            self._load([_nyfed_source(), bad])

    def test_non_bool_archival_is_rejected(self):
        bad = _archival_source()
        bad["archival"] = "yes"
        with self.assertRaises(CanonicalDataError):
            self._load([_nyfed_source(), bad])


class ArchivalBindingBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        _registry(self.root)
        self.config = _config([_nyfed_source()])
        self.pipeline = RefreshPipeline(self.root, self.config, SeedHttpClient())
        self.pipeline.refresh()  # seed a live nyfed generation
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        self.csv_paths = _write_nfci_corpus(self.corpus)

    def _bind_archival(self):
        """Bind the deep NFCI vintages, then admit an ARCHIVAL (enabled:false)
        config row for that same source_id."""
        binding_source = _deep_source()  # bind path is agnostic to enabled flag
        outcome = bind_offline_vintage(
            self.pipeline, binding_source, self.csv_paths, AS_OF,
        )
        archival = _archival_source()
        self.pipeline.config["sources"].append(archival)
        return archival, outcome


class ArchivalSnapshotTests(ArchivalBindingBase):
    def test_build_snapshot_includes_archival_head(self):
        # §1.3(a) — an enabled:false archival head is config-known to snapshot.
        archival, _ = self._bind_archival()
        snapshot = self.pipeline.build_snapshot(AS_OF)
        bound_ids = {b["source_id"] for b in snapshot["sources"]}
        self.assertIn(archival["source_id"], bound_ids)
        self.assertIn("nyfed_reference_rates", bound_ids)

    def test_recovery_heads_accept_archival_head(self):
        # the exact-set recovery invariant must treat enabled∪archival as the
        # expected runtime-head set (was: enabled only).
        archival, _ = self._bind_archival()
        runtime_heads = self.pipeline.store.all_source_heads()
        self.assertIn(archival["source_id"], runtime_heads)
        # must not raise:
        self.pipeline._validate_generation_recovery_heads(runtime_heads)


class ArchivalStatusHonestyTests(ArchivalBindingBase):
    def test_bound_archival_is_static_not_degraded(self):
        # §1.2 — bound archival surfaces as archival_static; service stays ready.
        archival, _ = self._bind_archival()
        health, _counts = self.pipeline._current_source_health()
        self.assertEqual(health[archival["source_id"]], "archival_static")
        self.assertEqual(
            self.pipeline._service_state(True, health, False), "ready"
        )

    def test_unbound_archival_is_flagged_and_degrades(self):
        # §1.3(c) — an archival family with NO head in the store is a defect.
        archival = _archival_source()
        self.pipeline.config["sources"].append(archival)  # never bound
        health, _counts = self.pipeline._current_source_health()
        self.assertEqual(health[archival["source_id"]], "archival_unbound")
        self.assertEqual(
            self.pipeline._service_state(True, health, False), "degraded"
        )


class ArchivalRefreshUntouchedTests(ArchivalBindingBase):
    def test_resident_refresh_never_fetches_archival(self):
        # §1.3(b) — the resident inventory/refresh pass leaves archival families
        # untouched: no fetch, head bytes byte-identical after a full refresh.
        archival, _ = self._bind_archival()
        head_path = (
            self.pipeline.store.runtime
            / "source_heads"
            / ("%s.json" % archival["source_id"])
        )
        before = head_path.read_bytes()

        class RecordingClient(SeedHttpClient):
            def fetch(self, source, now=None, conditional_headers=None):
                if source["source_id"] == archival["source_id"]:
                    raise AssertionError("archival family was fetched")
                return super().fetch(
                    source, now=now, conditional_headers=conditional_headers
                )

        self.pipeline.http_client = RecordingClient()
        self.pipeline.refresh()
        self.assertEqual(head_path.read_bytes(), before)


class ArchivalMatrixTests(ArchivalBindingBase):
    def test_archival_source_is_not_an_active_collector_row(self):
        # The source_matrix record-kind contract is fixed (test_rmv2_source_matrix
        # ALLOWED_RECORD_KINDS, D0 §1.2). An archival row must NOT be emitted as
        # an active_collector — the active collectors stay exactly the enabled set.
        from live_data.rmv2_live import matrix as live_matrix

        archival, _ = self._bind_archival()
        coverage = self.pipeline.build_coverage(AS_OF)
        built = live_matrix.build_source_matrix(
            self.root, self.pipeline.config, self.pipeline.store, coverage, AS_OF
        )
        active_ids = {
            row["source_id"]
            for row in built["rows"]
            if row["record_kind"] == "active_collector"
        }
        enabled_ids = {
            s["source_id"] for s in self.pipeline.config["sources"] if s["enabled"]
        }
        self.assertEqual(active_ids, enabled_ids)
        self.assertNotIn(archival["source_id"], active_ids)
        self.assertLessEqual(
            set(Counter(r["record_kind"] for r in built["rows"])),
            {"active_collector", "registered_source_family", "reserved_collector"},
        )


class NonArchivalUnchangedTests(ArchivalBindingBase):
    def test_enabled_live_source_has_no_archival_class(self):
        # §1.3(d) — a normal enabled source is byte-for-byte unaffected: healthy,
        # never archival_static/archival_unbound.
        health, _counts = self.pipeline._current_source_health()
        self.assertEqual(health["nyfed_reference_rates"], "healthy")
        self.assertNotIn(
            health["nyfed_reference_rates"],
            ("archival_static", "archival_unbound"),
        )


class ArchivalCollisionGateTests(ArchivalBindingBase):
    """B-LAND-3C-R2 regression: once an archival head is in the PUBLISHED
    generation, the feed_factory collision gate must treat the generation-member
    set as enabled ∪ archival. Before the fix it used enabled-only, so the first
    bind after any archival family false-tripped 'active generation source set is
    stale or mixed' (190 enabled != 197 published)."""

    def _publish_with_archival(self):
        archival, _ = self._bind_archival()  # binds + admits archival into config
        snapshot = self.pipeline.build_snapshot(AS_OF)
        coverage = self.pipeline.build_coverage(AS_OF)
        status = self.pipeline.build_status(AS_OF, [], snapshot, coverage)
        status["source_matrix"] = {
            "csv_bytes": 0, "csv_sha256": "0" * 64,
            "definition_sha256": "0" * 64, "json_bytes": 0,
            "json_sha256": "0" * 64, "row_count": 0,
        }
        self.pipeline.store.publish_generation(snapshot, status, coverage)
        return archival

    def test_second_bind_after_published_archival_is_not_stale_or_mixed(self):
        self._publish_with_archival()
        # a SECOND legitimate deep base (ICSA) must pass the candidate gate; the
        # published generation now contains an enabled:false archival head.
        second = _deep_source(base="ICSA", suffix="_fredmd")
        # must NOT raise "active generation source set is stale or mixed"
        feed_factory._validate_source_candidate(
            self.pipeline.project_root, self.pipeline.config, second)


if __name__ == "__main__":
    unittest.main()
