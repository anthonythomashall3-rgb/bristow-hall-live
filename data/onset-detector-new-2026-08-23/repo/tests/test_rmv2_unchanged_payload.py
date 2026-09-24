from __future__ import absolute_import

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import HttpResponse
from live_data.rmv2_live.canonical import read_json
from live_data.rmv2_live.pipeline import RefreshPipeline


FIRST_ATTEMPT = "2026-07-29T12:00:00Z"
SECOND_ATTEMPT = "2026-07-29T12:06:00Z"
BODY_A = b"publisher payload generation A"
BODY_B = b"publisher payload generation B"


def source_config():
    return {
        "adapter": "raw_capture",
        "allowed_hosts": ["publisher.example"],
        "coverage_source_ids": ["synthetic_publisher"],
        "enabled": True,
        "endpoint": "https://publisher.example/data.bin",
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
        "source_id": "synthetic_live",
        "value_status": "actual",
    }


def config_value():
    return {
        "api": {
            "host": "127.0.0.1",
            "port": 8792,
            "website_poll_seconds": 60,
        },
        "catalog_registry": "registry.csv",
        "schema_version": "recession-monitor-v2.live-data-config.v1",
        "service": {"refresh_tick_seconds": 60},
        "sources": [source_config()],
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
        "synthetic_publisher,A,current,daily,"
        "https://publisher.example,Synthetic publisher,public,daily\n",
        encoding="utf-8",
    )


def response(
    body,
    status=200,
    etag='"generation-a"',
    last_modified="Wed, 29 Jul 2026 12:00:00 GMT",
):
    headers = {
        "etag": etag,
        "last-modified": last_modified,
    }
    if status != 304:
        headers["content-type"] = "application/octet-stream"
    return HttpResponse(
        "https://publisher.example/data.bin",
        status,
        headers,
        body,
    )


class ScriptedHttpClient(object):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def fetch(self, source, now=None, conditional_headers=None):
        conditional_headers = dict(conditional_headers or {})
        self.calls.append({
            "conditional_headers": conditional_headers,
            "now": now.isoformat() if now is not None else None,
            "source_id": source["source_id"],
        })
        if not self.responses:
            raise AssertionError("unexpected publisher fetch")
        result = self.responses.pop(0)
        result.request_headers = conditional_headers
        return result


class UnchangedPayloadContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_registry(self.root)
        self.config = config_value()

    def tearDown(self):
        self.temp.cleanup()

    def _pipeline(self, client, timestamp):
        return RefreshPipeline(
            self.root,
            self.config,
            client,
            clock=lambda: timestamp,
        )

    def _receipts(self):
        root = self.root / "store" / "receipts" / "synthetic_live"
        return sorted(root.glob("*.json")) if root.exists() else []

    def _attempts(self):
        root = self.root / "store" / "attempts" / "synthetic_live"
        return sorted(root.glob("*.json")) if root.exists() else []

    def _generations(self):
        root = self.root / "store" / "generations"
        return sorted(path for path in root.iterdir() if path.is_dir())

    def _first_refresh(self, client):
        first = self._pipeline(client, FIRST_ATTEMPT).refresh()
        self.assertEqual(first["outcomes"][0]["outcome"], "success")
        self.assertIsNotNone(first["pointer"])
        return {
            "generation_count": len(self._generations()),
            "head": read_json(
                self.root / "runtime" / "source_heads" / "synthetic_live.json"
            ),
            "pointer": read_json(self.root / "public" / "latest.pointer.json"),
            "snapshot_bytes": (
                self.root / "public" / "live_snapshot.json"
            ).read_bytes(),
        }

    def _assert_unchanged_refresh(self, client, before):
        second = self._pipeline(client, SECOND_ATTEMPT).refresh()
        self.assertEqual(second["outcomes"][0]["outcome"], "unchanged")
        self.assertIsNone(second["pointer"])
        self.assertEqual(
            read_json(
                self.root / "runtime" / "source_heads" / "synthetic_live.json"
            ),
            before["head"],
        )
        self.assertEqual(
            read_json(self.root / "public" / "latest.pointer.json"),
            before["pointer"],
        )
        self.assertEqual(len(self._generations()), before["generation_count"])
        self.assertEqual(
            (self.root / "public" / "live_snapshot.json").read_bytes(),
            before["snapshot_bytes"],
        )
        operational = read_json(
            self.root / "public" / "operational_status.json"
        )
        self.assertFalse(operational["generation_advanced"])
        self.assertEqual(
            operational["active_generation_sha256"],
            before["pointer"]["generation_sha256"],
        )
        status = read_json(
            self.root / "runtime" / "source_status" / "synthetic_live.json"
        )
        self.assertEqual(status["outcome"], "unchanged")
        self.assertEqual(status["attempted_at"], SECOND_ATTEMPT)
        self.assertEqual(status["last_success_at"], FIRST_ATTEMPT)
        return second

    def test_identical_200_at_new_retrieval_time_records_poll_without_new_evidence_head(self):
        client = ScriptedHttpClient([
            response(BODY_A),
            response(BODY_A),
        ])
        before = self._first_refresh(client)
        self._assert_unchanged_refresh(client, before)

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["conditional_headers"], {})
        self.assertEqual(
            client.calls[1]["conditional_headers"],
            {
                "If-Modified-Since": "Wed, 29 Jul 2026 12:00:00 GMT",
                "If-None-Match": '"generation-a"',
            },
        )
        self.assertEqual(len(self._receipts()), 1)
        self.assertEqual(len(self._attempts()), 1)
        unchanged_attempt = read_json(self._attempts()[0])
        self.assertEqual(unchanged_attempt["outcome"], "unchanged")
        self.assertEqual(unchanged_attempt["attempted_at"], SECOND_ATTEMPT)
        self.assertEqual(
            unchanged_attempt["source_bytes_sha256"],
            before["head"]["source_bytes_sha256"],
        )
        self.assertEqual(
            len(self._receipts()) + len(self._attempts()),
            2,
            "both polls must remain observable without duplicating evidence",
        )

    def test_http_304_is_typed_unchanged_and_does_not_advance_generation(self):
        client = ScriptedHttpClient([
            response(BODY_A, etag='"generation-a"'),
            response(
                b"",
                status=304,
                etag='"generation-a"',
                last_modified="Wed, 29 Jul 2026 12:00:00 GMT",
            ),
        ])
        before = self._first_refresh(client)
        self._assert_unchanged_refresh(client, before)

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(
            client.calls[1]["conditional_headers"]["If-None-Match"],
            '"generation-a"',
        )
        self.assertEqual(len(self._receipts()), 1)
        self.assertEqual(len(self._attempts()), 1)
        unchanged_attempt = read_json(self._attempts()[0])
        self.assertEqual(unchanged_attempt["outcome"], "unchanged")
        self.assertEqual(unchanged_attempt["response"]["status"], 304)

    def test_http_304_without_prior_head_is_typed_failed_and_creates_no_generation(self):
        client = ScriptedHttpClient([
            response(
                b"",
                status=304,
                etag='"generation-a"',
                last_modified="Wed, 29 Jul 2026 12:00:00 GMT",
            ),
        ])
        result = self._pipeline(client, FIRST_ATTEMPT).refresh()
        self.assertEqual(result["outcomes"][0]["outcome"], "failed")
        self.assertIsNone(result["pointer"])
        self.assertEqual(self._receipts(), [])
        self.assertEqual(len(self._attempts()), 1)
        self.assertFalse(
            (self.root / "runtime" / "source_heads" / "synthetic_live.json").exists()
        )
        attempt = read_json(self._attempts()[0])
        self.assertEqual(attempt["failure_stage"], "request")
        self.assertEqual(attempt["error_type"], "SourceUnavailable")

    def test_header_change_with_identical_body_does_not_advance_scientific_generation(self):
        client = ScriptedHttpClient([
            response(
                BODY_A,
                etag='"generation-a"',
                last_modified="Wed, 29 Jul 2026 12:00:00 GMT",
            ),
            response(
                BODY_A,
                etag='"publisher-rekeyed-etag"',
                last_modified="Wed, 29 Jul 2026 12:05:00 GMT",
            ),
        ])
        before = self._first_refresh(client)
        self._assert_unchanged_refresh(client, before)

        unchanged_attempt = read_json(self._attempts()[0])
        self.assertEqual(
            unchanged_attempt["response"]["etag"],
            '"publisher-rekeyed-etag"',
        )
        self.assertEqual(
            unchanged_attempt["response"]["last_modified"],
            "Wed, 29 Jul 2026 12:05:00 GMT",
        )
        self.assertEqual(len(self._receipts()), 1)

    def test_changed_body_advances_evidence_head_and_public_generation(self):
        client = ScriptedHttpClient([
            response(BODY_A, etag='"generation-a"'),
            response(
                BODY_B,
                etag='"generation-b"',
                last_modified="Wed, 29 Jul 2026 12:06:00 GMT",
            ),
        ])
        before = self._first_refresh(client)
        second = self._pipeline(client, SECOND_ATTEMPT).refresh()

        self.assertEqual(second["outcomes"][0]["outcome"], "success")
        self.assertIsNotNone(second["pointer"])
        after_head = read_json(
            self.root / "runtime" / "source_heads" / "synthetic_live.json"
        )
        after_pointer = read_json(
            self.root / "public" / "latest.pointer.json"
        )
        self.assertNotEqual(
            after_head["source_bytes_sha256"],
            before["head"]["source_bytes_sha256"],
        )
        self.assertNotEqual(
            after_head["receipt_sha256"],
            before["head"]["receipt_sha256"],
        )
        self.assertNotEqual(
            after_pointer["generation_sha256"],
            before["pointer"]["generation_sha256"],
        )
        self.assertEqual(len(self._generations()), 2)
        self.assertEqual(len(self._receipts()), 2)
        self.assertEqual(len(self._attempts()), 0)
        operational = read_json(
            self.root / "public" / "operational_status.json"
        )
        self.assertTrue(operational["generation_advanced"])

    def test_parser_method_change_reprocesses_identical_publisher_bytes(self):
        client = ScriptedHttpClient([
            response(BODY_A),
            response(BODY_A),
        ])
        before = self._first_refresh(client)
        self.config["sources"][0]["method_version"] = "synthetic-v2"

        second = self._pipeline(client, SECOND_ATTEMPT).refresh()

        self.assertEqual(second["outcomes"][0]["outcome"], "success")
        self.assertIsNotNone(second["pointer"])
        after_head = read_json(
            self.root / "runtime" / "source_heads" / "synthetic_live.json"
        )
        self.assertEqual(
            after_head["source_bytes_sha256"],
            before["head"]["source_bytes_sha256"],
        )
        self.assertNotEqual(
            after_head["normalized_sha256"],
            before["head"]["normalized_sha256"],
        )
        self.assertEqual(after_head["method_version"], "synthetic-v2")
        self.assertNotEqual(
            second["pointer"]["generation_sha256"],
            before["pointer"]["generation_sha256"],
        )

    def test_source_matrix_definition_change_rebinds_generation_without_new_source_evidence(self):
        client = ScriptedHttpClient([
            response(BODY_A),
            response(BODY_A),
        ])
        before = self._first_refresh(client)
        with (self.root / "registry.csv").open("a", encoding="utf-8") as handle:
            handle.write(
                "new_official_family,A,current,monthly,"
                "https://publisher.example/new,Synthetic publisher,public,monthly\n"
            )

        second = self._pipeline(client, SECOND_ATTEMPT).refresh()

        self.assertEqual(second["outcomes"][0]["outcome"], "unchanged")
        self.assertIsNotNone(second["pointer"])
        self.assertEqual(len(self._receipts()), 1)
        self.assertEqual(len(self._attempts()), 1)
        self.assertEqual(
            read_json(
                self.root / "runtime" / "source_heads" / "synthetic_live.json"
            ),
            before["head"],
        )
        after_pointer = read_json(
            self.root / "public" / "latest.pointer.json"
        )
        self.assertNotEqual(
            after_pointer["generation_sha256"],
            before["pointer"]["generation_sha256"],
        )
        status = read_json(self.root / "public" / "live_status.json")
        self.assertFalse(status["scientific_outputs_updated"])
        self.assertEqual(status["source_matrix"]["row_count"], 3)
        self.assertRegex(
            status["source_matrix"]["definition_sha256"],
            r"^[0-9a-f]{64}$",
        )


if __name__ == "__main__":
    unittest.main()
