from __future__ import absolute_import

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.canonical import canonical_json_bytes
from live_data.rmv2_live.store import LiveStore


SCHEMA_VERSION = "recession-monitor-v2.feed-factory-inventory.v1"
RETRIEVED_AT = "2026-07-30T12:00:00Z"


def json_bytes(value):
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8") +
        b"\n"
    )


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def source(source_id):
    return {
        "enabled": True,
        "method_version": "%s.v1" % source_id,
        "source_id": source_id,
    }


def install_source_evidence(store, source_id):
    raw = ("publisher-%s" % source_id).encode("utf-8")
    source_digest, _ = store.store_source_object(raw)
    record = {
        "observation_period": "2026-01",
        "retrieved_at": RETRIEVED_AT,
        "series_id": "%s.SERIES" % source_id,
        "source_bytes_sha256": source_digest,
        "source_id": source_id,
        "unit": "index",
        "validated_at": RETRIEVED_AT,
        "value": "1.0",
    }
    normalized = {
        "parser_id": "rmv2-live/status_test",
        "records": [record],
        "retrieved_at": RETRIEVED_AT,
        "schema_version": "recession-monitor-v2.normalized-source.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source_id,
    }
    normalized_digest, _ = store.store_normalized(normalized)
    receipt = {
        "clocks": {
            "provider_available_at": RETRIEVED_AT,
            "publisher_released_at": None,
            "retrieved_at": RETRIEVED_AT,
            "validated_at": RETRIEVED_AT,
        },
        "information_set_mode": "current_revised",
        "normalized_sha256": normalized_digest,
        "outcome": "retrieved_and_validated",
        "predecessor_receipt_sha256": None,
        "publisher": "Fixture Publisher",
        "request": {
            "body_sha256": None,
            "conditional_headers": {},
            "method": "GET",
            "parameters": {},
            "url": "https://publisher.example/%s" % source_id,
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
        "adapter": "status_test",
        "etag": None,
        "last_modified": None,
        "latest_observation_period": "2026-01",
        "method_version": "status-test-v1",
        "normalized_sha256": normalized_digest,
        "receipt_sha256": receipt_digest,
        "record_count": 1,
        "retrieved_at": RETRIEVED_AT,
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


def store_config():
    return {
        "public": "live_data/public",
        "root": "live_data/store",
        "runtime": "live_data/runtime",
    }


def write_active_generation(root, live_source_ids, coverage):
    store = LiveStore(Path(root), {"store": store_config()})
    store.initialize()
    bindings = [
        install_source_evidence(store, source_id)
        for source_id in sorted(live_source_ids)
    ]
    snapshot = {
        "generated_at": RETRIEVED_AT,
        "schema_version": "recession-monitor-v2.live-snapshot.v1",
        "series": {},
        "sources": bindings,
    }
    status = {
        "generated_at": RETRIEVED_AT,
        "schema_version": "recession-monitor-v2.live-status.v1",
        "service_state": "ready",
    }
    pointer = store.publish_generation(snapshot, status, coverage)
    return pointer["generation_sha256"]


def write_candidate(
    root,
    source_value,
    bundle_id="a" * 64,
    predecessor_config_sha256=None,
):
    candidate_root = (
        Path(root) / "live_data" / "feed_factory" /
        "candidates" / source_value["source_id"] / bundle_id
    )
    if predecessor_config_sha256 is None:
        active_config = (
            Path(root) / "live_data" / "config" / "sources.v1.json"
        )
        predecessor_config_sha256 = hashlib.sha256(
            active_config.read_bytes()
        ).hexdigest()
    write_json(
        candidate_root / "manifest.json",
        {
            "predecessor_config_sha256": predecessor_config_sha256,
            "schema_version": "recession-monitor-v2.feed-onboarding-bundle.v3",
            "scientific_effect": "none",
            "source_id": source_value["source_id"],
            "status": "CANDIDATE_NOT_ACTIVE",
        },
    )
    write_json(
        candidate_root / "candidate.sources.v1.json",
        {
            "schema_version": "recession-monitor-v2.live-data-config.v1",
            "sources": [source_value],
        },
    )


def write_factory_artifacts(root, source_id):
    factory = Path(root) / "live_data" / "feed_factory"
    write_json(
        factory / "drafts" / ("%s.v1.json" % source_id),
        {
            "schema_version": "recession-monitor-v2.feed-discovery-spec.v1",
            "source": {"source_id": source_id},
        },
    )
    write_json(
        factory / "probes" / source_id / ("b" * 64) /
        "probe.receipt.json",
        {
            "schema_version": "recession-monitor-v2.feed-probe-receipt.v1",
            "source_id": source_id,
        },
    )
    write_json(
        factory / "recipes" / ("%s.%s.v1.json" % (source_id, "c" * 64)),
        {
            "schema_version": "recession-monitor-v2.feed-onboarding-spec.v1",
            "source": {"source_id": source_id},
        },
    )


def write_project(
    root,
    enabled_sources,
    live_source_ids,
    health,
    service_state="ready",
    recovery_required=False,
    include_normal_reservation=True,
    include_exception_reservations=True,
    include_blocked_exceptions=True,
):
    root = Path(root)
    coverage_rows = []
    coverage_counts = {
        "blocked_rights": 0,
        "quarantined_target_bearing": 0,
    }
    if include_blocked_exceptions:
        coverage_rows = [
            {
                "live_state": "blocked_rights",
                "source_id": "licensed_one",
            },
            {
                "live_state": "blocked_rights",
                "source_id": "licensed_two",
            },
            {
                "live_state": "quarantined_target_bearing",
                "source_id": "target_one",
            },
        ]
        coverage_counts = {
            "blocked_rights": 2,
            "quarantined_target_bearing": 1,
        }
    coverage = {
        "counts": coverage_counts,
        "generated_at": RETRIEVED_AT,
        "rows": coverage_rows,
        "schema_version": "recession-monitor-v2.source-coverage.v1",
        "total_source_families": len(coverage_rows),
    }
    generation_id = write_active_generation(
        root,
        live_source_ids,
        coverage,
    )
    write_json(
        root / "live_data" / "config" / "sources.v1.json",
        {
            "schema_version": "recession-monitor-v2.live-data-config.v1",
            "store": store_config(),
            "sources": enabled_sources,
        },
    )
    reservations = []
    if include_exception_reservations:
        reservations.extend([
            {
                "auth_env": "EXAMPLE_API_KEY",
                "role": "core_input",
                "source_id": "planned_credential",
            },
            {
                "auth_env": None,
                "role": "lower_priority_context",
                "source_id": "planned_lower",
            },
        ])
    if include_normal_reservation:
        reservations.insert(0, {
            "auth_env": None,
            "role": "core_input",
            "source_id": "planned_normal",
        })
    write_json(
        root / "live_data" / "config" / "planned_sources.v1.json",
        {
            "schema_version": "recession-monitor-v2.planned-sources.v1",
            "sources": reservations,
        },
    )
    write_json(
        root / "live_data" / "public" / "operational_status.json",
        {
            "active_generation_sha256": generation_id,
            "current_source_health": health,
            "generation_recovery_required": recovery_required,
            "schema_version": "recession-monitor-v2.operational-status.v1",
            "service_state": service_state,
        },
    )
    return generation_id


def tree_fingerprint(root):
    result = {}
    root = Path(root)
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        data = path.read_bytes()
        result[str(path.relative_to(root))] = {
            "mode": path.stat().st_mode,
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return result


class FeedFactoryStatusTests(unittest.TestCase):
    def run_inventory(self, root, json_output=True):
        command = [
            sys.executable,
            "-B",
            "-m",
            "live_data.rmv2_live",
            "--project-root",
            str(root),
            "feed-factory",
            "inventory",
        ]
        if json_output:
            command.append("--json")
        return subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=30,
        )

    def test_json_inventory_reports_complete_scoped_lifecycle_without_writes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            generation_id = write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
                include_exception_reservations=False,
                include_blocked_exceptions=False,
            )
            write_factory_artifacts(root, "source_live")
            write_candidate(root, live)
            before = tree_fingerprint(root)

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(
                payload["overall_state"],
                "SCOPED_WORK_COMPLETE",
            )
            self.assertEqual(
                payload["active_generation"]["generation_id"],
                generation_id,
            )
            self.assertEqual(
                payload["active_generation"]["source_count"],
                1,
            )
            self.assertEqual(
                payload["sources"]["enabled"],
                {"count": 1, "source_ids": ["source_live"]},
            )
            self.assertEqual(
                payload["sources"]["healthy"],
                {"count": 1, "source_ids": ["source_live"]},
            )
            self.assertEqual(
                payload["sources"]["failed"],
                {"count": 0, "source_ids": []},
            )
            self.assertEqual(
                payload["sources"]["not_yet_refreshed"],
                {"count": 0, "source_ids": []},
            )
            for artifact_name in (
                "drafts",
                "probes",
                "recipes",
                "candidates",
            ):
                artifact = payload["factory_artifacts"][artifact_name]
                self.assertEqual(artifact["artifact_count"], 1)
                self.assertEqual(
                    artifact["source_ids"],
                    ["source_live"],
                )
            self.assertEqual(
                payload["reservations"]["counts"],
                {
                    "credential": 0,
                    "lower_priority": 0,
                    "normal": 0,
                    "total": 0,
                },
            )
            self.assertEqual(
                payload["blocked_or_deferred"]["rights_blocked"],
                {"count": 0, "source_ids": []},
            )
            self.assertEqual(
                payload["blocked_or_deferred"]["target_quarantined"],
                {"count": 0, "source_ids": []},
            )
            candidate = payload["candidate_lifecycle"][0]
            self.assertTrue(candidate["config_applied"])
            self.assertTrue(candidate["live"])
            self.assertEqual(candidate["state"], "LIVE")
            self.assertEqual(payload["pending_candidates"], [])
            self.assertIn("not every possible", payload["scope_notice"].lower())
            self.assertNotIn("complete", payload["scope_notice"].lower())
            self.assertEqual(tree_fingerprint(root), before)

    def test_exception_only_scope_has_distinct_blocked_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
                include_exception_reservations=True,
                include_blocked_exceptions=True,
            )

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                payload["overall_state"],
                "BLOCKED_EXCEPTIONS_ONLY",
            )
            self.assertEqual(
                payload["reservations"]["counts"]["credential"],
                1,
            )
            self.assertEqual(
                payload["reservations"]["counts"]["lower_priority"],
                1,
            )
            self.assertEqual(
                payload["blocked_or_deferred"]["rights_blocked"]["count"],
                2,
            )
            self.assertEqual(
                payload["blocked_or_deferred"]["target_quarantined"]["count"],
                1,
            )

    def test_public_coverage_cannot_override_authenticated_generation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
                include_exception_reservations=False,
                include_blocked_exceptions=True,
            )
            write_json(
                root / "live_data" / "public" / "source_coverage.json",
                {
                    "counts": {
                        "blocked_rights": 0,
                        "quarantined_target_bearing": 0,
                    },
                    "generated_at": RETRIEVED_AT,
                    "rows": [],
                    "schema_version":
                        "recession-monitor-v2.source-coverage.v1",
                    "total_source_families": 0,
                },
            )

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_state"], "DEGRADED")
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(
                payload["blocked_or_deferred"]["rights_blocked"],
                {
                    "count": 2,
                    "source_ids": ["licensed_one", "licensed_two"],
                },
            )
            self.assertEqual(
                payload["blocked_or_deferred"]["target_quarantined"],
                {"count": 1, "source_ids": ["target_one"]},
            )
            self.assertTrue(any(
                "differs from authenticated generation" in error
                for error in payload["errors"]
            ))

    def test_enabled_source_is_fulfilled_not_outstanding_reservation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
                include_exception_reservations=False,
                include_blocked_exceptions=False,
            )
            write_json(
                root / "live_data" / "config" /
                "planned_sources.v1.json",
                {
                    "schema_version":
                        "recession-monitor-v2.planned-sources.v1",
                    "sources": [{
                        "auth_env": None,
                        "role": "core_input",
                        "source_id": "source_live",
                    }],
                },
            )

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                payload["overall_state"],
                "SCOPED_WORK_COMPLETE",
            )
            self.assertEqual(
                payload["reservations"]["configured_counts"],
                {
                    "credential": 0,
                    "lower_priority": 0,
                    "normal": 1,
                    "total": 1,
                },
            )
            self.assertEqual(
                payload["reservations"]["counts"],
                {
                    "credential": 0,
                    "lower_priority": 0,
                    "normal": 0,
                    "total": 0,
                },
            )
            self.assertEqual(
                payload["reservations"]["fulfilled"],
                {"count": 1, "source_ids": ["source_live"]},
            )

    def test_unapplied_candidate_is_ready_for_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            review = source("source_review")
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
            )
            write_factory_artifacts(root, "source_review")
            write_candidate(root, review)

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_state"], "READY_FOR_REVIEW")
            self.assertEqual(
                [item["source_id"] for item in payload["pending_candidates"]],
                ["source_review"],
            )
            self.assertEqual(
                payload["candidate_lifecycle"][0]["state"],
                "READY_FOR_REVIEW",
            )

    def test_configured_source_awaiting_first_generation_is_degraded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            waiting = source("source_waiting")
            write_project(
                root,
                [live, waiting],
                ["source_live"],
                {"source_live": "healthy"},
            )
            write_factory_artifacts(root, "source_waiting")
            write_candidate(root, waiting)

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_state"], "DEGRADED")
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(
                payload["sources"]["not_yet_refreshed"]["source_ids"],
                ["source_waiting"],
            )
            candidate = payload["candidate_lifecycle"][0]
            self.assertTrue(candidate["config_applied"])
            self.assertFalse(candidate["live"])
            self.assertEqual(candidate["state"], "CONFIGURED_AWAITING_REFRESH")

    def test_same_source_candidate_update_is_ready_for_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            update = dict(live)
            update["method_version"] = "source_live.v2"
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
                include_exception_reservations=False,
                include_blocked_exceptions=False,
            )
            write_candidate(root, update)

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_state"], "READY_FOR_REVIEW")
            candidate = payload["candidate_lifecycle"][0]
            self.assertFalse(candidate["config_applied"])
            self.assertTrue(candidate["source_already_active"])
            self.assertEqual(candidate["state"], "READY_FOR_REVIEW")

    def test_stale_predecessor_candidate_is_historical_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            stale_update = dict(live)
            stale_update["method_version"] = "source_live.v0"
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
                include_exception_reservations=False,
                include_blocked_exceptions=False,
            )
            write_candidate(
                root,
                stale_update,
                predecessor_config_sha256="0" * 64,
            )

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                payload["overall_state"],
                "SCOPED_WORK_COMPLETE",
            )
            self.assertEqual(payload["pending_candidates"], [])
            candidate = payload["candidate_lifecycle"][0]
            self.assertFalse(candidate["config_applied"])
            self.assertTrue(candidate["source_already_active"])
            self.assertEqual(
                candidate["state"],
                "SUPERSEDED_OR_HISTORICAL",
            )

    def test_normal_actionable_reservation_keeps_status_working(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=True,
            )

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_state"], "WORKING")
            self.assertEqual(
                payload["completion_blockers"][
                    "normal_actionable_reservations"
                ],
                ["planned_normal"],
            )

    def test_failed_source_or_recovery_requirement_is_degraded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bad = source("source_bad")
            write_project(
                root,
                [bad],
                ["source_bad"],
                {"source_bad": "failed"},
                service_state="degraded",
                recovery_required=True,
            )

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_state"], "DEGRADED")
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(
                payload["sources"]["failed"]["source_ids"],
                ["source_bad"],
            )
            self.assertTrue(
                payload["active_generation"]["recovery_required"]
            )

    def test_rogue_operational_health_entry_is_degraded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            write_project(
                root,
                [live],
                ["source_live"],
                {
                    "rogue_source": "healthy",
                    "source_live": "healthy",
                },
                include_normal_reservation=False,
                include_exception_reservations=False,
                include_blocked_exceptions=False,
            )

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_state"], "DEGRADED")
            self.assertTrue(any(
                "health" in error and "exact" in error
                for error in payload["errors"]
            ))

    def test_incomplete_authoritative_generation_fails_closed_as_degraded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
                include_exception_reservations=False,
                include_blocked_exceptions=False,
            )
            pointer_path = (
                root / "live_data" / "public" / "latest.pointer.json"
            )
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
            generation_member_path = (
                root / "live_data" / "store" / "generations" /
                pointer["generation_sha256"] / "status.json"
            )
            generation_member_path.unlink()

            result = self.run_inventory(root)

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_state"], "DEGRADED")
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(payload["errors"])
            self.assertEqual(
                payload["active_generation"]["source_count"],
                0,
            )

    def test_default_inventory_is_concise_human_progress_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = source("source_live")
            write_project(
                root,
                [live],
                ["source_live"],
                {"source_live": "healthy"},
                include_normal_reservation=False,
                include_exception_reservations=False,
                include_blocked_exceptions=False,
            )

            result = self.run_inventory(root, json_output=False)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Feed Factory Status", result.stdout)
            self.assertIn("SCOPED_WORK_COMPLETE", result.stdout)
            self.assertIn("1 enabled", result.stdout)
            self.assertIn("1 healthy", result.stdout)
            self.assertIn("0 failed", result.stdout)
            self.assertIn("0 awaiting first refresh", result.stdout)
            self.assertIn("not every possible", result.stdout.lower())
            with self.assertRaises(ValueError):
                json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
