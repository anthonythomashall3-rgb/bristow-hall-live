"""F1 binding-attestation — O(changed) hot paths, byte-identical to the closure.

The publish, generation-read, and inventory hot paths must authenticate a
generation WITHOUT re-reading the (multi-GB, weekly-vintage) normalized blobs of
unchanged sources.  The content-addressed attestation must be byte-for-byte
equivalent to the full ``verify_source_binding`` closure, must fall back to the
full closure on a cache miss (and fail closed on missing evidence), and must
leave the ``verify`` oracle (``attest_bindings=False``) doing the full read.
"""
from __future__ import absolute_import

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import store as store_module
from live_data.rmv2_live.adapters import HttpResponse
from live_data.rmv2_live.pipeline import RefreshPipeline
from live_data.rmv2_live.store import (
    CanonicalDataError,
    read_verified_generation,
    verify_source_binding,
)


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
        "api": {"host": "127.0.0.1", "port": 8793, "website_poll_seconds": 60},
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


class _NormalizedReadCounter(object):
    """Instrument safe_regular_file to count reads that touch normalized blobs."""

    def __init__(self):
        self._orig = store_module.safe_regular_file
        self.normalized_bytes = 0
        self.normalized_paths = []

    def __enter__(self):
        orig = self._orig

        def patched(path, root):
            data = orig(path, root)
            posix = Path(path).as_posix()
            if "/normalized/sha256/" in posix:
                self.normalized_bytes += len(data)
                self.normalized_paths.append(posix)
            return data

        store_module.safe_regular_file = patched
        return self

    def __exit__(self, *exc):
        store_module.safe_regular_file = self._orig
        return False


class BindingAttestationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        _write_registry(self.root)
        self.config = _config()
        self.client = ScriptedHttpClient({
            "synthetic_live_a": _response(
                "https://publisher.example/a.bin", b"payload-A-v1", '"a1"'),
            "synthetic_live_b": _response(
                "https://publisher.example/b.bin", b"payload-B-v1", '"b1"'),
        })

    def tearDown(self):
        self.temp.cleanup()

    def _pipeline(self, client, ts):
        return RefreshPipeline(self.root, self.config, client, clock=lambda: ts)

    def _bindings(self):
        pipe = self._pipeline(self.client, T2)
        return pipe.build_snapshot(T2, use_projection_cache=True)["sources"]

    def test_attestation_facts_match_full_closure(self):
        self._pipeline(self.client, T1).refresh()
        store = self._pipeline(self.client, T2).store
        for binding in self._bindings():
            evidence = verify_source_binding(store.root, binding)
            attestation = store.attest_source_binding(binding)
            self.assertEqual(
                attestation["source_id"], binding["source_id"])
            self.assertEqual(
                attestation["parser_id"],
                evidence["normalized"].get("parser_id"))
            self.assertEqual(
                attestation["etag"],
                evidence["receipt"]["response"].get("etag"))
            self.assertEqual(
                attestation["last_modified"],
                evidence["receipt"]["response"].get("last_modified"))
            self.assertEqual(
                attestation["record_count"], binding["record_count"])
            self.assertEqual(
                attestation["latest_observation_period"],
                binding["latest_observation_period"])

    def test_warm_attested_read_touches_no_normalized_blob(self):
        self._pipeline(self.client, T1).refresh()
        store = self._pipeline(self.client, T2).store
        # Warm the attestation cache (one full closure per source).
        for binding in self._bindings():
            store.attest_source_binding(binding)
        with _NormalizedReadCounter() as counter:
            generation = read_verified_generation(
                store.public,
                store.root / "generations",
                attest_bindings=True,
            )
        self.assertEqual(counter.normalized_bytes, 0, counter.normalized_paths)
        self.assertEqual(counter.normalized_paths, [])
        self.assertTrue(generation["source_bindings"])

    def test_verify_oracle_still_reads_all_normalized_blobs(self):
        self._pipeline(self.client, T1).refresh()
        store = self._pipeline(self.client, T2).store
        for binding in self._bindings():
            store.attest_source_binding(binding)
        with _NormalizedReadCounter() as counter:
            read_verified_generation(
                store.public,
                store.root / "generations",
                attest_bindings=False,
            )
        # The oracle path re-reads every source's normalized blob.
        self.assertGreater(counter.normalized_bytes, 0)
        self.assertEqual(len(counter.normalized_paths), 2)

    def test_attested_generation_is_identical_to_oracle(self):
        self._pipeline(self.client, T1).refresh()
        store = self._pipeline(self.client, T2).store
        full = read_verified_generation(
            store.public, store.root / "generations", attest_bindings=False)
        attested = read_verified_generation(
            store.public, store.root / "generations", attest_bindings=True)
        self.assertEqual(full["manifest"], attested["manifest"])
        self.assertEqual(full["members"], attested["members"])
        self.assertEqual(full["source_bindings"], attested["source_bindings"])
        self.assertEqual(full["pointer"], attested["pointer"])

    def test_changed_source_only_reads_its_own_blob(self):
        self._pipeline(self.client, T1).refresh()
        store = self._pipeline(self.client, T2).store
        bindings = self._bindings()
        for binding in bindings:
            store.attest_source_binding(binding)
        digest_a = next(
            b["normalized_sha256"] for b in bindings
            if b["source_id"] == "synthetic_live_a")
        # Source B changes -> new normalized digest -> attestation miss for B
        # only. The whole republish (build_snapshot + publish_generation +
        # readback) must never re-read source A's unchanged normalized blob.
        changed = ScriptedHttpClient({
            "synthetic_live_b": _response(
                "https://publisher.example/b.bin", b"payload-B-v2", '"b2"'),
        })
        with _NormalizedReadCounter() as counter:
            self._pipeline(changed, T3).refresh(source_ids=["synthetic_live_b"])
        read_digests = {p.rsplit("/", 1)[-1] for p in counter.normalized_paths}
        self.assertNotIn(digest_a + ".json", read_digests)
        self.assertTrue(counter.normalized_paths)  # B was (re)read at least once

    def test_missing_evidence_fails_closed(self):
        self._pipeline(self.client, T1).refresh()
        store = self._pipeline(self.client, T2).store
        binding = self._bindings()[0]
        store.attest_source_binding(binding)  # warm
        # Delete the immutable normalized blob; the attested guard must fail.
        digest = binding["normalized_sha256"]
        blob = (store.root / "normalized" / "sha256" / digest[:2] /
                (digest + ".json"))
        blob.chmod(0o644)
        blob.unlink()
        with self.assertRaises(CanonicalDataError):
            store.attest_source_binding(binding)


if __name__ == "__main__":
    unittest.main()
