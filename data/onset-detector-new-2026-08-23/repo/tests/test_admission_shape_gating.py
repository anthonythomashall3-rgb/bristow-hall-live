"""B-FAST-1 §3 — shape-gated admission ceiling.

The runbook (§6.1/§6.2) caps *new parser shapes* at 5 per cycle while allowing
*unlimited instances of a proven shape*. The prior code conflated the two:
``batch = pending[:max_batch]`` capped total sources at 5 regardless of shape.

A *shape* is the deterministic triple ``(adapter_id, parser_version,
response_schema_sha256)``. A shape is PROVEN iff the content-addressed store
already holds a green acquisition receipt for a currently-configured source
with that exact shape (byte-derived, no judgement). An unmeasurable shape
(missing adapter) is NEVER proven.

These tests drive the same hermetic fake-ops harness as
``test_rmv2_admission_runner`` and seed a tmp store, so they never touch
launchd, the network, or the real store. They MUST fail against the old
total-cap-of-5 (proven batches would be truncated to 5).
"""

from __future__ import absolute_import

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_data.rmv2_live.canonical import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
)
from live_data.rmv2_admission import runner  # noqa: E402
from test_rmv2_admission_runner import FakeOps, make_draft  # noqa: E402

_MISSING = object()


def build_queue(root, specs, max_batch=5):
    """specs: list of (source_id, adapter). adapter=_MISSING drops the field."""
    root = Path(root)
    for sub in (
        "live_data/config",
        "live_data/feed_factory/drafts",
        "live_data/runtime",
        "live_data/public",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    entries = []
    for source_id, adapter in specs:
        draft = make_draft(source_id)
        if adapter is _MISSING:
            del draft["source"]["adapter"]
        else:
            draft["source"]["adapter"] = adapter
        draft_rel = "live_data/feed_factory/drafts/%s.v1.json" % source_id
        draft_bytes = canonical_json_bytes(draft)
        (root / draft_rel).write_bytes(draft_bytes)
        entries.append({
            "draft_path": draft_rel,
            "reviewed": True,
            "sha256": sha256_bytes(draft_bytes),
            "source_id": source_id,
        })
    queue = {
        "drafts": entries,
        "policy": {
            "allow_store_mutation": True,
            "max_batch": max_batch,
            "no_ai": True,
            "scientific_binding": False,
        },
        "queue_id": "rmv2-admission-test.v1",
        "schema_version": runner.QUEUE_SCHEMA,
    }
    queue_path = root / "live_data" / "config" / "admission_queue.v1.json"
    queue_path.write_bytes(canonical_json_bytes(queue))
    return queue_path


def source_map_for(queue_path):
    import json
    queue = json.loads(Path(queue_path).read_text())
    return {e["draft_path"]: e["source_id"] for e in queue["drafts"]}


def seed_proven_adapter(root, adapter):
    """Write a config source + one green store receipt for ``adapter`` so its
    shape ``(adapter, None, None)`` is proven."""
    root = Path(root)
    source_id = "seed_%s" % (adapter if adapter is not None else "none")
    config = {
        "schema_version": "recession-monitor-v2.sources.v1",
        "sources": [{
            "source_id": source_id,
            "adapter": adapter,
            "method_version": "%s.seed.v1" % source_id,
        }],
    }
    config_dir = root / "live_data" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "sources.v1.json").write_bytes(
        canonical_json_bytes(config)
    )
    receipt_dir = root / "live_data" / "store" / "receipts" / source_id
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / "r.json").write_bytes(canonical_json_bytes({
        "outcome": "retrieved_and_validated",
        "source_id": source_id,
    }))


class AdmissionShapeGatingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, queue_path, baseline_head_count=0):
        ops = FakeOps(
            source_map_for(queue_path),
            baseline_head_count=baseline_head_count,
        )
        return runner.run_cycle(self.root, queue_path, ops=ops, process_id=7)

    def test_proven_shape_admits_unlimited(self):
        seed_proven_adapter(self.root, "fred_json_api")
        specs = [("prov_%02d_current" % i, "fred_json_api") for i in range(50)]
        qp = build_queue(self.root, specs, max_batch=5)
        record = self._run(qp)
        self.assertEqual(len(record["batch_source_ids"]), 50)
        self.assertEqual(record["terminal_state"], runner.STATE_ALL_ADMITTED)

    def test_new_shapes_capped_at_five(self):
        specs = [("new_%02d_current" % i, "adapter_%d" % i) for i in range(8)]
        qp = build_queue(self.root, specs, max_batch=5)
        record = self._run(qp)
        self.assertEqual(len(record["batch_source_ids"]), 5)
        self.assertEqual(
            record["terminal_state"], runner.STATE_BATCH_GREEN_MORE_PENDING
        )

    def test_mixed_proven_plus_new(self):
        seed_proven_adapter(self.root, "fred_json_api")
        specs = [("prov_%02d_current" % i, "fred_json_api") for i in range(50)]
        specs += [("new_%02d_current" % i, "adapter_%d" % i) for i in range(8)]
        qp = build_queue(self.root, specs, max_batch=5)
        record = self._run(qp)
        # all 50 proven + at most 5 new = 55; 3 new left pending.
        self.assertEqual(len(record["batch_source_ids"]), 55)
        self.assertEqual(
            record["terminal_state"], runner.STATE_BATCH_GREEN_MORE_PENDING
        )

    def test_unmeasurable_shape_is_never_proven(self):
        # Even with a config source that has adapter=None and a green receipt,
        # a missing-adapter draft must count as NEW and stay under the cap.
        seed_proven_adapter(self.root, None)
        specs = [("blank_%02d_current" % i, _MISSING) for i in range(8)]
        qp = build_queue(self.root, specs, max_batch=5)
        record = self._run(qp)
        self.assertEqual(len(record["batch_source_ids"]), 5)
        self.assertEqual(
            record["terminal_state"], runner.STATE_BATCH_GREEN_MORE_PENDING
        )
        self.assertFalse(
            runner.is_proven_shape(self.root, (None, None, None))
        )


if __name__ == "__main__":
    unittest.main()
