from __future__ import absolute_import

import copy
import http.client
import inspect
import os
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import cli
from live_data.rmv2_live.adapters import SourceUnavailable, parse_bls_json
from live_data.rmv2_live.canonical import (
    CanonicalDataError,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    strict_json_loads,
)
from live_data.rmv2_live.config import load_config, load_env_file
from live_data.rmv2_live.matrix import source_matrix_definition_sha256
from live_data.rmv2_live.server import create_server
from live_data.rmv2_live import store as store_module
from live_data.rmv2_live.store import (
    LiveStore,
    read_verified_generation,
    safe_regular_file,
    safe_regular_file_identity,
)


FIXED_TIME_1 = "2026-07-29T12:00:00Z"
FIXED_TIME_2 = "2026-07-29T12:06:00Z"

GENERATION_MEMBER_NAMES = frozenset((
    "coverage.json",
    "snapshot.json",
    "status.json",
))


def source_config(source_id="bls_test"):
    return {
        "adapter": "bls_json",
        "allowed_hosts": ["api.bls.gov"],
        "coverage_source_ids": ["bls_ces"],
        "enabled": True,
        "endpoint": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        "expected_content_types": ["application/json"],
        "frequency": "monthly",
        "information_set_mode": "current_revised",
        "label": "Synthetic BLS source",
        "max_bytes": 100000,
        "method_version": "test-v1",
        "poll_seconds": 300,
        "publisher": "U.S. Bureau of Labor Statistics",
        "publisher_release_clock": "publisher clock",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "items": [{
                "label": "Payrolls",
                "series_id": "CESX",
                "unit": "thousands",
            }],
        },
        "source_id": source_id,
        "value_status": "actual",
    }


def config_value(sources=None):
    return {
        "api": {
            "host": "127.0.0.1",
            "port": 8792,
            "website_poll_seconds": 60,
        },
        "catalog_registry": "registry.csv",
        "schema_version": "recession-monitor-v2.live-data-config.v1",
        "service": {"refresh_tick_seconds": 60},
        "sources": list(sources if sources is not None else [source_config()]),
        "store": {
            "public": "public",
            "root": "store",
            "runtime": "runtime",
        },
    }


def write_registry(root):
    (Path(root) / "registry.csv").write_text(
        "source_id,access_class,coverage,frequency,primary_url,publisher,"
        "rights_status,typical_release_or_availability\n"
        "bls_ces,A,current,monthly,https://api.bls.gov,BLS,public,monthly\n",
        encoding="utf-8",
    )


def write_config(root, config=None):
    root = Path(root)
    write_registry(root)
    path = root / "sources.v1.json"
    path.write_bytes(canonical_json_bytes(config or config_value()))
    return path


def snapshot_value(marker, generated_at=FIXED_TIME_1):
    return {
        "generated_at": generated_at,
        "schema_version": "recession-monitor-v2.live-snapshot.v1",
        "series": {
            "synthetic.series": {
                "latest": {"value": marker},
                "observations": [{"value": marker}],
                "series_id": "synthetic.series",
                "source_id": "synthetic",
                "unit": "index",
            },
        },
        "sources": [],
    }


def install_source_evidence(
    store,
    source_id="bls_test",
    generated_at=FIXED_TIME_1,
    value="1.0",
):
    raw = ("publisher-%s-%s" % (source_id, value)).encode("utf-8")
    source_digest, _ = store.store_source_object(raw)
    record = {
        "observation_period": "2026-01",
        "retrieved_at": generated_at,
        "series_id": "%s.SERIES" % source_id,
        "source_bytes_sha256": source_digest,
        "source_id": source_id,
        "unit": "index",
        "validated_at": generated_at,
        "value": value,
    }
    normalized = {
        "parser_id": "rmv2-live/bls_json",
        "records": [record],
        "retrieved_at": generated_at,
        "schema_version": "recession-monitor-v2.normalized-source.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source_id,
    }
    normalized_digest, _ = store.store_normalized(normalized)
    receipt = {
        "clocks": {
            "provider_available_at": generated_at,
            "publisher_released_at": None,
            "retrieved_at": generated_at,
            "validated_at": generated_at,
        },
        "information_set_mode": "current_revised",
        "normalized_sha256": normalized_digest,
        "outcome": "retrieved_and_validated",
        "predecessor_receipt_sha256": None,
        "publisher": "BLS",
        "request": {
            "body_sha256": None,
            "conditional_headers": {},
            "method": "POST",
            "parameters": {},
            "url": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        },
        "response": {
            "content_length": len(raw),
            "content_type": "application/json",
            "etag": None,
            "last_modified": None,
            "status": 200,
        },
        "rights_status": "public",
        "schema_version": "recession-monitor-v2.acquisition-receipt.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source_id,
    }
    receipt_digest, _ = store.store_receipt(source_id, receipt)
    head = {
        "adapter": "bls_json",
        "etag": None,
        "last_modified": None,
        "latest_observation_period": "2026-01",
        "method_version": "test-v1",
        "normalized_sha256": normalized_digest,
        "receipt_sha256": receipt_digest,
        "record_count": 1,
        "retrieved_at": generated_at,
        "schema_version": "recession-monitor-v2.source-head.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source_id,
    }
    store.write_source_head(source_id, head)
    return {
        key: head[key]
        for key in (
            "latest_observation_period",
            "normalized_sha256",
            "receipt_sha256",
            "record_count",
            "retrieved_at",
            "source_bytes_sha256",
            "source_id",
        )
    }


def status_value(marker, generated_at=FIXED_TIME_1):
    return {
        "generated_at": generated_at,
        "marker": marker,
        "no_ai": True,
        "schema_version": "recession-monitor-v2.live-status.v1",
        "service_state": "ready",
    }


def coverage_value(marker, generated_at=FIXED_TIME_1):
    return {
        "generated_at": generated_at,
        "marker": marker,
        "rows": [],
        "schema_version": "recession-monitor-v2.source-coverage.v1",
    }


def bls_row(latest="true", footnotes=None, value="159000"):
    return {
        "footnotes": list(footnotes or []),
        "latest": latest,
        "period": "M06",
        "value": value,
        "year": "2026",
    }


def bls_payload(series_rows):
    return canonical_json_bytes({
        "Results": {"series": series_rows},
        "status": "REQUEST_SUCCEEDED",
    })


class ImmutableGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_registry(self.root)
        self.store = LiveStore(self.root, config_value())
        self.store.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_generation_is_named_by_manifest_and_manifest_commits_all_members(self):
        snapshot = snapshot_value("one")
        status = status_value("one")
        coverage = coverage_value("one")

        pointer = self.store.publish_generation(snapshot, status, coverage)

        self.assertEqual(
            pointer["schema_version"],
            "recession-monitor-v2.live-pointer.v2",
        )
        self.assertEqual(
            pointer["generation_sha256"],
            pointer["manifest_sha256"],
        )
        generation = (
            self.store.root / "generations" / pointer["generation_sha256"]
        )
        self.assertEqual(
            {item.name for item in generation.iterdir()},
            GENERATION_MEMBER_NAMES.union({"manifest.json"}),
        )
        manifest_bytes = (generation / "manifest.json").read_bytes()
        self.assertEqual(sha256_bytes(manifest_bytes), generation.name)
        manifest = strict_json_loads(manifest_bytes)
        self.assertEqual(
            manifest["schema_version"],
            "recession-monitor-v2.live-generation-manifest.v2",
        )
        self.assertEqual(set(manifest["members"]), GENERATION_MEMBER_NAMES)

        for name in sorted(GENERATION_MEMBER_NAMES):
            member_bytes = (generation / name).read_bytes()
            self.assertTrue(
                {"bytes", "sha256"}.issubset(
                    set(manifest["members"][name])
                ),
            )
            self.assertEqual(
                manifest["members"][name]["bytes"],
                len(member_bytes),
            )
            self.assertEqual(
                manifest["members"][name]["sha256"],
                sha256_bytes(member_bytes),
            )
            pointer_hash_field = {
                "coverage.json": "coverage_sha256",
                "snapshot.json": "snapshot_sha256",
                "status.json": "status_sha256",
            }[name]
            self.assertEqual(pointer[pointer_hash_field], sha256_bytes(member_bytes))
            self.assertEqual(
                stat.S_IMODE((generation / name).stat().st_mode),
                0o444,
            )
        self.assertEqual(
            stat.S_IMODE((generation / "manifest.json").stat().st_mode),
            0o444,
        )

    def test_latest_previous_and_lkg_are_generation_pointers_not_mutable_snapshots(self):
        pointer1 = self.store.publish_generation(
            snapshot_value("one"),
            status_value("one"),
            coverage_value("one"),
        )
        self.assertEqual(
            read_json(self.store.public / "latest.pointer.json"),
            pointer1,
        )
        self.assertTrue(
            (self.store.public / "latest.lkg.pointer.json").is_file()
        )
        self.assertEqual(
            read_json(self.store.public / "latest.lkg.pointer.json"),
            pointer1,
        )
        self.assertFalse(
            (self.store.public / "latest.previous.pointer.json").exists()
        )

        pointer2 = self.store.publish_generation(
            snapshot_value("two", FIXED_TIME_2),
            status_value("two", FIXED_TIME_2),
            coverage_value("two", FIXED_TIME_2),
        )
        self.assertEqual(
            read_json(self.store.public / "latest.previous.pointer.json"),
            pointer1,
        )
        self.assertEqual(
            read_json(self.store.public / "latest.pointer.json"),
            pointer2,
        )
        self.assertEqual(
            read_json(self.store.public / "latest.lkg.pointer.json"),
            pointer2,
        )
        self.assertEqual(
            read_json(self.store.public / "latest.rollback.pointer.json"),
            pointer1,
        )
        self.assertNotEqual(pointer1["generation_sha256"], pointer2["generation_sha256"])

    def test_status_only_verification_materializes_status_but_hashes_every_member(self):
        pointer = self.store.publish_generation(
            snapshot_value("status-only"),
            status_value("status-only"),
            coverage_value("status-only"),
        )
        generation = self.store.root / "generations" / pointer["generation_sha256"]
        snapshot_bytes = (generation / "snapshot.json").read_bytes()
        coverage_bytes = (generation / "coverage.json").read_bytes()
        status_bytes = (generation / "status.json").read_bytes()
        parsed_payloads = []
        original_loader = store_module.strict_json_loads

        def recording_loader(data):
            parsed_payloads.append(data)
            return original_loader(data)

        with mock.patch.object(
            store_module,
            "strict_json_loads",
            side_effect=recording_loader,
        ):
            verified = read_verified_generation(
                self.store.public,
                self.store.root / "generations",
                materialize_members=("status.json",),
            )

        self.assertEqual(set(verified["members"]), {"status.json"})
        self.assertEqual(verified["members"]["status.json"]["marker"], "status-only")
        self.assertIn(status_bytes, parsed_payloads)
        self.assertIn(
            snapshot_bytes,
            parsed_payloads,
            "the snapshot receipt map must be parsed to authenticate the manifest",
        )
        self.assertNotIn(coverage_bytes, parsed_payloads)

        snapshot_path = generation / "snapshot.json"
        snapshot_path.chmod(0o644)
        corrupted = bytearray(snapshot_bytes)
        corrupted[-2] = ord(" ")
        self.assertEqual(len(corrupted), len(snapshot_bytes))
        snapshot_path.write_bytes(bytes(corrupted))
        with self.assertRaises(CanonicalDataError):
            read_verified_generation(
                self.store.public,
                self.store.root / "generations",
                materialize_members=("status.json",),
            )

    def test_storage_identity_ignores_ctime_only_filesystem_tracking(self):
        pointer = self.store.publish_generation(
            snapshot_value("ctime-stable"),
            status_value("ctime-stable"),
            coverage_value("ctime-stable"),
        )
        target = (
            self.store.root / "generations" /
            pointer["generation_sha256"] / "coverage.json"
        )
        real_fstat = store_module.os.fstat
        ctime_offset = [0]

        def ctime_only_change(descriptor):
            info = real_fstat(descriptor)
            ctime_offset[0] += 1
            return SimpleNamespace(
                st_ctime_ns=info.st_ctime_ns + ctime_offset[0],
                st_dev=info.st_dev,
                st_gid=info.st_gid,
                st_ino=info.st_ino,
                st_mode=info.st_mode,
                st_mtime_ns=info.st_mtime_ns,
                st_nlink=info.st_nlink,
                st_size=info.st_size,
                st_uid=info.st_uid,
            )

        with mock.patch.object(
            store_module.os,
            "fstat",
            side_effect=ctime_only_change,
        ):
            first = safe_regular_file_identity(target, self.store.root)
            second = safe_regular_file_identity(target, self.store.root)

        self.assertEqual(first, second)
        self.assertEqual(
            set(first),
            {"device", "gid", "inode", "mode", "mtime_ns", "size", "uid"},
        )

    def test_generation_materialization_subset_is_exact_and_fail_closed(self):
        self.store.publish_generation(
            snapshot_value("subset"),
            status_value("subset"),
            coverage_value("subset"),
        )
        with self.assertRaises(CanonicalDataError):
            read_verified_generation(
                self.store.public,
                self.store.root / "generations",
                materialize_members=(),
            )
        with self.assertRaises(CanonicalDataError):
            read_verified_generation(
                self.store.public,
                self.store.root / "generations",
                materialize_members=("unknown.json",),
            )

    def test_manifest_source_receipt_map_must_match_snapshot_exactly(self):
        pointer = self.store.publish_generation(
            snapshot_value("bound"),
            status_value("bound"),
            coverage_value("bound"),
        )
        old_root = (
            self.store.root / "generations" / pointer["generation_sha256"]
        )
        manifest = read_json(old_root / "manifest.json")
        manifest["source_head_receipt_sha256"]["synthetic"] = "f" * 64
        manifest_bytes = canonical_json_bytes(manifest)
        replacement_digest = sha256_bytes(manifest_bytes)
        replacement_root = (
            self.store.root / "generations" / replacement_digest
        )
        replacement_root.mkdir()
        for name in sorted(GENERATION_MEMBER_NAMES):
            (replacement_root / name).write_bytes(
                (old_root / name).read_bytes()
            )
        (replacement_root / "manifest.json").write_bytes(manifest_bytes)
        replacement_pointer = dict(pointer)
        replacement_pointer["generation_sha256"] = replacement_digest
        replacement_pointer["manifest_sha256"] = replacement_digest
        atomic_write_json(
            self.store.public / "latest.pointer.json",
            replacement_pointer,
        )

        with self.assertRaises(CanonicalDataError):
            read_verified_generation(
                self.store.public,
                self.store.root / "generations",
            )


class GenerationBackedApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_registry(self.root)
        self.store = LiveStore(self.root, config_value())
        self.store.initialize()
        self.pointer = self.store.publish_generation(
            snapshot_value("immutable"),
            status_value("immutable"),
            coverage_value("immutable"),
        )
        self.generations = self.store.root / "generations"

        # Compatibility mirrors are deliberately hostile. Generation-backed
        # routes must never trust these mutable files.
        atomic_write_json(
            self.store.public / "live_snapshot.json",
            snapshot_value("mutable-tamper"),
        )
        atomic_write_json(
            self.store.public / "live_status.json",
            status_value("mutable-tamper"),
        )
        atomic_write_json(
            self.store.public / "source_coverage.json",
            coverage_value("mutable-tamper"),
        )
        atomic_write_json(
            self.store.public / "operational_status.json",
            {
                "marker": "operational",
                "schema_version": "recession-monitor-v2.operational-status.v1",
                "scope": "operational_only",
            },
        )

        self.assertIn(
            "generations_root",
            inspect.signature(create_server).parameters,
            "create_server must receive the immutable generations root",
        )
        self.server = create_server(
            "127.0.0.1",
            0,
            self.store.public,
            generations_root=self.generations,
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=5)
        self.temp.cleanup()

    def request(self, path):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.port, timeout=5
        )
        connection.request(
            "GET",
            path,
            headers={"Host": "127.0.0.1:%d" % self.port},
        )
        response = connection.getresponse()
        body = response.read()
        result = (response.status, strict_json_loads(body))
        connection.close()
        return result

    def test_routes_read_verified_immutable_generation_and_separate_operational_status(self):
        status_code, status = self.request("/api/v1/status")
        self.assertEqual(status_code, 200)
        self.assertEqual(status["marker"], "immutable")

        status_code, coverage = self.request("/api/v1/sources")
        self.assertEqual(status_code, 200)
        self.assertEqual(coverage["marker"], "immutable")

        status_code, snapshot = self.request("/api/v1/snapshot")
        self.assertEqual(status_code, 200)
        self.assertEqual(
            snapshot["series"]["synthetic.series"]["latest"]["value"],
            "immutable",
        )

        status_code, series = self.request(
            "/api/v1/series/synthetic.series"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(series["latest"]["value"], "immutable")

        status_code, operational = self.request(
            "/api/v1/operational-status"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(
            operational["schema_version"],
            "recession-monitor-v2.operational-status.v1",
        )
        self.assertEqual(operational["scope"], "operational_only")
        self.assertNotEqual(operational, status)

    def test_health_degrades_on_operational_generation_binding_mismatch(self):
        atomic_write_json(
            self.store.public / "operational_status.json",
            {
                "active_generation_sha256": "f" * 64,
                "generated_at": FIXED_TIME_2,
                "schema_version": (
                    "recession-monitor-v2.live-operational-status.v1"
                ),
                "service_state": "ready",
            },
        )
        status_code, health = self.request("/healthz")
        self.assertEqual(status_code, 200)
        self.assertEqual(health["service_state"], "degraded")

    def test_every_generation_route_rejects_unrequested_member_tampering(self):
        generation = self.generations / self.pointer["generation_sha256"]
        coverage_path = generation / "coverage.json"
        coverage_path.chmod(0o644)
        coverage_path.write_bytes(coverage_path.read_bytes() + b"\n")

        routes = (
            "/healthz",
            "/api/v1/pointer",
            "/api/v1/bundle",
            "/api/v1/status",
            "/api/v1/snapshot",
            "/api/v1/sources",
            "/api/v1/series/synthetic.series",
        )
        for route in routes:
            with self.subTest(route=route):
                status_code, body = self.request(route)
                self.assertEqual(status_code, 500)
                self.assertEqual(
                    body["error"]["code"],
                    "invalid_local_state",
                )

        # Operational liveness is intentionally not evidence that an immutable
        # data generation is valid.
        status_code, operational = self.request(
            "/api/v1/operational-status"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(operational["scope"], "operational_only")

    def test_health_uses_status_only_cache_and_invalidates_on_pointer_change(self):
        self.assertTrue(
            hasattr(self.server, "read_status_generation"),
            "health needs a status-only immutable-generation reader",
        )
        with mock.patch(
            "live_data.rmv2_live.server.read_verified_generation",
            wraps=read_verified_generation,
        ) as verifier:
            first = self.server.read_status_generation()
            cached = self.server.read_status_generation()
            self.assertIs(first, cached)
            self.assertEqual(
                verifier.call_args.kwargs["materialize_members"],
                ("status.json",),
            )
            self.assertEqual(verifier.call_count, 1)

            self.store.publish_generation(
                snapshot_value("replacement", FIXED_TIME_2),
                status_value("replacement", FIXED_TIME_2),
                coverage_value("replacement", FIXED_TIME_2),
            )
            replacement = self.server.read_status_generation()

        self.assertEqual(
            replacement["members"]["status.json"]["marker"],
            "replacement",
        )
        self.assertEqual(verifier.call_count, 2)

    def test_generation_caches_reject_post_warm_member_corruption(self):
        self.server.read_generation()
        self.server.read_status_generation()
        generation = self.generations / self.pointer["generation_sha256"]
        coverage_path = generation / "coverage.json"
        coverage_path.chmod(0o644)
        corrupted = bytearray(coverage_path.read_bytes())
        corrupted[-2] = ord(" ")
        coverage_path.write_bytes(bytes(corrupted))

        with self.assertRaises(CanonicalDataError):
            self.server.read_generation()
        with self.assertRaises(CanonicalDataError):
            self.server.read_status_generation()


class BlsExactSetTests(unittest.TestCase):
    def test_latest_observation_is_not_laundered_into_preliminary(self):
        source = source_config()
        records = parse_bls_json(
            source,
            bls_payload([{
                "data": [bls_row(latest="true")],
                "seriesID": "CESX",
            }]),
            FIXED_TIME_1,
        )
        self.assertEqual(len(records), 1)
        self.assertIn("latest_observation", records[0])
        self.assertTrue(records[0]["latest_observation"])
        self.assertFalse(records[0]["preliminary"])

        records = parse_bls_json(
            source,
            bls_payload([{
                "data": [bls_row(
                    latest="true",
                    footnotes=[{"code": "P", "text": "Preliminary"}],
                )],
                "seriesID": "CESX",
            }]),
            FIXED_TIME_1,
        )
        self.assertTrue(records[0]["latest_observation"])
        self.assertTrue(records[0]["preliminary"])

    def test_duplicate_missing_and_unrequested_series_fail_exact_set_closure(self):
        source = source_config()
        source["series"]["items"].append({
            "label": "Unemployment",
            "series_id": "LNSX",
            "unit": "percent",
        })
        requested = {
            "data": [bls_row()],
            "seriesID": "CESX",
        }
        other_requested = {
            "data": [bls_row(value="4.1")],
            "seriesID": "LNSX",
        }
        bad_payloads = (
            [requested, copy.deepcopy(requested), other_requested],
            [requested],
            [requested, {
                "data": [bls_row()],
                "seriesID": "UNREQUESTED",
            }],
        )
        for rows in bad_payloads:
            with self.subTest(series_ids=[row["seriesID"] for row in rows]):
                with self.assertRaises(SourceUnavailable):
                    parse_bls_json(
                        source,
                        bls_payload(rows),
                        FIXED_TIME_1,
                    )


class LocalBoundaryTests(unittest.TestCase):
    def test_source_id_traversal_fails_in_config_and_direct_store_calls(self):
        for source_id in ("../escape", "nested/name", "nested\\name", ".", ".."):
            with self.subTest(source_id=source_id):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    config = config_value([source_config(source_id)])
                    path = write_config(root, config)
                    with self.assertRaises(CanonicalDataError):
                        load_config(path)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = LiveStore(root, config_value())
            store.initialize()
            direct_calls = (
                lambda: store.store_receipt("../escape", {"x": 1}),
                lambda: store.store_attempt("../escape", {"x": 1}),
                lambda: store.write_source_head("../escape", {"x": 1}),
                lambda: store.write_source_status("../escape", {"x": 1}),
            )
            for call in direct_calls:
                with self.subTest(call=call):
                    with self.assertRaises(CanonicalDataError):
                        call()

    def test_store_public_and_runtime_roots_must_be_pairwise_disjoint(self):
        overlaps = (
            {"root": "live", "public": "live", "runtime": "runtime"},
            {"root": "live", "public": "live/public", "runtime": "runtime"},
            {"root": "live", "public": "public", "runtime": "live/runtime"},
            {"root": "live/runtime", "public": "public", "runtime": "live"},
        )
        for paths in overlaps:
            with self.subTest(paths=paths):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    config = config_value()
                    config["store"] = paths
                    path = write_config(root, config)
                    with self.assertRaises(CanonicalDataError):
                        load_config(path)
                    with self.assertRaises(CanonicalDataError):
                        LiveStore(root, config)

    def test_local_env_rejects_symlink_and_group_or_world_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = root / "secret.env"
            secret.write_text("RMV2_SAFE_SECRET=value\n", encoding="utf-8")
            secret.chmod(0o600)
            alias = root / "local.env"
            alias.symlink_to(secret)
            with self.assertRaises(CanonicalDataError):
                load_env_file(alias)

            secret.chmod(0o644)
            with self.assertRaises(CanonicalDataError):
                load_env_file(secret)

            secret.chmod(0o600)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("RMV2_SAFE_SECRET", None)
                load_env_file(secret)
                self.assertEqual(os.environ["RMV2_SAFE_SECRET"], "value")
                os.environ.pop("RMV2_SAFE_SECRET", None)

    def test_safe_regular_file_rejects_replaced_symlink_hardlink_and_fifo(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root.parent / (root.name + "-outside.json")
            outside.write_bytes(b'{"outside":true}')
            try:
                replaced = root / "replaced.json"
                replaced.write_bytes(b'{"safe":true}')
                replaced.unlink()
                replaced.symlink_to(outside)
                with self.assertRaises(CanonicalDataError):
                    safe_regular_file(replaced, root)

                target = root / "target.json"
                target.write_bytes(b'{"safe":true}')
                hardlink = root / "hardlink.json"
                os.link(str(target), str(hardlink))
                with self.assertRaises(CanonicalDataError):
                    safe_regular_file(hardlink, root)

                fifo = root / "special.pipe"
                os.mkfifo(str(fifo))
                with self.assertRaises(CanonicalDataError):
                    safe_regular_file(fifo, root)
            finally:
                try:
                    outside.unlink()
                except FileNotFoundError:
                    pass

    def test_fifo_rejection_cannot_block_either_reader(self):
        """REGRESSION: a FIFO at a member path must be REJECTED, not waited on.

        POSIX open(fifo, O_RDONLY) blocks until a writer appears. Both readers
        opened without O_NONBLOCK, so with no writer they hung forever inside
        open() and the S_ISREG rejection below it was unreachable — an unbounded
        stall of the verifier/server on a path an attacker or an interrupted
        producer can create. Each reader must fail fast; the hard join bound
        here turns a re-regression into a failure rather than a hung suite.
        """
        for reader in (safe_regular_file, safe_regular_file_identity):
            with self.subTest(reader=reader.__name__):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    fifo = root / "member.json"
                    os.mkfifo(str(fifo))
                    outcome = {}

                    def _call(reader=reader, fifo=fifo, root=root):
                        try:
                            reader(fifo, root)
                        except CanonicalDataError as exc:  # expected
                            outcome["error"] = str(exc)
                        except BaseException as exc:  # noqa: BLE001
                            outcome["error"] = "unexpected: %r" % (exc,)
                        else:
                            outcome["error"] = "no rejection raised"

                    worker = threading.Thread(target=_call, daemon=True)
                    worker.start()
                    worker.join(10)
                    self.assertFalse(
                        worker.is_alive(),
                        "%s blocked on a FIFO instead of rejecting it" % reader.__name__,
                    )
                    self.assertIn("not a regular file", outcome.get("error", ""))


class VerifyGenerationTests(unittest.TestCase):
    def _fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        config_path = write_config(root)
        config = load_config(config_path)
        store = LiveStore(root, config)
        store.initialize()
        snapshot = snapshot_value("verified")
        snapshot["sources"] = []
        pointer = store.publish_generation(
            snapshot,
            status_value("verified"),
            coverage_value("verified"),
        )
        args = SimpleNamespace(
            config=str(config_path),
            project_root=str(root),
        )
        return temp, store, pointer, args

    def test_verify_command_accepts_intact_generation(self):
        temp, _store, _pointer, args = self._fixture()
        try:
            with mock.patch.object(cli, "_print") as output:
                self.assertEqual(cli.command_verify(args), 0)
            payload = output.call_args.args[0]
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["checked_source_heads"], [])
            self.assertTrue(payload["no_ai_endpoints"])
        finally:
            temp.cleanup()

    def test_verify_command_reads_each_published_normalized_blob_once(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        try:
            config_path = write_config(root)
            config = load_config(config_path)
            store = LiveStore(root, config)
            store.initialize()
            binding = install_source_evidence(store)

            matrix_root = root / "live_data" / "catalog"
            matrix_root.mkdir(parents=True)
            matrix = {
                "rows": [{
                    "record_kind": "active_collector",
                    "source_id": "bls_test",
                }],
            }
            matrix["definition_sha256"] = source_matrix_definition_sha256(
                matrix["rows"]
            )
            atomic_write_json(
                matrix_root / "source_matrix.v1.json",
                matrix,
            )

            snapshot = snapshot_value("single-pass")
            snapshot["sources"] = [binding]
            status = status_value("single-pass")
            status["snapshot_source_count"] = 1
            status["source_matrix"] = {
                "definition_sha256": matrix["definition_sha256"],
                "row_count": 1,
            }
            store.publish_generation(
                snapshot,
                status,
                coverage_value("single-pass"),
            )
            args = SimpleNamespace(
                config=str(config_path),
                project_root=str(root),
            )

            normalized_paths = []
            original = store_module.safe_regular_file

            def counted(path, allowed_root):
                data = original(path, allowed_root)
                if "/normalized/sha256/" in Path(path).as_posix():
                    normalized_paths.append(Path(path).as_posix())
                return data

            with mock.patch.object(
                store_module,
                "safe_regular_file",
                side_effect=counted,
            ):
                with mock.patch.object(cli, "_print"):
                    self.assertEqual(cli.command_verify(args), 0)

            self.assertEqual(len(normalized_paths), 1, normalized_paths)
        finally:
            temp.cleanup()

    def test_verify_command_rejects_manifest_member_and_pointer_drift(self):
        mutations = (
            "manifest",
            "member",
            "pointer",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                temp, store, pointer, args = self._fixture()
                try:
                    generation = (
                        store.root / "generations" /
                        pointer["generation_sha256"]
                    )
                    if mutation == "manifest":
                        path = generation / "manifest.json"
                        path.chmod(0o644)
                        path.write_bytes(path.read_bytes() + b"\n")
                    elif mutation == "member":
                        path = generation / "status.json"
                        self.assertTrue(
                            path.is_file(),
                            "status.json must be an immutable generation member",
                        )
                        path.chmod(0o644)
                        path.write_bytes(path.read_bytes() + b"\n")
                    else:
                        value = read_json(
                            store.public / "latest.pointer.json"
                        )
                        self.assertIn("snapshot_sha256", value)
                        value["snapshot_sha256"] = "0" * 64
                        atomic_write_json(
                            store.public / "latest.pointer.json",
                            value,
                        )
                    with mock.patch.object(cli, "_print"):
                        with self.assertRaises(CanonicalDataError):
                            cli.command_verify(args)
                finally:
                    temp.cleanup()

    def test_config_generation_closure_rejects_stale_scheduler_matrix(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        try:
            config_path = write_config(root)
            config = load_config(config_path)
            store = LiveStore(root, config)
            store.initialize()
            closure_binding = install_source_evidence(store)
            closure_receipt = closure_binding["receipt_sha256"]
            matrix_root = root / "live_data" / "catalog"
            matrix_root.mkdir(parents=True)
            matrix = {
                "rows": [{
                    "record_kind": "active_collector",
                    "source_id": "bls_test",
                }],
            }
            matrix["definition_sha256"] = source_matrix_definition_sha256(
                matrix["rows"]
            )
            atomic_write_json(
                matrix_root / "source_matrix.v1.json",
                matrix,
            )
            snapshot = snapshot_value("closure")
            snapshot["sources"] = [closure_binding]
            status = status_value("closure")
            status["snapshot_source_count"] = 1
            status["source_matrix"] = {
                "definition_sha256": matrix["definition_sha256"],
                "row_count": 1,
            }
            store.publish_generation(
                snapshot,
                status,
                coverage_value("closure"),
            )

            self.assertEqual(
                cli._verify_config_generation_closure(
                    root,
                    config,
                    store,
                )["status"],
                "PASS",
            )

            drifted_head = store.read_source_head("bls_test")
            drifted_head["receipt_sha256"] = sha256_bytes(b"drifted receipt")
            store.write_source_head("bls_test", drifted_head)
            with self.assertRaises(CanonicalDataError):
                cli._verify_config_generation_closure(
                    root,
                    config,
                    store,
                )
            restored_head = store.read_source_head("bls_test")
            restored_head["receipt_sha256"] = closure_receipt
            store.write_source_head("bls_test", restored_head)

            status["source_matrix"]["row_count"] = 0
            store.publish_generation(
                dict(snapshot, generated_at=FIXED_TIME_2),
                dict(status, generated_at=FIXED_TIME_2),
                coverage_value("stale", FIXED_TIME_2),
            )
            with self.assertRaises(CanonicalDataError):
                cli._verify_config_generation_closure(
                    root,
                    config,
                    store,
                )
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
