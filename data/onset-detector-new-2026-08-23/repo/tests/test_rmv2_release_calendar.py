"""B1.4-SCHED — release-calendar gating, idle-tick fast exit, incremental warm.

These pin the scheduler contract added in B1.4:
  * `_release_boundary` rolls a derived next-expected release forward/backward so
    "has this release happened yet" tracks wall time without regenerating the file.
  * `_is_due` polls a calendared source only once its release boundary passes, and
    still fast-retries a failed poll; an "unknown" source falls back to the exact
    pre-existing poll_seconds gate (no behaviour change when the calendar is absent).
  * `refresh(due_only=True)` on a tick where NOTHING is due does no store-closure
    work and leaves the active generation pointer byte-for-byte untouched.
  * the service pointer read used to gate the incremental warm is O(1).
"""
from __future__ import absolute_import

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import HttpResponse
from live_data.rmv2_live.cli import _read_pointer_bytes
from live_data.rmv2_live.pipeline import (
    RefreshPipeline,
    _release_boundary,
    load_release_calendar,
)
from live_data.rmv2_live.canonical import atomic_write_json


T1 = "2026-07-29T12:00:00Z"
T2 = "2026-07-29T12:01:00Z"  # +60s: inside the default 300s poll window


def _dt(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _source(source_id, endpoint, poll_seconds=300):
    return {
        "adapter": "raw_capture",
        "allowed_hosts": ["publisher.example"],
        "coverage_source_ids": ["synthetic_publisher"],
        "enabled": True,
        "endpoint": endpoint,
        "expected_content_types": ["application/octet-stream"],
        "frequency": "weekly",
        "information_set_mode": "current_revised",
        "label": "Synthetic publisher payload",
        "max_bytes": 100000,
        "method_version": "synthetic-v1",
        "poll_seconds": poll_seconds,
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


class ReleaseBoundaryTests(unittest.TestCase):
    ENTRY = {
        "next_expected_release_utc": "2026-08-05T13:30:00Z",  # a Wednesday
        "cadence_gap_days": 7,
    }

    def test_now_before_next_returns_previous_boundary(self):
        b = _release_boundary(self.ENTRY, _dt("2026-08-05T12:00:00Z"))
        self.assertEqual(b, _dt("2026-07-29T13:30:00Z"))

    def test_now_after_next_returns_that_boundary(self):
        b = _release_boundary(self.ENTRY, _dt("2026-08-05T14:00:00Z"))
        self.assertEqual(b, _dt("2026-08-05T13:30:00Z"))

    def test_rolls_forward_weeks_later(self):
        b = _release_boundary(self.ENTRY, _dt("2026-08-20T00:00:00Z"))
        self.assertEqual(b, _dt("2026-08-19T13:30:00Z"))

    def test_unknown_entry_yields_none(self):
        self.assertIsNone(_release_boundary({"next_expected_release_utc": None}, _dt(T1)))
        self.assertIsNone(_release_boundary(
            {"next_expected_release_utc": "2026-08-05T13:30:00Z", "cadence_gap_days": None},
            _dt(T1),
        ))


class LoadReleaseCalendarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "live_data" / "config").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, doc):
        atomic_write_json(self.root / "live_data" / "config" / "release_calendar.v1.json", doc)

    def test_absent_file_is_empty(self):
        self.assertEqual(load_release_calendar(self.root), {})

    def test_wrong_schema_is_empty(self):
        self._write({"schema_version": "something-else", "sources": {"x": {}}})
        self.assertEqual(load_release_calendar(self.root), {})

    def test_valid_returns_sources(self):
        self._write({
            "schema_version": "recession-monitor-v2.release-calendar.v1",
            "sources": {"synthetic_live_a": {"confidence": "high"}},
        })
        got = load_release_calendar(self.root)
        self.assertIn("synthetic_live_a", got)


class IsDueCalendarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        _write_registry(self.root)
        self.config = _config()
        self.pipe = RefreshPipeline(self.root, self.config, ScriptedHttpClient({}), clock=lambda: T1)
        self.source = self.config["sources"][0]

    def tearDown(self):
        self.temp.cleanup()

    def _status(self, attempted, outcome="unchanged"):
        return {"attempted_at": attempted, "outcome": outcome, "source_id": self.source["source_id"]}

    def test_no_prior_attempt_is_due(self):
        self.assertTrue(self.pipe._is_due(self.source, None, _dt(T1)))

    def test_calendared_not_due_before_boundary(self):
        # boundary rolls to 2026-07-29T13:30; now is just before it, last poll earlier
        self.pipe.release_calendar = {self.source["source_id"]: {
            "next_expected_release_utc": "2026-07-29T13:30:00Z", "cadence_gap_days": 7}}
        now = _dt("2026-07-29T13:00:00Z")
        status = self._status("2026-07-29T12:00:00Z")
        self.assertFalse(self.pipe._is_due(self.source, status, now))

    def test_calendared_due_after_boundary_when_not_yet_polled(self):
        self.pipe.release_calendar = {self.source["source_id"]: {
            "next_expected_release_utc": "2026-07-29T13:30:00Z", "cadence_gap_days": 7}}
        now = _dt("2026-07-29T14:00:00Z")
        status = self._status("2026-07-29T12:00:00Z")  # polled BEFORE the boundary
        self.assertTrue(self.pipe._is_due(self.source, status, now))

    def test_calendared_not_due_after_polling_for_release(self):
        self.pipe.release_calendar = {self.source["source_id"]: {
            "next_expected_release_utc": "2026-07-29T13:30:00Z", "cadence_gap_days": 7}}
        now = _dt("2026-07-29T14:00:00Z")
        status = self._status("2026-07-29T13:45:00Z")  # already polled AFTER the boundary
        self.assertFalse(self.pipe._is_due(self.source, status, now))

    def test_failed_poll_fast_retries_regardless_of_calendar(self):
        self.pipe.release_calendar = {self.source["source_id"]: {
            "next_expected_release_utc": "2026-08-30T13:30:00Z", "cadence_gap_days": 7}}
        now = _dt("2026-07-29T12:10:00Z")
        status = self._status("2026-07-29T12:00:00Z", outcome="failed")  # 600s ago > 300
        self.assertTrue(self.pipe._is_due(self.source, status, now))

    def test_unknown_calendar_entry_falls_back_to_poll_seconds(self):
        self.pipe.release_calendar = {self.source["source_id"]: {
            "next_expected_release_utc": None}}
        # 60s after last poll < poll_seconds 300 -> not due (pure fallback)
        self.assertFalse(self.pipe._is_due(self.source, self._status(T1), _dt(T2)))
        # 400s after -> due
        self.assertTrue(self.pipe._is_due(
            self.source, self._status(T1), _dt("2026-07-29T12:06:40Z")))

    def test_no_calendar_matches_legacy_poll_seconds(self):
        self.pipe.release_calendar = {}
        self.assertFalse(self.pipe._is_due(self.source, self._status(T1), _dt(T2)))


class IdleTickFastExitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        _write_registry(self.root)
        self.config = _config()

    def tearDown(self):
        self.temp.cleanup()

    def _pipeline(self, client, ts):
        return RefreshPipeline(self.root, self.config, client, clock=lambda: ts)

    def test_idle_tick_does_no_store_work_and_leaves_pointer_untouched(self):
        client = ScriptedHttpClient({
            "synthetic_live_a": _response("https://publisher.example/a.bin", b"A-v1", '"a1"'),
            "synthetic_live_b": _response("https://publisher.example/b.bin", b"B-v1", '"b1"'),
        })
        self._pipeline(client, T1).refresh()  # first publish
        public = self.root / "public"
        pointer_before = _read_pointer_bytes(public)
        gens_before = sorted((self.root / "store" / "generations").iterdir())

        # T2 is 60s later; poll_seconds is 300 and there is no calendar, so nothing
        # is due. Nothing is acquired, so no generation is published and the
        # active pointer is left byte-for-byte untouched (the scheduler's pointer-
        # gated warm therefore does no O(store) re-verification on this tick).
        result = self._pipeline(client, T2).refresh(due_only=True)

        self.assertIsNone(result["pointer"])
        self.assertTrue(all(
            o["outcome"] in ("not_due", "disabled") for o in result["outcomes"]))
        # No new generation, pointer byte-identical.
        self.assertEqual(_read_pointer_bytes(public), pointer_before)
        self.assertEqual(sorted((self.root / "store" / "generations").iterdir()), gens_before)

    def test_due_tick_still_refreshes_and_can_publish(self):
        client = ScriptedHttpClient({
            "synthetic_live_a": _response("https://publisher.example/a.bin", b"A-v1", '"a1"'),
            "synthetic_live_b": _response("https://publisher.example/b.bin", b"B-v1", '"b1"'),
        })
        self._pipeline(client, T1).refresh()
        public = self.root / "public"
        pointer_before = _read_pointer_bytes(public)

        # 400s later, source A changes; due_only should poll and publish.
        changed = ScriptedHttpClient({
            "synthetic_live_a": _response("https://publisher.example/a.bin", b"A-v2", '"a2"'),
            "synthetic_live_b": _response("https://publisher.example/b.bin", b"B-v1", '"b1"'),
        })
        later = "2026-07-29T12:06:40Z"
        result = self._pipeline(changed, later).refresh(due_only=True)
        self.assertFalse(result.get("idle"))
        self.assertIsNotNone(result["pointer"])
        self.assertNotEqual(_read_pointer_bytes(public), pointer_before)


class PointerReadTests(unittest.TestCase):
    def test_read_pointer_bytes_absent_then_present(self):
        with tempfile.TemporaryDirectory() as d:
            public = Path(d)
            self.assertIsNone(_read_pointer_bytes(public))
            (public / "latest.pointer.json").write_bytes(b'{"generation_sha256":"x"}')
            self.assertEqual(_read_pointer_bytes(public), b'{"generation_sha256":"x"}')
            (public / "latest.pointer.json").write_bytes(b'{"generation_sha256":"y"}')
            self.assertNotEqual(_read_pointer_bytes(public), b'{"generation_sha256":"x"}')


if __name__ == "__main__":
    unittest.main()
