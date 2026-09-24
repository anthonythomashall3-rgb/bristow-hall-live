"""Hermetic tests for the deterministic AI-free admission runner.

Every external effect is injected through a fake operations object, so these
tests never touch launchd, the network, or the real store. They pin the
admission cadence order, the <=5 batch cap, hard-stop-to-green recovery, the
never-bootout-while-barrier-held rule, the dedicated single-writer lock, the
append-only journal, and the fail-closed queue contract.
"""

from __future__ import absolute_import

import fcntl
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live_data.rmv2_live.canonical import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
)
from live_data.rmv2_admission import runner  # noqa: E402


def make_draft(source_id):
    return {
        "activation": {
            "scientific_effect": "none",
            "website_effect": "measurement_catalog_and_status_only",
        },
        "reservation": {"action": "none", "source_id": None},
        "schema_version": runner.DISCOVERY_SCHEMA,
        "source": {
            "adapter": "fred_json_api",
            "allowed_hosts": ["api.stlouisfed.org"],
            "coverage_source_ids": ["fred_current_provider"],
            "enabled": True,
            "endpoint": (
                "https://api.stlouisfed.org/fred/series/observations"
                "?series_id=X&file_type=json"
            ),
            "expected_content_types": ["application/json"],
            "frequency": "daily",
            "information_set_mode": "current_revised",
            "label": "test series",
            "max_bytes": 8000000,
            "method_version": "fred_json_api_current.v1",
            "poll_seconds": 3600,
            "publisher": "Federal Reserve Bank of St. Louis provider",
            "publisher_release_clock": "series-specific",
            "rights_status": "FRED_terms_and_underlying_publisher_rights_control",
            "secret_env": "FRED_API_KEY",
            "secret_required": True,
            "series": {"label": "X", "series_id": "X", "unit": "u"},
            "source_id": source_id,
            "value_status": "actual",
        },
    }


def write_project(root, source_ids, max_batch=5, mutate=None):
    """Write drafts + a canonical approved-draft queue; return the queue path."""
    root = Path(root)
    for sub in (
        "live_data/config",
        "live_data/feed_factory/drafts",
        "live_data/runtime",
        "live_data/public",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    entries = []
    for source_id in source_ids:
        draft = make_draft(source_id)
        if mutate:
            mutate(draft)
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


class FakeOps(object):
    """Injected operations that simulate a consistent store transition."""

    def __init__(
        self,
        source_map,
        baseline_live=(),
        baseline_head_count=0,
        barrier=True,
        fail_verify=False,
        fail_selfheal=False,
        key_scan_status="PASS",
    ):
        self.source_map = source_map            # draft_path -> source_id
        self.live = set(baseline_live)
        self.head_count = baseline_head_count
        self.barrier = barrier
        self.fail_verify = fail_verify
        self.fail_selfheal = fail_selfheal
        self.key_scan_status = key_scan_status
        self.calls = []
        self._tick = 0
        self.verify_count = 0

    def now(self):
        self._tick += 1
        return "2026-08-01T00:00:%02dZ" % (self._tick % 60)

    def barrier_free(self):
        self.calls.append(("barrier_free",))
        return self.barrier

    def read_state(self):
        self.calls.append(("read_state",))
        return {
            "service_state": "ready",
            "healthy_source_ids": frozenset(self.live),
            "head_count": self.head_count,
        }

    def stop_agents(self):
        self.calls.append(("stop_agents",))
        return [("bootout", label) for label in runner.AGENT_LABELS]

    def start_agents(self):
        self.calls.append(("start_agents",))
        return [("bootstrap", label) for label in runner.AGENT_LABELS]

    def publish_bundle(self):
        self.calls.append(("publish_bundle",))
        return {"generation_sha256": "a" * 64, "scientific_effect": "none"}

    def key_scan(self):
        self.calls.append(("key_scan",))
        return {"status": self.key_scan_status, "findings": [], "files_scanned": 3}

    def run_cli(self, arguments):
        self.calls.append(("run_cli", tuple(arguments)))
        head = arguments[0]
        if head == "feed-factory" and arguments[1] == "prepare":
            source_id = self.source_map[arguments[3]]
            return {
                "status": "CANDIDATE_NOT_ACTIVE",
                "manifest_path": (
                    "live_data/feed_factory/candidates/%s/manifest.json"
                    % source_id
                ),
            }
        if head == "feed-factory" and arguments[1] == "apply":
            manifest = arguments[3]
            source_id = manifest.split("/")[3]
            self.live.add(source_id)
            self.head_count += 1
            return {
                "status": "APPLIED_CONFIG_ONLY_REFRESH_REQUIRED",
                "source_id": source_id,
            }
        if head == "refresh" and "--source" in arguments:
            return {
                "outcomes": [{"source_id": arguments[-1], "outcome": "success"}],
                "snapshot_source_count": self.head_count,
            }
        if head == "refresh":  # full self-heal refresh
            return {
                "outcomes": [],
                "snapshot_source_count": self.head_count,
            }
        if head == "verify":
            self.verify_count += 1
            # First verify is the post-batch gate; a later verify is the
            # self-heal check driven independently by fail_selfheal.
            fail = self.fail_verify if self.verify_count == 1 \
                else self.fail_selfheal
            if fail:
                return {"status": "FAIL", "config_generation_closure": {}}
            return {
                "status": "PASS",
                "config_generation_closure": {"status": "PASS"},
                "checked_source_heads": ["s%d" % i for i in range(self.head_count)],
            }
        raise AssertionError("unexpected run_cli %r" % (arguments,))


def source_map_for(queue_path):
    import json
    queue = json.loads(Path(queue_path).read_text())
    return {e["draft_path"]: e["source_id"] for e in queue["drafts"]}


class AdmissionRunnerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _order(self, calls):
        return [c[0] if c[0] != "run_cli" else ("cli",) + c[1][:2] for c in calls]

    def test_full_batch_green_cadence_order(self):
        qp = write_project(self.root, ["fred_a_current", "fred_b_current"])
        ops = FakeOps(source_map_for(qp), baseline_head_count=74)
        result = runner.run_cycle(self.root, qp, ops=ops, process_id=101)
        self.assertEqual(result["terminal_state"], runner.STATE_ALL_ADMITTED)
        self.assertTrue(result["green"])
        self.assertEqual(result["verify_head_count"], 76)
        self.assertEqual(result["bundle_generation"], "a" * 64)
        # Cadence: barrier check happens before any bootout; agents stop before
        # the first prepare; verify/publish/key_scan follow the batch; agents
        # restart last.
        names = [c[0] for c in ops.calls]
        self.assertLess(names.index("barrier_free"), names.index("stop_agents"))
        first_prepare = next(
            i for i, c in enumerate(ops.calls)
            if c[0] == "run_cli" and c[1][1] == "prepare"
        )
        self.assertLess(names.index("stop_agents"), first_prepare)
        self.assertLess(names.index("publish_bundle"), names.index("key_scan"))
        self.assertLess(names.index("key_scan"), names.index("start_agents"))
        self.assertEqual(names[-1], "start_agents")
        # Per-draft order: prepare -> apply -> refresh --source, twice.
        cli = [c[1] for c in ops.calls if c[0] == "run_cli"]
        self.assertEqual(cli[0][1], "prepare")
        self.assertEqual(cli[1][1], "apply")
        self.assertEqual(cli[2][0], "refresh")
        self.assertEqual(cli[2][1], "--source")

    def test_batch_capped_at_five(self):
        ids = ["fred_%d_current" % i for i in range(7)]
        qp = write_project(self.root, ids, max_batch=5)
        ops = FakeOps(source_map_for(qp), baseline_head_count=10)
        result = runner.run_cycle(self.root, qp, ops=ops, process_id=1)
        self.assertEqual(
            result["terminal_state"], runner.STATE_BATCH_GREEN_MORE_PENDING
        )
        self.assertEqual(len(result["batch_source_ids"]), 5)
        applies = [
            c for c in ops.calls
            if c[0] == "run_cli" and c[1][1:2] == ("apply",)
        ]
        self.assertEqual(len(applies), 5)

    def test_resume_skips_already_live(self):
        qp = write_project(self.root, ["fred_a_current", "fred_b_current"])
        ops = FakeOps(
            source_map_for(qp),
            baseline_live=["fred_a_current"],
            baseline_head_count=75,
        )
        result = runner.run_cycle(self.root, qp, ops=ops, process_id=2)
        self.assertEqual(result["batch_source_ids"], ["fred_b_current"])
        self.assertEqual(result["terminal_state"], runner.STATE_ALL_ADMITTED)

    def test_noop_when_all_live(self):
        qp = write_project(self.root, ["fred_a_current"])
        ops = FakeOps(
            source_map_for(qp),
            baseline_live=["fred_a_current"],
            baseline_head_count=74,
        )
        result = runner.run_cycle(self.root, qp, ops=ops, process_id=3)
        self.assertEqual(
            result["terminal_state"], runner.STATE_NOOP_ALL_ADMITTED
        )
        self.assertNotIn("stop_agents", [c[0] for c in ops.calls])
        # A drained-queue tick is transient: it must not append a journal line.
        journal = (
            self.root / "live_data" / "runtime" / "admission" / "journal.jsonl"
        )
        self.assertFalse(journal.exists() and journal.read_bytes().strip())

    def test_barrier_held_defers_without_bootout(self):
        qp = write_project(self.root, ["fred_a_current"])
        ops = FakeOps(source_map_for(qp), baseline_head_count=74, barrier=False)
        result = runner.run_cycle(self.root, qp, ops=ops, process_id=4)
        self.assertEqual(
            result["terminal_state"], runner.STATE_DEFERRED_BARRIER_HELD
        )
        self.assertTrue(result["green"])
        names = [c[0] for c in ops.calls]
        self.assertIn("barrier_free", names)
        self.assertNotIn("stop_agents", names)
        self.assertNotIn("run_cli", names)

    def test_hard_stop_to_green_on_verify_failure(self):
        qp = write_project(self.root, ["fred_a_current", "fred_b_current"])
        ops = FakeOps(
            source_map_for(qp), baseline_head_count=74, fail_verify=True
        )
        result = runner.run_cycle(self.root, qp, ops=ops, process_id=5)
        self.assertEqual(result["terminal_state"], runner.STATE_HALTED_GREEN)
        self.assertTrue(result["green"])
        names = [c[0] for c in ops.calls]
        # No bundle/keyscan on the failure path, but agents still restart.
        self.assertNotIn("publish_bundle", names)
        self.assertNotIn("key_scan", names)
        self.assertEqual(names[-1], "start_agents")
        # A clean full refresh was issued to self-heal.
        self.assertTrue(any(
            c[0] == "run_cli" and c[1] == ("refresh",) for c in ops.calls
        ))

    def test_hard_stop_degraded_when_selfheal_fails(self):
        qp = write_project(self.root, ["fred_a_current"])
        ops = FakeOps(
            source_map_for(qp),
            baseline_head_count=74,
            fail_verify=True,
            fail_selfheal=True,
        )
        result = runner.run_cycle(self.root, qp, ops=ops, process_id=6)
        self.assertEqual(result["terminal_state"], runner.STATE_HALTED_DEGRADED)
        self.assertFalse(result["green"])
        self.assertEqual([c[0] for c in ops.calls][-1], "start_agents")

    def test_key_scan_failure_hard_stops(self):
        qp = write_project(self.root, ["fred_a_current"])
        ops = FakeOps(
            source_map_for(qp),
            baseline_head_count=74,
            key_scan_status="FAIL",
        )
        result = runner.run_cycle(self.root, qp, ops=ops, process_id=7)
        self.assertEqual(result["terminal_state"], runner.STATE_HALTED_GREEN)
        self.assertIn("key_scan", [c[0] for c in ops.calls])

    def test_dedicated_lock_excludes_second_cycle(self):
        qp = write_project(self.root, ["fred_a_current"])
        admission = self.root / "live_data" / "runtime" / "admission"
        admission.mkdir(parents=True, exist_ok=True)
        lock_path = admission / "runner.lock"
        held = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            ops = FakeOps(source_map_for(qp), baseline_head_count=74)
            result = runner.run_cycle(self.root, qp, ops=ops, process_id=8)
        finally:
            fcntl.flock(held, fcntl.LOCK_UN)
            os.close(held)
        self.assertEqual(result["terminal_state"], runner.STATE_LOCKED_OUT)
        self.assertEqual(ops.calls, [])
        # LOCKED_OUT is not persisted to the journal.
        journal = admission / "journal.jsonl"
        self.assertFalse(journal.exists() and journal.read_bytes())

    def test_journal_is_append_only(self):
        # max_batch=1 forces two separately persisted admission cycles.
        qp = write_project(
            self.root, ["fred_a_current", "fred_b_current"], max_batch=1
        )
        ops1 = FakeOps(source_map_for(qp), baseline_head_count=74)
        r1 = runner.run_cycle(self.root, qp, ops=ops1, process_id=9)
        self.assertEqual(
            r1["terminal_state"], runner.STATE_BATCH_GREEN_MORE_PENDING
        )
        ops2 = FakeOps(
            source_map_for(qp),
            baseline_live=["fred_a_current"],
            baseline_head_count=75,
        )
        r2 = runner.run_cycle(self.root, qp, ops=ops2, process_id=10)
        self.assertEqual(r2["terminal_state"], runner.STATE_ALL_ADMITTED)
        journal = (
            self.root / "live_data" / "runtime" / "admission" / "journal.jsonl"
        )
        lines = [ln for ln in journal.read_bytes().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)

    def test_latest_status_roundtrip(self):
        qp = write_project(self.root, ["fred_a_current"])
        ops = FakeOps(source_map_for(qp), baseline_head_count=74)
        runner.run_cycle(self.root, qp, ops=ops, process_id=11)
        latest = runner.read_latest_status(self.root)
        self.assertEqual(latest["schema_version"], runner.STATUS_SCHEMA)
        self.assertTrue(latest["green"])
        self.assertEqual(latest["terminal_state"], runner.STATE_ALL_ADMITTED)


class AdmissionQueueContractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _load(self, qp):
        return runner.load_queue(self.root, qp)

    def test_valid_queue_loads(self):
        qp = write_project(self.root, ["fred_a_current"])
        loaded = self._load(qp)
        self.assertEqual(loaded["max_batch"], 5)
        self.assertEqual(len(loaded["drafts"]), 1)

    def test_unreviewed_draft_rejected(self):
        qp = write_project(self.root, ["fred_a_current"])
        raw = qp.read_bytes().replace(b'"reviewed":true', b'"reviewed":false')
        qp.write_bytes(raw)
        with self.assertRaises(runner.AdmissionContractError):
            self._load(qp)

    def test_stale_sha_rejected(self):
        qp = write_project(self.root, ["fred_a_current"])
        draft = (
            self.root / "live_data" / "feed_factory" / "drafts"
            / "fred_a_current.v1.json"
        )
        draft.write_bytes(draft.read_bytes().replace(b'"daily"', b'"weekly"'))
        with self.assertRaises(runner.AdmissionContractError):
            self._load(qp)

    def test_scientific_binding_rejected(self):
        qp = write_project(self.root, ["fred_a_current"])
        qp.write_bytes(qp.read_bytes().replace(
            b'"scientific_binding":false', b'"scientific_binding":true'
        ))
        with self.assertRaises(runner.AdmissionContractError):
            self._load(qp)

    def test_batch_above_ceiling_rejected(self):
        qp = write_project(self.root, ["fred_a_current"], max_batch=5)
        qp.write_bytes(qp.read_bytes().replace(
            b'"max_batch":5', b'"max_batch":6'
        ))
        with self.assertRaises(runner.AdmissionContractError):
            self._load(qp)

    def test_embedded_secret_value_rejected(self):
        def add_secret(draft):
            draft["source"]["api_key"] = "abc123secret"
        qp = write_project(self.root, ["fred_a_current"], mutate=add_secret)
        with self.assertRaises(runner.AdmissionContractError):
            self._load(qp)


class KeylessLeakScanTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "live_data" / "public_deploy").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_clean_bundle_passes(self):
        bundle = self.root / "live_data" / "public_deploy" / "series.json"
        bundle.write_text('{"series":[{"id":"X","value":1}]}')
        result = runner.keyless_leak_scan(
            self.root, roots=[self.root / "live_data" / "public_deploy"]
        )
        self.assertEqual(result["status"], "PASS")

    def test_api_key_query_is_flagged(self):
        bundle = self.root / "live_data" / "public_deploy" / "leak.json"
        bundle.write_text('{"url":"https://x/obs?api_key=SECRETVAL&f=json"}')
        result = runner.keyless_leak_scan(
            self.root, roots=[self.root / "live_data" / "public_deploy"]
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["findings"]), 1)

    def test_local_env_is_never_scanned(self):
        env = self.root / "live_data" / "public_deploy" / "local.env"
        env.write_text("FRED_API_KEY=SECRETVAL\n")
        result = runner.keyless_leak_scan(
            self.root, roots=[self.root / "live_data" / "public_deploy"]
        )
        self.assertEqual(result["status"], "PASS")


class SecretScanWordBoundaryTests(unittest.TestCase):
    """The draft secret-scan must not false-positive on benign keys whose name
    merely contains a sensitive substring (e.g. ``missing_tokens``), while still
    rejecting keys that are or end with a real secret word."""

    def test_missing_tokens_is_not_a_secret(self):
        # 'missing_tokens' contains the substring 'token' but is a benign
        # missing-value token list; it must pass the scan.
        runner._scan_secret_values({"missing_tokens": ["", "NA"]}, "series")
        runner._scan_secret_values({"missing_tokens": []}, "series")
        runner._scan_secret_values(
            {"series": {"missing_tokens": ["", "NA"]}}, "source"
        )

    def test_real_secret_keys_still_rejected(self):
        for key in (
            "token", "api_token", "access_token", "auth_token",
            "api_key", "apikey", "password", "secret", "client_secret",
        ):
            with self.subTest(key=key):
                with self.assertRaises(runner.AdmissionContractError):
                    runner._scan_secret_values({key: "value"}, "src")

    def test_secret_env_name_still_allowed(self):
        runner._scan_secret_values(
            {"secret_env": "FRED_API_KEY", "secret_required": True}, "source"
        )


def _plist_bytes(label):
    import plistlib
    return plistlib.dumps({
        "Label": label,
        "ProgramArguments": ["/bin/true"],
    })


class AgentLabelRegistrationTests(unittest.TestCase):
    """The resident quiesce set must cover every deployed launchd plist, and
    must never include the on-demand admission runner. A hand-maintained writer
    list that silently drifts was the B1.3 root cause (a scheduled
    admission-runner not in AGENT_LABELS survived the batch bootout)."""

    def test_real_launchd_source_dir_matches_agent_labels(self):
        root = Path(__file__).resolve().parents[1]
        installed = runner.launchd_source_labels(root)
        self.assertTrue(installed, "no reviewed launchd plists found")
        self.assertEqual(installed, set(runner.AGENT_LABELS))
        # Assertion helper agrees and returns the covered set.
        self.assertEqual(
            runner.assert_agent_labels_cover_launchd_source(root), installed
        )

    def test_admission_runner_label_is_not_a_resident_agent(self):
        self.assertNotIn(
            "com.anthonyhall.recession-monitor-v2.admission-runner",
            runner.AGENT_LABELS,
        )

    def test_unregistered_launchd_plist_trips_assertion(self):
        with tempfile.TemporaryDirectory() as tmp:
            launchd = Path(tmp) / "live_data" / "launchd"
            launchd.mkdir(parents=True)
            (launchd / (runner.AGENT_LABELS[0] + ".plist")).write_bytes(
                _plist_bytes(runner.AGENT_LABELS[0])
            )
            (launchd / "com.example.rogue-writer.plist").write_bytes(
                _plist_bytes("com.example.rogue-writer")
            )
            with self.assertRaises(runner.AdmissionContractError):
                runner.assert_agent_labels_cover_launchd_source(Path(tmp))


if __name__ == "__main__":
    unittest.main()
