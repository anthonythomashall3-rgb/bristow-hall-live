from __future__ import absolute_import

import copy
import fcntl
import hashlib
import importlib.util
import json
import os
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


try:
    from live_data.rmv2_autopilot import __main__ as autopilot_cli
    from live_data.rmv2_autopilot.runner import (
        DefaultExecutor,
        QueueContractError,
        ServiceBusyError,
        _validate_inventory,
        derive_overall_state,
        load_queue,
        read_latest_status,
        run_cycle,
    )
except ImportError:
    autopilot_cli = None
    DefaultExecutor = None
    QueueContractError = None
    ServiceBusyError = None
    _validate_inventory = None
    derive_overall_state = None
    load_queue = None
    read_latest_status = None
    run_cycle = None


SHA256_ZERO = "0" * 64


def canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def base_policy(actions=None, allow_network=False, allow_mutation=False):
    return {
        "allow_mutation": allow_mutation,
        "allow_network": allow_network,
        "allowed_actions": actions or ["report_only", "verify_live"],
        "completion_scope": "registered_and_reserved_project_scope",
        "no_ai": True,
        "rights_bypass_authorized": False,
        "science_authorized": False,
        "secrets_embedded": False,
        "target_access_authorized": False,
    }


def task(
    task_id,
    action="report_only",
    enabled=True,
    prerequisites=None,
    parameters=None,
    reviewed=False,
    exception_kind=None,
    artifact=None,
    predecessors=None,
    receipt=None,
):
    return {
        "action": action,
        "artifact": artifact,
        "enabled": enabled,
        "exception_kind": exception_kind,
        "expected_predecessors": predecessors or [],
        "parameters": parameters or {},
        "prerequisites": prerequisites or [],
        "required_receipt": receipt,
        "reviewed": reviewed,
        "task_id": task_id,
    }


def base_queue(tasks=None, policy=None):
    return {
        "policy": policy or base_policy(),
        "queue_id": "rmv2-data-autopilot-test.v1",
        "schema_version": "recession-monitor-v2.data-autopilot-queue.v1",
        "tasks": tasks or [
            task("report-scope"),
            task(
                "verify-live",
                action="verify_live",
                prerequisites=["report-scope"],
            ),
        ],
    }


def healthy_inventory():
    empty_collection = {
        "artifact_count": 0,
        "paths": [],
        "source_count": 0,
        "source_ids": [],
    }
    return {
        "active_generation": {
            "generation_id": "a" * 64,
            "recovery_required": False,
            "source_count": 2,
            "source_ids": ["one", "two"],
        },
        "blocked_or_deferred": {
            "rights_blocked": {"count": 0, "source_ids": []},
            "target_quarantined": {"count": 0, "source_ids": []},
        },
        "candidate_lifecycle": [],
        "completion_blockers": {
            "credential_exceptions": [],
            "failed_sources": [],
            "lower_priority_exceptions": [],
            "normal_actionable_reservations": [],
            "not_yet_refreshed_sources": [],
            "ready_for_review_candidates": [],
            "rights_exceptions": [],
            "target_quarantine_exceptions": [],
            "unresolved_factory_sources": [],
        },
        "counts": {
            "candidates": 0,
            "drafts": 0,
            "probes": 0,
            "recipes": 0,
        },
        "errors": [],
        "factory_artifacts": {
            "candidates": dict(empty_collection),
            "drafts": dict(empty_collection),
            "probes": dict(empty_collection),
            "recipes": dict(empty_collection),
        },
        "factory_root": "/tmp/rmv2-feed-factory",
        "overall_state": "SCOPED_WORK_COMPLETE",
        "overall_state_reason": "The scoped acquisition inventory is complete.",
        "pending_candidates": [],
        "reservations": {
            "configured_counts": {
                "credential": 0,
                "lower_priority": 0,
                "normal": 0,
                "total": 0,
            },
            "configured_source_ids": {
                "credential": [],
                "lower_priority": [],
                "normal": [],
            },
            "counts": {
                "credential": 0,
                "lower_priority": 0,
                "normal": 0,
                "total": 0,
            },
            "fulfilled": {
                "count": 0,
                "source_ids": [],
            },
            "source_ids": {
                "credential": [],
                "lower_priority": [],
                "normal": [],
            },
        },
        "schema_version": "recession-monitor-v2.feed-factory-inventory.v1",
        "scientific_effect": "none",
        "scope_notice": "Acquisition inventory only.",
        "sources": {
            "enabled": {"count": 2, "source_ids": ["one", "two"]},
            "failed": {"count": 0, "source_ids": []},
            "healthy": {"count": 2, "source_ids": ["one", "two"]},
            "not_yet_refreshed": {"count": 0, "source_ids": []},
        },
        "status": "PASS",
    }


class AutopilotTestCase(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(
            load_queue,
            "live_data.rmv2_autopilot must exist before these tests can pass",
        )
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "live_data" / "config").mkdir(parents=True)
        (self.root / "live_data" / "runtime").mkdir(parents=True)
        self.queue_path = (
            self.root / "live_data" / "config" / "autopilot_queue.v1.json"
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_queue(self, value=None):
        self.queue_path.write_bytes(canonical_bytes(value or base_queue()))
        return self.queue_path

    def load(self, value=None):
        return load_queue(self.root, self.write_queue(value))


class QueueContractTests(AutopilotTestCase):
    def test_loads_an_exact_non_ai_queue(self):
        loaded = self.load()
        self.assertEqual(
            loaded.queue["schema_version"],
            "recession-monitor-v2.data-autopilot-queue.v1",
        )
        self.assertEqual(loaded.queue_sha256, sha256(self.queue_path.read_bytes()))
        self.assertEqual(
            [item["task_id"] for item in loaded.queue["tasks"]],
            ["report-scope", "verify-live"],
        )

    def test_rejects_duplicate_json_keys_and_duplicate_task_ids(self):
        self.queue_path.write_bytes(
            b'{"policy":{},"policy":{},"queue_id":"x",'
            b'"schema_version":"recession-monitor-v2.data-autopilot-queue.v1",'
            b'"tasks":[]}'
        )
        with self.assertRaisesRegex(QueueContractError, "duplicate JSON key"):
            load_queue(self.root, self.queue_path)

        value = base_queue([
            task("same"),
            task("same"),
        ])
        with self.assertRaisesRegex(QueueContractError, "duplicate task_id"):
            self.load(value)

    def test_rejects_extra_fields_and_unsupported_actions(self):
        value = base_queue()
        value["unexpected"] = True
        with self.assertRaisesRegex(QueueContractError, "key mismatch"):
            self.load(value)

        value = base_queue([task("invent", action="invent_work")])
        value["policy"]["allowed_actions"] = ["invent_work"]
        with self.assertRaisesRegex(QueueContractError, "unsupported action"):
            self.load(value)

    def test_rejects_symlinked_and_hardlinked_queue_files(self):
        target = self.root / "queue-target.json"
        target.write_bytes(canonical_bytes(base_queue()))
        self.queue_path.symlink_to(target)
        with self.assertRaisesRegex(QueueContractError, "regular unlinked file"):
            load_queue(self.root, self.queue_path)
        self.queue_path.unlink()

        os.link(str(target), str(self.queue_path))
        with self.assertRaisesRegex(QueueContractError, "regular unlinked file"):
            load_queue(self.root, self.queue_path)

    def test_rejects_unsafe_artifact_paths_and_embedded_secrets(self):
        value = base_queue([
            task(
                "prepare",
                action="factory_prepare",
                parameters={"draft_path": "../outside.json"},
                reviewed=True,
                artifact={
                    "path": "../outside.json",
                    "sha256": SHA256_ZERO,
                },
                predecessors=[{
                    "path": "live_data/config/sources.v1.json",
                    "sha256": SHA256_ZERO,
                }],
            ),
        ], base_policy(
            ["factory_prepare"],
            allow_network=True,
            allow_mutation=True,
        ))
        with self.assertRaisesRegex(QueueContractError, "unsafe project path"):
            self.load(value)

        value = base_queue()
        value["policy"]["api_token"] = "do-not-store-this"
        with self.assertRaisesRegex(
            QueueContractError,
            "embedded secret|key mismatch",
        ):
            self.load(value)

    def test_rejects_rights_target_science_and_ai_authority(self):
        for field, replacement in (
            ("rights_bypass_authorized", True),
            ("target_access_authorized", True),
            ("science_authorized", True),
            ("no_ai", False),
            ("secrets_embedded", True),
        ):
            value = base_queue()
            value["policy"][field] = replacement
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    QueueContractError,
                    "policy prohibits|no_ai|secrets",
                ):
                    self.load(value)

    def test_rejects_unknown_or_forward_prerequisites(self):
        value = base_queue([
            task("first", prerequisites=["later"]),
            task("later"),
        ])
        with self.assertRaisesRegex(
            QueueContractError,
            "prerequisite must name an earlier task",
        ):
            self.load(value)

        value = base_queue([task("first", prerequisites=["missing"])])
        with self.assertRaisesRegex(
            QueueContractError,
            "prerequisite must name an earlier task",
        ):
            self.load(value)

    def test_rejects_unreviewed_apply_and_mutation_without_exact_predecessor(self):
        value = base_queue([
            task(
                "apply",
                action="factory_apply_reviewed",
                parameters={"bundle_path": "live_data/feed_factory/x/manifest.json"},
                reviewed=False,
                artifact={
                    "path": "live_data/feed_factory/x/manifest.json",
                    "sha256": SHA256_ZERO,
                },
                predecessors=[{
                    "path": "live_data/config/sources.v1.json",
                    "sha256": SHA256_ZERO,
                }],
            ),
        ], base_policy(
            ["factory_apply_reviewed"],
            allow_mutation=True,
        ))
        with self.assertRaisesRegex(QueueContractError, "reviewed"):
            self.load(value)

        value["tasks"][0]["reviewed"] = True
        value["tasks"][0]["expected_predecessors"] = []
        with self.assertRaisesRegex(QueueContractError, "predecessor"):
            self.load(value)

    def test_rejects_network_or_mutation_actions_not_allowed_by_policy(self):
        value = base_queue([
            task(
                "refresh",
                action="targeted_refresh",
                parameters={"source_id": "one"},
                reviewed=True,
                predecessors=[{
                    "path": "live_data/config/sources.v1.json",
                    "sha256": SHA256_ZERO,
                }],
            ),
        ], base_policy(["targeted_refresh"]))
        with self.assertRaisesRegex(
            QueueContractError,
            "allow_network|allow_mutation",
        ):
            self.load(value)

    def test_rejects_unclassified_exception_kind(self):
        value = base_queue([
            task(
                "unknown-exception",
                enabled=False,
                exception_kind="anything_goes",
            ),
        ])
        with self.assertRaisesRegex(QueueContractError, "exception_kind"):
            self.load(value)


class CycleTests(AutopilotTestCase):
    def persisted_cycle(self, process_id=103):
        self.write_queue()
        calls = []

        def executor(action, parameters, project_root):
            calls.append(action)
            return {"status": "PASS"}

        kwargs = {
            "executor": executor,
            "inventory_provider": healthy_inventory,
            "clock": lambda: "2026-07-30T20:00:00Z",
            "process_id": process_id,
        }
        result = run_cycle(self.root, self.queue_path, **kwargs)
        runtime = self.root / "live_data" / "runtime" / "autopilot"
        attempt_path = (
            runtime / "attempts" / ("%s.json" % result["cycle_id"])
        )
        latest_path = runtime / "latest_status.json"
        return result, calls, kwargs, attempt_path, latest_path

    def test_dry_run_dispatches_nothing_and_writes_no_runtime_ledger(self):
        self.write_queue()
        calls = []

        def executor(action, parameters, project_root):
            calls.append((action, parameters, project_root))
            return {"status": "PASS"}

        result = run_cycle(
            self.root,
            self.queue_path,
            dry_run=True,
            executor=executor,
            inventory_provider=healthy_inventory,
            clock=lambda: "2026-07-30T20:00:00Z",
            process_id=101,
        )
        self.assertTrue(result["dry_run"])
        self.assertEqual(calls, [])
        self.assertFalse(
            (self.root / "live_data" / "runtime" / "autopilot").exists()
        )
        self.assertEqual(
            [item["state"] for item in result["task_results"]],
            ["DRY_RUN", "DRY_RUN"],
        )

    def test_one_cycle_dispatches_each_task_exactly_once_and_persists_canonical_status(self):
        self.write_queue()
        calls = []

        def executor(action, parameters, project_root):
            calls.append(action)
            return {"action": action, "status": "PASS"}

        result = run_cycle(
            self.root,
            self.queue_path,
            executor=executor,
            inventory_provider=healthy_inventory,
            clock=lambda: "2026-07-30T20:00:00Z",
            process_id=102,
        )
        self.assertEqual(calls, ["report_only", "verify_live"])
        self.assertEqual(result["overall_state"], "SCOPED_WORK_COMPLETE")
        self.assertEqual(
            [item["invocation_count"] for item in result["task_results"]],
            [1, 1],
        )

        runtime = self.root / "live_data" / "runtime" / "autopilot"
        attempt_path = runtime / "attempts" / ("%s.json" % result["cycle_id"])
        latest_path = runtime / "latest_status.json"
        attempt_bytes = attempt_path.read_bytes()
        latest_bytes = latest_path.read_bytes()
        self.assertEqual(
            attempt_bytes,
            canonical_bytes(json.loads(attempt_bytes.decode("utf-8"))),
        )
        self.assertEqual(
            latest_bytes,
            canonical_bytes(json.loads(latest_bytes.decode("utf-8"))),
        )
        latest = json.loads(latest_bytes.decode("utf-8"))
        self.assertEqual(latest["attempt_sha256"], sha256(attempt_bytes))
        self.assertEqual(latest["cycle_id"], result["cycle_id"])

    def test_same_cycle_identity_replays_existing_attempt_without_dispatch(self):
        first, calls, kwargs, _, _ = self.persisted_cycle()
        second = run_cycle(self.root, self.queue_path, **kwargs)
        self.assertEqual(calls, ["report_only", "verify_live"])
        self.assertEqual(second["cycle_id"], first["cycle_id"])
        self.assertTrue(second["replayed_existing_attempt"])

    def test_replay_rejects_forged_attempt_identity_and_task_contracts(self):
        first, calls, kwargs, attempt_path, _ = self.persisted_cycle(113)
        original = json.loads(attempt_path.read_text(encoding="utf-8"))

        mutations = {
            "extra attempt key": lambda value: value.update({"extra": True}),
            "missing queue id": lambda value: value.pop("queue_id"),
            "wrong schema": lambda value: value.update({
                "schema_version": "forged",
            }),
            "wrong cycle id": lambda value: value.update({
                "cycle_id": "f" * 64,
            }),
            "wrong queue id": lambda value: value.update({
                "queue_id": "forged-queue",
            }),
            "wrong queue hash": lambda value: value.update({
                "queue_sha256": "f" * 64,
            }),
            "wrong process": lambda value: value.update({"process_id": 999}),
            "wrong start": lambda value: value.update({
                "started_at": "2026-07-30T20:00:01Z",
            }),
            "missing task": lambda value: value["task_results"].pop(),
            "extra task key": lambda value: value["task_results"][0].update({
                "extra": True,
            }),
            "wrong task id": lambda value: value["task_results"][0].update({
                "task_id": "forged-task",
            }),
            "wrong action": lambda value: value["task_results"][0].update({
                "action": "verify_live",
            }),
            "wrong task state": lambda value: value["task_results"][0].update({
                "state": "FORGED",
            }),
            "wrong invocation count": lambda value: value[
                "task_results"
            ][0].update({"invocation_count": 2}),
        }
        for label, mutate in sorted(mutations.items()):
            value = copy.deepcopy(original)
            mutate(value)
            attempt_path.write_bytes(canonical_bytes(value))
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    QueueContractError,
                    "attempt|task result|queue|cycle|process",
                ):
                    run_cycle(self.root, self.queue_path, **kwargs)
        self.assertEqual(first["cycle_id"], original["cycle_id"])
        self.assertEqual(calls, ["report_only", "verify_live"])

    def test_latest_status_rejects_unsafe_tampered_and_cross_bound_records(self):
        _, _, _, attempt_path, latest_path = self.persisted_cycle(114)
        original_attempt = attempt_path.read_bytes()
        original_latest = json.loads(latest_path.read_text(encoding="utf-8"))

        mutations = {
            "extra status key": lambda value: value.update({"extra": True}),
            "missing queue id": lambda value: value.pop("queue_id"),
            "wrong schema": lambda value: value.update({
                "schema_version": "forged",
            }),
            "unsafe attempt path": lambda value: value.update({
                "attempt_path": "live_data/config/autopilot_queue.v1.json",
            }),
            "wrong attempt hash": lambda value: value.update({
                "attempt_sha256": "f" * 64,
            }),
            "wrong cycle": lambda value: value.update({
                "cycle_id": "f" * 64,
            }),
            "wrong queue": lambda value: value.update({
                "queue_id": "forged-queue",
            }),
            "wrong state": lambda value: value.update({
                "overall_state": "WORKING",
                "overall_state_reason": (
                    "Normal reservations, receipts, refreshes, or explicit "
                    "queue work remain."
                ),
            }),
            "wrong generation": lambda value: value.update({
                "active_generation_sha256": "f" * 64,
            }),
            "wrong task counts": lambda value: value.update({
                "task_state_counts": {"SUCCESS": 999},
            }),
            "wrong update time": lambda value: value.update({
                "updated_at": "2026-07-30T20:00:01Z",
            }),
        }
        for label, mutate in sorted(mutations.items()):
            attempt_path.write_bytes(original_attempt)
            value = copy.deepcopy(original_latest)
            mutate(value)
            latest_path.write_bytes(canonical_bytes(value))
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    QueueContractError,
                    "status|attempt|path|hash|queue|state|generation",
                ):
                    read_latest_status(self.root)

        attempt = json.loads(original_attempt.decode("utf-8"))
        attempt["extra"] = True
        forged_attempt = canonical_bytes(attempt)
        attempt_path.write_bytes(forged_attempt)
        latest = copy.deepcopy(original_latest)
        latest["attempt_sha256"] = sha256(forged_attempt)
        latest_path.write_bytes(canonical_bytes(latest))
        with self.assertRaisesRegex(QueueContractError, "attempt"):
            read_latest_status(self.root)

        for label, mutate_attempt in (
            (
                "queue/action forgery",
                lambda value: value["task_results"][0].update({
                    "action": "verify_live",
                }),
            ),
            (
                "empty task-result forgery",
                lambda value: value.update({"task_results": []}),
            ),
        ):
            attempt = json.loads(original_attempt.decode("utf-8"))
            mutate_attempt(attempt)
            forged_attempt = canonical_bytes(attempt)
            attempt_path.write_bytes(forged_attempt)
            latest = copy.deepcopy(original_latest)
            latest["attempt_sha256"] = sha256(forged_attempt)
            if not attempt["task_results"]:
                latest["task_state_counts"] = {}
            latest_path.write_bytes(canonical_bytes(latest))
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    QueueContractError,
                    "attempt|queue|task",
                ):
                    read_latest_status(self.root)

    def test_rejects_rehashed_operation_receipt_forgery(self):
        _, _, _, attempt_path, latest_path = self.persisted_cycle(115)
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        attempt["task_results"][0]["operation_receipt_sha256"] = "f" * 64
        forged_attempt = canonical_bytes(attempt)
        attempt_path.write_bytes(forged_attempt)
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        latest["attempt_sha256"] = sha256(forged_attempt)
        latest_path.write_bytes(canonical_bytes(latest))
        with self.assertRaisesRegex(QueueContractError, "receipt"):
            read_latest_status(self.root)

    def test_rejects_impossible_rehashed_timestamp(self):
        _, _, _, attempt_path, latest_path = self.persisted_cycle(116)
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        attempt["task_results"][0]["started_at"] = "2026-99-99T99:99:99Z"
        forged_attempt = canonical_bytes(attempt)
        attempt_path.write_bytes(forged_attempt)
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        latest["attempt_sha256"] = sha256(forged_attempt)
        latest_path.write_bytes(canonical_bytes(latest))
        with self.assertRaisesRegex(QueueContractError, "timestamp"):
            read_latest_status(self.root)

    def test_legacy_v1_status_is_explicitly_superseded(self):
        self.write_queue()
        runtime = self.root / "live_data" / "runtime" / "autopilot"
        runtime.mkdir(parents=True)
        (runtime / "latest_status.json").write_bytes(canonical_bytes({
            "schema_version": "recession-monitor-v2.data-autopilot-status.v1",
        }))
        status = read_latest_status(self.root)
        self.assertEqual(status["overall_state"], "NOT_RUN")
        self.assertEqual(
            status["superseded_status_schema"],
            "recession-monitor-v2.data-autopilot-status.v1",
        )

    def test_lock_contention_returns_without_dispatch_or_status_write(self):
        self.write_queue()
        runtime = self.root / "live_data" / "runtime" / "autopilot"
        runtime.mkdir(parents=True)
        lock_path = runtime / "cycle.lock"
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            calls = []
            result = run_cycle(
                self.root,
                self.queue_path,
                executor=lambda *args: calls.append(args),
                inventory_provider=healthy_inventory,
                clock=lambda: "2026-07-30T20:00:01Z",
                process_id=104,
            )
        self.assertEqual(result["overall_state"], "LOCKED_OUT")
        self.assertEqual(calls, [])
        self.assertFalse((runtime / "latest_status.json").exists())

    def test_execution_failure_is_not_retried_and_blocks_dependents(self):
        self.write_queue()
        calls = []

        def executor(action, parameters, project_root):
            calls.append(action)
            if action == "report_only":
                raise RuntimeError("one deliberate failure")
            return {"status": "PASS"}

        result = run_cycle(
            self.root,
            self.queue_path,
            executor=executor,
            inventory_provider=healthy_inventory,
            clock=lambda: "2026-07-30T20:00:02Z",
            process_id=105,
        )
        self.assertEqual(calls, ["report_only"])
        self.assertEqual(
            [item["state"] for item in result["task_results"]],
            ["FAILED", "BLOCKED_DEPENDENCY"],
        )
        self.assertEqual(result["task_results"][0]["invocation_count"], 1)
        self.assertRegex(
            result["task_results"][0]["operation_receipt_sha256"],
            r"^[0-9a-f]{64}$",
        )
        self.assertEqual(result["task_results"][1]["invocation_count"], 0)
        self.assertEqual(result["overall_state"], "DEGRADED")

    def test_stale_hash_fails_before_a_mutating_operation_is_dispatched(self):
        config_path = self.root / "live_data" / "config" / "sources.v1.json"
        config_path.write_bytes(b"current")
        draft_path = self.root / "live_data" / "draft.json"
        draft_path.write_bytes(b"draft")
        value = base_queue([
            task(
                "prepare",
                action="factory_prepare",
                parameters={"draft_path": "live_data/draft.json"},
                reviewed=True,
                artifact={
                    "path": "live_data/draft.json",
                    "sha256": sha256(b"draft"),
                },
                predecessors=[{
                    "path": "live_data/config/sources.v1.json",
                    "sha256": SHA256_ZERO,
                }],
            ),
        ], base_policy(
            ["factory_prepare"],
            allow_network=True,
            allow_mutation=True,
        ))
        self.write_queue(value)
        calls = []
        result = run_cycle(
            self.root,
            self.queue_path,
            executor=lambda *args: calls.append(args),
            inventory_provider=healthy_inventory,
            clock=lambda: "2026-07-30T20:00:03Z",
            process_id=106,
        )
        self.assertEqual(calls, [])
        self.assertEqual(result["task_results"][0]["state"], "PRECONDITION_FAILED")
        self.assertEqual(result["overall_state"], "DEGRADED")

    def test_missing_required_receipt_remains_working_and_does_not_dispatch(self):
        value = base_queue([
            task(
                "waiting",
                receipt={
                    "path": "live_data/runtime/receipts/waiting.json",
                    "sha256": SHA256_ZERO,
                },
            ),
        ])
        self.write_queue(value)
        calls = []
        result = run_cycle(
            self.root,
            self.queue_path,
            executor=lambda *args: calls.append(args),
            inventory_provider=healthy_inventory,
            clock=lambda: "2026-07-30T20:00:04Z",
            process_id=107,
        )
        self.assertEqual(calls, [])
        self.assertEqual(result["task_results"][0]["state"], "WAITING_FOR_RECEIPT")
        self.assertEqual(result["overall_state"], "WORKING")


class CompletionStateTests(AutopilotTestCase):
    def result(self, state="SUCCESS"):
        return [{
            "action": "report_only",
            "error": None,
            "error_type": None,
            "finished_at": "2026-07-30T20:00:00Z",
            "invocation_count": 1,
            "operation_receipt_sha256": "1" * 64,
            "started_at": "2026-07-30T20:00:00Z",
            "state": state,
            "task_id": "report",
        }]

    def test_normal_reservation_prevents_completion(self):
        inventory = healthy_inventory()
        inventory["reservations"]["counts"]["normal"] = 1
        inventory["reservations"]["counts"]["total"] = 1
        inventory["reservations"]["source_ids"]["normal"] = ["normal-source"]
        inventory["reservations"]["configured_counts"]["normal"] = 1
        inventory["reservations"]["configured_counts"]["total"] = 1
        inventory["reservations"]["configured_source_ids"]["normal"] = [
            "normal-source",
        ]
        inventory["completion_blockers"][
            "normal_actionable_reservations"
        ] = ["normal-source"]
        inventory["overall_state"] = "WORKING"
        inventory["overall_state_reason"] = "Normal work remains."
        self.assertEqual(
            derive_overall_state(base_queue(), self.result(), inventory),
            "WORKING",
        )

    def test_endpoint_identity_fulfilled_reservation_is_accepted(self):
        # Regression (Lane-0 autopilot DEGRADED loop): a planned reservation
        # fulfilled by ENDPOINT identity records the planned reservation id
        # (e.g. "tsa_throughput"), which is intentionally NOT the suffixed
        # enabled source id ("tsa_throughput_current"). The inventory contract
        # must accept this. Before the fix the validator asserted
        # fulfilled ⊆ enabled-source-ids and raised, so every fulfilled
        # reservation forced overall_state=DEGRADED forever.
        inventory = healthy_inventory()
        inventory["active_generation"]["source_ids"] = ["tsa_throughput_current"]
        inventory["active_generation"]["source_count"] = 1
        inventory["sources"]["enabled"] = {
            "count": 1,
            "source_ids": ["tsa_throughput_current"],
        }
        inventory["sources"]["healthy"] = {
            "count": 1,
            "source_ids": ["tsa_throughput_current"],
        }
        res = inventory["reservations"]
        res["configured_source_ids"]["normal"] = ["tsa_throughput"]
        res["configured_counts"]["normal"] = 1
        res["configured_counts"]["total"] = 1
        res["source_ids"]["normal"] = []
        res["counts"]["normal"] = 0
        res["counts"]["total"] = 0
        res["fulfilled"] = {"count": 1, "source_ids": ["tsa_throughput"]}
        # Must not raise: a fulfilled reservation is a configured reservation
        # id, not an enabled source id.
        self.assertEqual(_validate_inventory(inventory), inventory)

    def test_fulfilled_reservation_must_be_a_configured_reservation(self):
        # The corrected contract still rejects a fulfilled id that is not a
        # configured reservation at all (genuine inventory corruption).
        inventory = healthy_inventory()
        res = inventory["reservations"]
        res["configured_source_ids"]["normal"] = ["tsa_throughput"]
        res["configured_counts"]["normal"] = 1
        res["configured_counts"]["total"] = 1
        res["source_ids"]["normal"] = []
        res["counts"]["normal"] = 0
        res["counts"]["total"] = 0
        res["fulfilled"] = {"count": 1, "source_ids": ["not_a_reservation"]}
        with self.assertRaises(QueueContractError):
            _validate_inventory(inventory)

    def test_pending_candidate_is_ready_for_review(self):
        inventory = healthy_inventory()
        candidate = {
            "bundle_id": "bundle",
            "config_applied": False,
            "live": False,
            "manifest_path": "live_data/feed_factory/bundle/manifest.json",
            "predecessor_matches_active": True,
            "source_already_active": False,
            "source_id": "candidate-source",
            "state": "READY_FOR_REVIEW",
        }
        inventory["candidate_lifecycle"] = [candidate]
        inventory["pending_candidates"] = [candidate]
        inventory["completion_blockers"][
            "ready_for_review_candidates"
        ] = ["candidate-source"]
        inventory["overall_state"] = "READY_FOR_REVIEW"
        inventory["overall_state_reason"] = "A candidate is ready for review."
        self.assertEqual(
            derive_overall_state(base_queue(), self.result(), inventory),
            "READY_FOR_REVIEW",
        )

    def test_unhealthy_feed_is_degraded(self):
        inventory = healthy_inventory()
        inventory["sources"]["failed"] = {
            "count": 1,
            "source_ids": ["one"],
        }
        inventory["sources"]["healthy"] = {
            "count": 1,
            "source_ids": ["two"],
        }
        inventory["completion_blockers"]["failed_sources"] = ["one"]
        inventory["overall_state"] = "DEGRADED"
        inventory["overall_state_reason"] = "A source failed."
        inventory["status"] = "FAIL"
        self.assertEqual(
            derive_overall_state(base_queue(), self.result(), inventory),
            "DEGRADED",
        )

    def test_only_named_exceptions_remain_is_blocked_exceptions_only(self):
        inventory = healthy_inventory()
        inventory["reservations"]["counts"]["credential"] = 1
        inventory["reservations"]["counts"]["total"] = 1
        inventory["reservations"]["source_ids"]["credential"] = [
            "credential-source",
        ]
        inventory["reservations"]["configured_counts"]["credential"] = 1
        inventory["reservations"]["configured_counts"]["total"] = 1
        inventory["reservations"]["configured_source_ids"]["credential"] = [
            "credential-source",
        ]
        inventory["blocked_or_deferred"]["rights_blocked"] = {
            "count": 1,
            "source_ids": ["licensed"],
        }
        inventory["completion_blockers"]["credential_exceptions"] = [
            "credential-source",
        ]
        inventory["completion_blockers"]["rights_exceptions"] = ["licensed"]
        inventory["overall_state"] = "BLOCKED_EXCEPTIONS_ONLY"
        inventory["overall_state_reason"] = "Named exceptions remain."
        queue = base_queue([
            task(
                "credential-exception",
                enabled=False,
                exception_kind="credential_required",
            ),
        ])
        self.assertEqual(
            derive_overall_state(queue, self.result(), inventory),
            "BLOCKED_EXCEPTIONS_ONLY",
        )

    def test_empty_healthy_scope_can_be_scoped_work_complete(self):
        self.assertEqual(
            derive_overall_state(base_queue(), self.result(), healthy_inventory()),
            "SCOPED_WORK_COMPLETE",
        )

    def test_missing_or_schema_drifted_inventory_is_degraded(self):
        self.assertEqual(
            derive_overall_state(base_queue(), self.result(), {}),
            "DEGRADED",
        )
        mutations = {
            "extra top-level key": lambda value: value.update({
                "unexpected": True,
            }),
            "missing schema": lambda value: value.pop("schema_version"),
            "wrong errors type": lambda value: value.update({"errors": {}}),
            "reservation count mismatch": lambda value: value[
                "reservations"
            ]["counts"].update({"normal": 1}),
            "source count mismatch": lambda value: value[
                "sources"
            ]["healthy"].update({"count": 1}),
            "duplicate source id": lambda value: value[
                "sources"
            ]["healthy"]["source_ids"].append("one"),
        }
        for label, mutate in sorted(mutations.items()):
            inventory = healthy_inventory()
            mutate(inventory)
            with self.subTest(label=label):
                self.assertEqual(
                    derive_overall_state(
                        base_queue(),
                        self.result(),
                        inventory,
                    ),
                    "DEGRADED",
                )

    def test_mixed_generation_source_set_is_degraded(self):
        inventory = healthy_inventory()
        inventory["active_generation"]["source_count"] = 1
        inventory["active_generation"]["source_ids"] = ["alien"]
        self.assertEqual(
            derive_overall_state(base_queue(), self.result(), inventory),
            "DEGRADED",
        )


class CliExitContractTests(AutopilotTestCase):
    def test_cli_returns_nonzero_for_degraded_locked_out_and_not_run(self):
        self.assertIsNotNone(autopilot_cli)
        original_print = autopilot_cli._print
        original_read = autopilot_cli.read_latest_status
        original_cycle = autopilot_cli.run_cycle
        autopilot_cli._print = lambda value: None
        try:
            for state in ("DEGRADED", "NOT_RUN"):
                autopilot_cli.read_latest_status = (
                    lambda project_root, queue_path=None, state=state: {
                        "overall_state": state,
                    }
                )
                with self.subTest(command="status", state=state):
                    self.assertNotEqual(
                        autopilot_cli.main([
                            "--project-root",
                            str(self.root),
                            "status",
                        ]),
                        0,
                    )

            for state, dry_run in (
                ("DEGRADED", True),
                ("LOCKED_OUT", False),
            ):
                autopilot_cli.run_cycle = (
                    lambda *args, state=state, **kwargs: {
                        "overall_state": state,
                    }
                )
                arguments = [
                    "--project-root",
                    str(self.root),
                    "cycle",
                ]
                if dry_run:
                    arguments.append("--dry-run")
                with self.subTest(command="cycle", state=state):
                    self.assertNotEqual(
                        autopilot_cli.main(arguments),
                        0,
                    )

            autopilot_cli.read_latest_status = (
                lambda project_root, queue_path=None: {
                    "overall_state": "SCOPED_WORK_COMPLETE",
                }
            )
            self.assertEqual(
                autopilot_cli.main([
                    "--project-root",
                    str(self.root),
                    "status",
                ]),
                0,
            )
        finally:
            autopilot_cli._print = original_print
            autopilot_cli.read_latest_status = original_read
            autopilot_cli.run_cycle = original_cycle


class PublicationBarrierTests(AutopilotTestCase):
    """A live refresh in progress is a wait, never a repair finding."""

    def barrier_path(self):
        return self.root / "live_data" / "runtime" / "refresh.lock"

    def hold_barrier(self):
        descriptor = os.open(
            str(self.barrier_path()),
            os.O_RDWR | os.O_CREAT,
            0o644,
        )
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.addCleanup(os.close, descriptor)
        self.addCleanup(fcntl.flock, descriptor, fcntl.LOCK_UN)
        return descriptor

    def test_default_executor_defers_verify_while_a_refresh_holds_the_barrier(self):
        self.hold_barrier()
        with self.assertRaises(ServiceBusyError):
            DefaultExecutor()("verify_live", {}, self.root)

    def test_barrier_is_released_after_a_verify_so_the_service_is_never_starved(self):
        executor = DefaultExecutor()
        calls = []

        def fake_verify(project_root, arguments):
            calls.append(arguments)
            with self.assertRaises(BlockingIOError):
                descriptor = os.open(
                    str(self.barrier_path()),
                    os.O_RDWR | os.O_CREAT,
                    0o644,
                )
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                finally:
                    os.close(descriptor)
            return {"status": "PASS"}

        module = sys.modules[DefaultExecutor.__module__]
        original = module._subprocess_json
        module._subprocess_json = fake_verify
        try:
            self.assertEqual(
                executor("verify_live", {}, self.root),
                {"status": "PASS"},
            )
        finally:
            module._subprocess_json = original
        self.assertEqual(calls, [["verify"]])
        self.hold_barrier()

    def test_a_deferred_verify_reports_working_not_degraded(self):
        self.write_queue()
        states = []

        def executor(action, parameters, project_root):
            states.append(action)
            if action == "verify_live":
                raise ServiceBusyError(
                    "live-data refresh holds the publication barrier"
                )
            return {"status": "PASS"}

        result = run_cycle(
            self.root,
            self.queue_path,
            executor=executor,
            inventory_provider=healthy_inventory,
            clock=lambda: "2026-07-30T20:00:00Z",
            process_id=131,
        )
        self.assertEqual(states, ["report_only", "verify_live"])
        deferred = result["task_results"][1]
        self.assertEqual(deferred["state"], "DEFERRED_SERVICE_BUSY")
        self.assertEqual(deferred["invocation_count"], 0)
        self.assertIsNone(deferred["operation_receipt_sha256"])
        self.assertIsNone(deferred["output_summary"])
        self.assertEqual(deferred["error_type"], "ServiceBusyError")
        self.assertEqual(result["overall_state"], "WORKING")

    def test_a_persisted_deferred_cycle_replays_through_the_fail_closed_reader(self):
        self.write_queue()

        def executor(action, parameters, project_root):
            if action == "verify_live":
                raise ServiceBusyError(
                    "live-data refresh holds the publication barrier"
                )
            return {"status": "PASS"}

        result = run_cycle(
            self.root,
            self.queue_path,
            executor=executor,
            inventory_provider=healthy_inventory,
            clock=lambda: "2026-07-30T20:00:00Z",
            process_id=132,
        )
        status = read_latest_status(self.root)
        self.assertEqual(status["overall_state"], "WORKING")
        self.assertEqual(status["cycle_id"], result["cycle_id"])
        self.assertEqual(
            status["task_state_counts"],
            {"DEFERRED_SERVICE_BUSY": 1, "SUCCESS": 1},
        )


class ShippedArtifactContractTests(unittest.TestCase):
    def test_default_queue_is_report_and_verify_only(self):
        self.assertIsNotNone(
            load_queue,
            "live_data.rmv2_autopilot must exist before these tests can pass",
        )
        queue_path = (
            PROJECT_ROOT / "live_data" / "config" /
            "autopilot_queue.v1.json"
        )
        loaded = load_queue(PROJECT_ROOT, queue_path)
        policy = loaded.queue["policy"]
        self.assertFalse(policy["allow_network"])
        self.assertFalse(policy["allow_mutation"])
        self.assertEqual(
            policy["allowed_actions"],
            ["report_only", "verify_live"],
        )
        self.assertEqual(
            [item["action"] for item in loaded.queue["tasks"]],
            ["report_only", "verify_live"],
        )

    def test_launchd_runs_one_cycle_without_keepalive(self):
        plist_path = (
            PROJECT_ROOT / "live_data" / "launchd" /
            "com.anthonyhall.recession-monitor-v2.data-autopilot.plist"
        )
        self.assertTrue(
            plist_path.is_file(),
            "the one-shot data-autopilot launchd plist must exist",
        )
        with plist_path.open("rb") as handle:
            value = plistlib.load(handle)
        self.assertEqual(
            value["Label"],
            "com.anthonyhall.recession-monitor-v2.data-autopilot",
        )
        self.assertNotIn("KeepAlive", value)
        self.assertIsInstance(value["StartInterval"], int)
        self.assertGreaterEqual(value["StartInterval"], 300)
        args = value["ProgramArguments"]
        self.assertIn("live_data.rmv2_autopilot", args)
        self.assertEqual(args[-1], "cycle")

    def test_all_expected_operator_files_exist(self):
        paths = [
            "live_data/rmv2_autopilot/__init__.py",
            "live_data/rmv2_autopilot/__main__.py",
            "live_data/rmv2_autopilot/runner.py",
            "live_data/config/autopilot_queue.v1.json",
            "live_data/scripts/data_autopilot.command",
            "live_data/scripts/install_data_autopilot.sh",
            "live_data/scripts/uninstall_data_autopilot.sh",
            "live_data/AUTOPILOT.md",
        ]
        self.assertEqual(
            [path for path in paths if not (PROJECT_ROOT / path).is_file()],
            [],
        )


if __name__ == "__main__":
    unittest.main()
