"""B1.3 incremental snapshot projection — byte-identity contract.

The per-source projection cache must make `build_snapshot` incremental WITHOUT
changing a single output byte: for any store state, the cached build must be
byte-identical to the full (uncached) rebuild, including after a source's
evidence changes (cache invalidation) and after warm reuse.
"""
from __future__ import absolute_import

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import HttpResponse
from live_data.rmv2_live.canonical import canonical_json_bytes
from live_data.rmv2_live.pipeline import RefreshPipeline


T1 = "2026-07-29T12:00:00Z"
T2 = "2026-07-29T12:06:00Z"
T3 = "2026-07-29T12:12:00Z"


def _source(source_id, endpoint):
    return {
        "adapter": "raw_capture",
        "allowed_hosts": ["publisher.example"],
        "coverage_source_ids": ["synthetic_publisher"],
        "enabled": True,
        "endpoint": endpoint,
        "expected_content_types": ["application/octet-stream"],
        "frequency": "daily",
        "information_set_mode": "current_revised",
        "label": "Synthetic publisher payload",
        "max_bytes": 100000,
        "method_version": "synthetic-v1",
        "poll_seconds": 300,
        "publisher": "Synthetic publisher",
        "publisher_release_clock": "publisher clock",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {},
        "source_id": source_id,
        "value_status": "actual",
    }


def _config():
    return {
        "api": {"host": "127.0.0.1", "port": 8792, "website_poll_seconds": 60},
        "catalog_registry": "registry.csv",
        "schema_version": "recession-monitor-v2.live-data-config.v1",
        "service": {"refresh_tick_seconds": 60},
        "sources": [
            _source("synthetic_live_a", "https://publisher.example/a.bin"),
            _source("synthetic_live_b", "https://publisher.example/b.bin"),
        ],
        "store": {"public": "public", "root": "store", "runtime": "runtime"},
    }


def _write_registry(root):
    (Path(root) / "registry.csv").write_text(
        "source_id,access_class,coverage,frequency,primary_url,publisher,"
        "rights_status,typical_release_or_availability\n"
        "synthetic_publisher,A,current,daily,"
        "https://publisher.example,Synthetic publisher,public,daily\n",
        encoding="utf-8",
    )


def _response(url, body, etag):
    return HttpResponse(
        url, 200,
        {"etag": etag, "last-modified": "Wed, 29 Jul 2026 12:00:00 GMT",
         "content-type": "application/octet-stream"},
        body,
    )


class ScriptedHttpClient(object):
    def __init__(self, by_source):
        self.by_source = dict(by_source)

    def fetch(self, source, now=None, conditional_headers=None):
        result = self.by_source[source["source_id"]]
        result.request_headers = dict(conditional_headers or {})
        return result


class IncrementalSnapshotByteIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        _write_registry(self.root)
        self.config = _config()

    def tearDown(self):
        self.temp.cleanup()

    def _pipeline(self, client, ts):
        return RefreshPipeline(self.root, self.config, client, clock=lambda: ts)

    def _sha(self, snapshot):
        return snapshot["generation_content_sha256"]

    def test_incremental_snapshot_is_byte_identical_to_full_rebuild(self):
        client = ScriptedHttpClient({
            "synthetic_live_a": _response(
                "https://publisher.example/a.bin", b"payload-A-v1", '"a1"'),
            "synthetic_live_b": _response(
                "https://publisher.example/b.bin", b"payload-B-v1", '"b1"'),
        })
        self._pipeline(client, T1).refresh()

        pipe = self._pipeline(client, T2)
        full = pipe.build_snapshot(T2, use_projection_cache=False)
        cold = pipe.build_snapshot(T2, use_projection_cache=True)   # computes+caches
        warm = pipe.build_snapshot(T2, use_projection_cache=True)   # reuses cache

        self.assertEqual(canonical_json_bytes(full), canonical_json_bytes(cold))
        self.assertEqual(canonical_json_bytes(full), canonical_json_bytes(warm))
        self.assertEqual(self._sha(full), self._sha(cold))
        self.assertEqual(self._sha(full), self._sha(warm))

    def test_changed_source_invalidates_only_its_projection(self):
        client = ScriptedHttpClient({
            "synthetic_live_a": _response(
                "https://publisher.example/a.bin", b"payload-A-v1", '"a1"'),
            "synthetic_live_b": _response(
                "https://publisher.example/b.bin", b"payload-B-v1", '"b1"'),
        })
        self._pipeline(client, T1).refresh()
        # warm the projection cache for both sources
        self._pipeline(client, T2).build_snapshot(T2, use_projection_cache=True)

        # source B changes; A untouched
        changed = ScriptedHttpClient({
            "synthetic_live_b": _response(
                "https://publisher.example/b.bin", b"payload-B-v2", '"b2"'),
        })
        self._pipeline(changed, T3).refresh(source_ids=["synthetic_live_b"])

        pipe = self._pipeline(changed, T3)
        inc = pipe.build_snapshot(T3, use_projection_cache=True)
        full = pipe.build_snapshot(T3, use_projection_cache=False)
        self.assertEqual(canonical_json_bytes(inc), canonical_json_bytes(full))
        self.assertEqual(self._sha(inc), self._sha(full))


if __name__ == "__main__":
    unittest.main()
