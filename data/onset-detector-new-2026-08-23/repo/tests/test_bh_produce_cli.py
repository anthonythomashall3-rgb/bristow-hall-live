"""B-PROD-1 CLI round-trip — bh produce (store-free) then bh commit-staged
(admit + publish ONE generation) on a real on-disk repo layout, with a fake http
client for determinism. Proves the producer/committer split end-to-end through
the same publish composition pipeline.refresh() uses.
"""
from __future__ import absolute_import

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import HttpResponse  # noqa: E402
from live_data.rmv2_live.pipeline import RefreshPipeline  # noqa: E402
from live_data.rmv2_live.store import read_verified_generation  # noqa: E402

from bh import produce  # noqa: E402


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
    def __init__(self, bodies):
        self.bodies = bodies

    def fetch(self, source, now=None, conditional_headers=None):
        return HttpResponse(
            source["endpoint"], 200,
            {"content-type": "text/csv", "etag": '"prod"'},
            self.bodies[source["source_id"]],
            request_body_sha256=None,
            request_headers=conditional_headers or {},
            request_method="GET",
            request_parameters={})


def _config(sources):
    return {
        "api": {"host": "127.0.0.1", "port": 8792, "website_poll_seconds": 60},
        "catalog_registry": "registry.csv",
        "schema_version": "recession-monitor-v2.live-data-config.v1",
        "service": {"refresh_tick_seconds": 60},
        "sources": list(sources),
        "store": {"public": "public", "root": "store", "runtime": "runtime"},
    }


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
    (Path(root) / "registry.csv").write_text(
        "source_id,access_class,coverage,frequency,primary_url,publisher,"
        "rights_status,typical_release_or_availability\n"
        "fred_public_graph,A,current,current,https://fred.stlouisfed.org,"
        "Federal Reserve Bank of St. Louis,public,weekly\n", encoding="utf-8")


class BhProduceCliRoundTrip(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        _registry(self.root)
        cfgdir = self.root / "live_data" / "config"
        cfgdir.mkdir(parents=True)
        self.seed = _live_source("seed_src", "seed_src.v1", "SEEDX")
        self.alpha = _live_source("alpha_src", "alpha_src.v1", "ALPHAX")
        (cfgdir / "sources.v1.json").write_text(
            json.dumps(_config([self.seed])), encoding="utf-8")
        self.http = FakeHttpClient({
            "seed_src": _body("SEEDX"),
            "alpha_src": _body("ALPHAX"),
        })
        # seed one generation so a pointer exists.
        RefreshPipeline(self.root, _config([self.seed]), self.http).refresh()

    def test_produce_is_store_free_then_commit_publishes(self):
        store = self.root / "store"
        # produce alpha into staging — store pointer must not move.
        pointer_before = (
            self.root / "public" / "latest.pointer.json").read_bytes()
        drafts = produce.run_produce(
            self.root, "alpha_src", http_client=self.http,
            now="2026-08-05T23:20:00Z", source_specs=[self.alpha])
        self.assertEqual(len(drafts), 1)
        self.assertEqual(
            (self.root / "public" / "latest.pointer.json").read_bytes(),
            pointer_before)
        self.assertFalse((store / "receipts" / "alpha_src").exists())

        # commit-staged admits alpha and publishes ONE new generation.
        outcome = produce.run_commit(
            self.root, http_client=self.http, now="2026-08-05T23:21:00Z")
        self.assertEqual(
            [r["outcome"] for r in outcome["results"]], ["committed"])
        self.assertIsNotNone(outcome["pointer"])
        self.assertNotEqual(
            (self.root / "public" / "latest.pointer.json").read_bytes(),
            pointer_before)

        # the published generation re-authenticates alpha's staged binding.
        gen = read_verified_generation(
            self.root / "public",
            store / "generations",
            materialize_members=("snapshot.json",))
        bound = {s["source_id"]
                 for s in gen["members"]["snapshot.json"]["sources"]}
        self.assertIn("alpha_src", bound)
        self.assertIn("seed_src", bound)
        # alpha is now in the on-disk config (committer is the one config writer).
        cfg = json.loads(
            (self.root / "live_data" / "config" / "sources.v1.json").read_text())
        self.assertIn("alpha_src",
                      {s["source_id"] for s in cfg["sources"]})


if __name__ == "__main__":
    unittest.main()
