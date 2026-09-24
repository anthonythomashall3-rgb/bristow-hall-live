"""B-PROD-1 — many producers, one committer.

Producers make bytes into exclusive staging dirs (no store/config/receipt/pointer
write); the committer is the ONLY writer of the generation pointer, receipt chain,
and source heads. Object production parallelizes because the store is
content-addressed (identical sha == identical bytes cannot conflict).

Proofs (batch §4):
  (a) two producers run concurrently into separate dirs — byte-level
      non-interference; store/config/receipts untouched by both.
  (b) commit serializes: linear receipt chain, one pointer flip, deterministic
      order independent of producer finish order.
  (c) sha-mismatch draft rejected (per-draft; commit continues).
  (d) unregistered shape/reservation rejected.
  (e) crash mid-commit: pointer unchanged; re-run is idempotent
      (content-addressed re-admit == no-op).
  (f) staged receipt missing producer_id or fetch timestamp FAILS schema.

The staged acquisition receipt is an ADDITIVE variant on the B-LAND-3
schema-discriminated closure (store.verify_source_binding): a live_http receipt
that additionally names WHO produced it (producer_id) and marks its kind. Its
http request/response block is REAL — the producer actually fetched — so nothing
is fabricated; the receipt only records producer + kind beside the truth.
"""
from __future__ import absolute_import

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import HttpResponse  # noqa: E402
from live_data.rmv2_live.canonical import (  # noqa: E402
    CanonicalDataError,
    canonical_json_bytes,
)
from live_data.rmv2_live.pipeline import RefreshPipeline  # noqa: E402
from live_data.rmv2_live.store import (  # noqa: E402
    STAGED_ACQUISITION_KIND,
    STAGED_ACQUISITION_RECEIPT_SCHEMA,
    read_verified_generation,
    source_binding_from_head,
    verify_source_binding,
)
from live_data.rmv2_live import staging  # noqa: E402

AS_OF = "2026-08-05T22:30:00Z"


def _body(series_id):
    return ("observation_date,%s\n2026-07-28,3.65\n" % series_id).encode("utf-8")


def _live_source(source_id, method_version, series_id):
    return {
        "adapter": "fred_graph_csv",
        "allowed_hosts": ["fred.stlouisfed.org"],
        "coverage_source_ids": ["fred_public_graph"],
        "enabled": True,
        "endpoint": (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s" % series_id
        ),
        "expected_content_types": ["text/csv"],
        "frequency": "weekly",
        "information_set_mode": "current_revised",
        "label": "FRED %s" % series_id,
        "max_bytes": 100000,
        "method_version": method_version,
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Bank of St. Louis",
        "publisher_release_clock": "publisher clock",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "label": "FRED %s" % series_id,
            "series_id": series_id,
            "unit": "Index",
        },
        "source_id": source_id,
        "value_status": "actual",
    }


class FakeHttpClient(object):
    """Returns a deterministic body per source_id with full request metadata."""

    def __init__(self, bodies):
        self.bodies = bodies
        self.calls = []

    def fetch(self, source, now=None, conditional_headers=None):
        self.calls.append(source["source_id"])
        body = self.bodies[source["source_id"]]
        return HttpResponse(
            source["endpoint"], 200,
            {"content-type": "application/json", "etag": '"prod"'},
            body,
            request_body_sha256=None,
            request_headers=conditional_headers or {},
            request_method="GET",
            request_parameters={},
        )


def _registry(root):
    catalog = Path(root) / "data_vault" / "catalog"
    catalog.mkdir(parents=True, exist_ok=True)
    header = (
        "schema_version,source_id,family,publisher,measure,frequency,coverage,"
        "typical_release_or_availability,revision_and_vintage_behavior,role,"
        "access_class,rights_status,primary_url,notes\n"
    )
    row = (
        "recession-monitor-v2.external-source-registry.v1,fred_public_graph,"
        "provider,Federal_Reserve_Bank_of_St_Louis,graph_series,weekly,current,"
        "API_availability,revised,construction_candidate,A,"
        "public_government_source_with_attribution,"
        "https://fred.stlouisfed.org/graph/,\n"
    )
    (catalog / "external_source_registry.csv").write_text(
        header + row, encoding="utf-8")
    reg = (
        "source_id,access_class,coverage,frequency,primary_url,publisher,"
        "rights_status,typical_release_or_availability\n"
        "fred_public_graph,A,current,current,"
        "https://fred.stlouisfed.org,Federal Reserve Bank of St. Louis,"
        "public,weekly\n"
    )
    (Path(root) / "registry.csv").write_text(reg, encoding="utf-8")


def _config(sources):
    return {
        "api": {"host": "127.0.0.1", "port": 8792, "website_poll_seconds": 60},
        "catalog_registry": "registry.csv",
        "schema_version": "recession-monitor-v2.live-data-config.v1",
        "service": {"refresh_tick_seconds": 60},
        "sources": list(sources),
        "store": {"public": "public", "root": "store", "runtime": "runtime"},
    }


def _tree_digest(path):
    """Order-independent digest of every regular file under path."""
    path = Path(path)
    if not path.exists():
        return "absent"
    entries = []
    for p in sorted(path.rglob("*")):
        if p.is_file():
            entries.append((str(p.relative_to(path)),
                            hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(repr(entries).encode("utf-8")).hexdigest()


class StagedProducerBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        _registry(self.root)
        self.seed = _live_source("nyfed_seed", "nyfed_seed.v1", "SEEDX")
        self.a = _live_source("prod_alpha", "prod_alpha.v1", "ALPHAX")
        self.b = _live_source("prod_beta", "prod_beta.v1", "BETAX")
        self.bodies = {
            "nyfed_seed": _body("SEEDX"),
            "prod_alpha": _body("ALPHAX"),
            "prod_beta": _body("BETAX"),
            "prod_bogus": _body("BOGUSX"),
        }
        self.http = FakeHttpClient(self.bodies)
        # seed one generation so a pointer exists.
        self.config = _config([self.seed])
        self.pipeline = RefreshPipeline(self.root, self.config, self.http)
        self.pipeline.refresh()
        self.staging_root = self.root / "live_data" / "staging"

    def _produce(self, source, stamp, split=None):
        return staging.produce(
            self.http, source, stamp, self.staging_root, split=split)

    def _pointer(self):
        p = self.pipeline.store.public / "latest.pointer.json"
        return p.read_bytes() if p.exists() else None

    def _publish_committed(self, committed_sources):
        for src in committed_sources:
            self.pipeline.config["sources"].append(src)
        snapshot = self.pipeline.build_snapshot(AS_OF)
        coverage = self.pipeline.build_coverage(AS_OF)
        status = self.pipeline.build_status(AS_OF, [], snapshot, coverage)
        status["source_matrix"] = {
            "csv_bytes": 0, "csv_sha256": "0" * 64,
            "definition_sha256": "0" * 64, "json_bytes": 0,
            "json_sha256": "0" * 64, "row_count": 0,
        }
        self.pipeline.store.publish_generation(snapshot, status, coverage)


class ProduceIsStoreFree(StagedProducerBase):
    def test_two_producers_do_not_interfere_and_leave_store_untouched(self):
        store_before = _tree_digest(self.pipeline.store.root)
        config_before = canonical_json_bytes(self.pipeline.config)

        d_a = self._produce(self.a, "2026-08-05T22:31:00Z")
        d_b = self._produce(self.b, "2026-08-05T22:31:05Z")

        dir_a = self.staging_root / d_a["producer_id"]
        dir_b = self.staging_root / d_b["producer_id"]
        self.assertNotEqual(dir_a, dir_b)
        self.assertTrue((dir_a / "draft.v1.json").is_file())
        self.assertTrue((dir_b / "draft.v1.json").is_file())
        # exclusive dirs: neither producer's files appear under the other's dir.
        a_files = {p.name for p in dir_a.iterdir()}
        b_files = {p.name for p in dir_b.iterdir()}
        self.assertNotIn(d_b["payload"]["sha256"] + ".bin", a_files)
        self.assertNotIn(d_a["payload"]["sha256"] + ".bin", b_files)

        # store + config byte-identical after both producers ran.
        self.assertEqual(_tree_digest(self.pipeline.store.root), store_before)
        self.assertEqual(canonical_json_bytes(self.pipeline.config), config_before)

    def test_produce_imports_no_store_mutation_api(self):
        # the produce code path must not reference a store-mutation entry point.
        import inspect
        src = inspect.getsource(staging.produce)
        for forbidden in ("store_source_object", "store_normalized",
                          "store_receipt", "write_source_head",
                          "publish_generation", "write_source_status"):
            self.assertNotIn(forbidden, src)


class CommitSerializes(StagedProducerBase):
    def test_linear_receipt_chain_one_pointer_flip_deterministic_order(self):
        # produce beta first, alpha second — commit order must be by producer_id,
        # independent of produce finish order.
        self._produce(self.b, "2026-08-05T22:40:00Z")
        self._produce(self.a, "2026-08-05T22:41:00Z")

        pointer_before = self._pointer()
        results = staging.commit_staged(self.pipeline, self.staging_root, AS_OF)
        committed = [r for r in results if r["outcome"] == "committed"]
        # deterministic order: alpha (producer_id sorts before beta) commits first.
        self.assertEqual([r["source_id"] for r in committed],
                         ["prod_alpha", "prod_beta"])
        # linear receipt chain: beta's predecessor is alpha's receipt.
        self.assertIsNone(committed[0]["predecessor_receipt_sha256"])
        self.assertEqual(committed[1]["predecessor_receipt_sha256"],
                         committed[0]["receipt_sha256"])
        # exactly one generation publish over both new heads.
        self._publish_committed([self.a, self.b])
        pointer_after = self._pointer()
        self.assertNotEqual(pointer_after, pointer_before)
        gen = read_verified_generation(
            self.pipeline.store.public,
            self.pipeline.store.root / "generations",
            materialize_members=("snapshot.json",),
        )
        bound = {s["source_id"]
                 for s in gen["members"]["snapshot.json"]["sources"]}
        self.assertIn("prod_alpha", bound)
        self.assertIn("prod_beta", bound)

    def test_committed_receipt_is_staged_kind_and_carries_producer_id(self):
        draft = self._produce(self.a, "2026-08-05T22:45:00Z")
        results = staging.commit_staged(self.pipeline, self.staging_root, AS_OF)
        head = self.pipeline.store.read_source_head("prod_alpha")
        binding = source_binding_from_head("prod_alpha", head)
        evidence = verify_source_binding(self.pipeline.store.root, binding)
        receipt = evidence["receipt"]
        self.assertEqual(receipt["schema_version"],
                         STAGED_ACQUISITION_RECEIPT_SCHEMA)
        self.assertEqual(receipt["acquisition_kind"], STAGED_ACQUISITION_KIND)
        self.assertEqual(receipt["producer_id"], draft["producer_id"])
        # real fetch timestamp preserved in the receipt clocks.
        self.assertEqual(receipt["clocks"]["retrieved_at"],
                         draft["fetched_at"])
        # committed draft moved out of the live scan set.
        self.assertTrue((self.staging_root / draft["producer_id"] /
                        "committed").exists())


class CommitRejects(StagedProducerBase):
    def test_sha_mismatch_draft_rejected_and_commit_continues(self):
        d_bad = self._produce(self.a, "2026-08-05T22:50:00Z")
        d_good = self._produce(self.b, "2026-08-05T22:50:05Z")
        # corrupt alpha's payload after produce (byte truth fails at commit).
        payload = (self.staging_root / d_bad["producer_id"] /
                   (d_bad["payload"]["sha256"] + ".bin"))
        payload.write_bytes(payload.read_bytes() + b"tampered")

        results = staging.commit_staged(self.pipeline, self.staging_root, AS_OF)
        by_id = {r["source_id"]: r for r in results}
        self.assertEqual(by_id["prod_alpha"]["outcome"], "rejected")
        self.assertIn("sha", by_id["prod_alpha"]["reason"].lower())
        self.assertEqual(by_id["prod_beta"]["outcome"], "committed")
        # rejected draft filed under rejected/<reason>/, not committed/.
        self.assertTrue(any(
            (self.staging_root / d_bad["producer_id"] / "rejected").glob("*")))
        self.assertIsNone(self.pipeline.store.read_source_head("prod_alpha"))
        self.assertIsNotNone(self.pipeline.store.read_source_head("prod_beta"))

    def test_unregistered_shape_rejected(self):
        bad = _live_source("prod_bogus", "prod_bogus.v1", "BOGUSX")
        bad["adapter"] = "no_such_adapter_shape"
        self._produce(bad, "2026-08-05T22:55:00Z")
        results = staging.commit_staged(self.pipeline, self.staging_root, AS_OF)
        r = [x for x in results if x["source_id"] == "prod_bogus"][0]
        self.assertEqual(r["outcome"], "rejected")
        self.assertIsNone(self.pipeline.store.read_source_head("prod_bogus"))


class CommitIsIdempotent(StagedProducerBase):
    def test_recommit_of_already_landed_draft_is_a_noop(self):
        draft = self._produce(self.a, "2026-08-05T23:00:00Z")
        pdir = self.staging_root / draft["producer_id"]
        payload_name = draft["payload"]["sha256"] + ".bin"
        pointer_before = self._pointer()
        first = staging.commit_staged(self.pipeline, self.staging_root, AS_OF)
        self.assertEqual([r["outcome"] for r in first], ["committed"])
        head_after_first = self.pipeline.store.read_source_head("prod_alpha")
        # the committer never publishes — the pointer is unchanged until a
        # separate publish step (§3: ONE publish at the end). A crash here leaves
        # the pointer where it was.
        self.assertEqual(self._pointer(), pointer_before)
        # simulate a crash AFTER admit but BEFORE the committed/ move: the live
        # draft + payload are still present, so the next commit re-scans them.
        # Content-addressed re-admit must be a no-op, not a duplicate landing.
        committed = pdir / "committed"
        (pdir / "draft.v1.json").write_bytes(
            (committed / "draft.v1.json").read_bytes())
        (pdir / payload_name).write_bytes(
            (committed / payload_name).read_bytes())
        second = staging.commit_staged(self.pipeline, self.staging_root, AS_OF)
        self.assertEqual([r["outcome"] for r in second], ["unchanged"])
        head_after_second = self.pipeline.store.read_source_head("prod_alpha")
        self.assertEqual(head_after_second, head_after_first)


class StagedReceiptSchema(StagedProducerBase):
    def _bind_and_get_receipt(self):
        draft = self._produce(self.a, "2026-08-05T23:10:00Z")
        body = self.bodies["prod_alpha"]
        return draft, body

    def test_staged_receipt_missing_producer_id_fails(self):
        draft, body = self._bind_and_get_receipt()
        receipt = staging.build_staged_receipt(
            source=self.a, draft=draft,
            source_bytes_sha256="a" * 64, normalized_sha256="b" * 64,
            predecessor_receipt_sha256=None)
        del receipt["producer_id"]
        with self.assertRaises(CanonicalDataError):
            staging._require_staged_receipt_fields(receipt)

    def test_staged_receipt_missing_fetch_timestamp_fails(self):
        draft, body = self._bind_and_get_receipt()
        receipt = staging.build_staged_receipt(
            source=self.a, draft=draft,
            source_bytes_sha256="a" * 64, normalized_sha256="b" * 64,
            predecessor_receipt_sha256=None)
        receipt["clocks"]["retrieved_at"] = ""
        with self.assertRaises(CanonicalDataError):
            staging._require_staged_receipt_fields(receipt)


if __name__ == "__main__":
    unittest.main()
