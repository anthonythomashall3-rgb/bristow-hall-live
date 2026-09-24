from __future__ import absolute_import

import ast
import copy
import hashlib
import http.client
import json
import os
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import (
    HttpResponse,
    SourceBlocked,
    SourceUnavailable,
)
from live_data.rmv2_live.canonical import (
    CanonicalDataError,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    strict_json_loads,
)
from live_data.rmv2_live.config import load_config, load_env_file
from live_data.rmv2_live.pipeline import RefreshPipeline
from live_data.rmv2_live.server import LiveDataApiHandler, create_server
from live_data.rmv2_live.store import (
    LiveStore,
    read_verified_generation,
    safe_regular_file,
)


FIXED_TIME_1 = "2026-07-29T12:00:00Z"
FIXED_TIME_2 = "2026-07-29T12:06:00Z"
FIXED_TIME_3 = "2026-07-29T12:07:00Z"


def source_config(source_id="nyfed_test", adapter="nyfed_reference_rate_json"):
    return {
        "adapter": adapter,
        "allowed_hosts": ["markets.newyorkfed.org"],
        "coverage_source_ids": ["nyfed_reference_rates"],
        "enabled": True,
        "endpoint": "https://markets.newyorkfed.org/example.json",
        "expected_content_types": ["application/json"],
        "frequency": "daily_business_day",
        "information_set_mode": "current_revised",
        "label": "Test source",
        "max_bytes": 100000,
        "method_version": "test-v1",
        "poll_seconds": 300,
        "publisher": "Test publisher",
        "publisher_release_clock": "publisher clock",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {},
        "source_id": source_id,
        "value_status": "actual",
    }


def fred_source_config(series_id="CPFF"):
    source = source_config(
        "fred_%s_current" % series_id.lower(),
        "fred_graph_csv",
    )
    source.update({
        "allowed_hosts": ["fred.stlouisfed.org"],
        "coverage_source_ids": ["fred_current_provider"],
        "endpoint": (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s" %
            series_id
        ),
        "expected_content_types": [
            "application/csv",
            "text/csv",
        ],
        "method_version": "fred_graph_current_csv.v1",
        "publisher": "Federal Reserve Bank of St. Louis",
        "publisher_release_clock": (
            "provider availability is series-specific; exact underlying "
            "publisher release time remains null"
        ),
        "rights_status": (
            "FRED_terms_and_underlying_publisher_rights_control"
        ),
        "series": {
            "label": "Test FRED series",
            "series_id": series_id,
            "unit": "percentage points",
        },
    })
    return source


def config_value(sources=None, port=8792):
    return {
        "api": {
            "host": "127.0.0.1",
            "port": port,
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


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def write_registry(root, access_class="A"):
    text = (
        "source_id,access_class,coverage,frequency,primary_url,publisher,"
        "rights_status,typical_release_or_availability\n"
        "nyfed_reference_rates,%s,current,current,"
        "https://markets.newyorkfed.org,New York Fed,public,daily\n"
        "licensed_source,C,licensed,monthly,https://example.test,"
        "Licensed publisher,licensed,monthly\n"
        "target_source,D,target,monthly,https://example.test,"
        "Target publisher,not_input,monthly\n"
    ) % access_class
    (Path(root) / "registry.csv").write_text(text, encoding="utf-8")


def nyfed_body(rate="3.65"):
    return canonical_json_bytes({
        "refRates": [{
            "effectiveDate": "2026-07-28",
            "percentRate": rate,
            "revisionIndicator": "",
            "type": "SOFR",
            "volumeInBillions": "2100",
        }],
    })


class FakeHttpClient(object):
    def __init__(self, bodies=None, error=None):
        self.bodies = dict(bodies or {})
        self.error = error
        self.calls = []

    def fetch(self, source, now=None, conditional_headers=None):
        self.calls.append(source["source_id"])
        if self.error is not None:
            raise self.error
        body = self.bodies.get(source["source_id"], nyfed_body())
        return HttpResponse(
            source["endpoint"],
            200,
            {"content-type": "application/json", "etag": '"test"'},
            body,
            request_headers=conditional_headers,
        )


class CanonicalAndConfigTests(unittest.TestCase):
    def test_canonical_json_is_deterministic_utf8_and_hashes_exact_bytes(self):
        left = {"z": ["é", 2], "a": {"b": True}}
        right = {"a": {"b": True}, "z": ["é", 2]}
        expected = '{"a":{"b":true},"z":["é",2]}'.encode("utf-8")
        self.assertEqual(canonical_json_bytes(left), expected)
        self.assertEqual(canonical_json_bytes(right), expected)
        self.assertEqual(sha256_bytes(expected), hashlib.sha256(expected).hexdigest())

    def test_strict_json_rejects_duplicates_nonfinite_floats_and_bad_utf8(self):
        invalid_values = (
            b'{"x":1,"x":2}',
            b'{"x":NaN}',
            b'{"x":Infinity}',
            b'{"x":1.25}',
            b'{"x":"\xff"}',
        )
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises((CanonicalDataError, UnicodeDecodeError)):
                    strict_json_loads(value)
        with self.assertRaises(CanonicalDataError):
            canonical_json_bytes({"x": 1.25})
        with self.assertRaises(CanonicalDataError):
            canonical_json_bytes({1: "not a JSON string key"})

    def test_config_accepts_exact_loopback_https_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            write_json(path, config_value())
            loaded = load_config(path)
            self.assertEqual(loaded["api"]["host"], "127.0.0.1")
            self.assertEqual(loaded["sources"][0]["source_id"], "nyfed_test")
            write_json(path, config_value([fred_source_config()]))
            loaded = load_config(path)
            self.assertEqual(
                loaded["sources"][0]["adapter"],
                "fred_graph_csv",
            )

    def test_config_rejects_duplicate_ids_extra_keys_and_unsafe_endpoints(self):
        mutations = []
        duplicate = config_value([source_config(), source_config()])
        mutations.append(duplicate)
        extra = config_value()
        extra["unexpected"] = True
        mutations.append(extra)
        insecure = config_value()
        insecure["sources"][0]["endpoint"] = "http://markets.newyorkfed.org/data"
        mutations.append(insecure)
        off_allowlist = config_value()
        off_allowlist["sources"][0]["endpoint"] = "https://evil.example/data"
        mutations.append(off_allowlist)
        external_bind = config_value()
        external_bind["api"]["host"] = "0.0.0.0"
        mutations.append(external_bind)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                with tempfile.TemporaryDirectory() as temp:
                    path = Path(temp) / "config.json"
                    write_json(path, value)
                    with self.assertRaises(CanonicalDataError):
                        load_config(path)

    def test_config_rejects_unknown_adapter_bad_poll_and_missing_required_secret_name(self):
        unknown = config_value()
        unknown["sources"][0]["adapter"] = "mystery"
        fast = config_value()
        fast["sources"][0]["poll_seconds"] = 59
        secret = config_value()
        secret["sources"][0]["secret_required"] = True
        secret["sources"][0]["secret_env"] = None
        for value in (unknown, fast, secret):
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "config.json"
                write_json(path, value)
                with self.assertRaises(CanonicalDataError):
                    load_config(path)

    def test_config_service_store_and_website_poll_contracts_are_exact(self):
        bad_values = []
        service_extra = config_value()
        service_extra["service"]["extra"] = "not allowed"
        bad_values.append(service_extra)
        store_missing = config_value()
        del store_missing["store"]["runtime"]
        bad_values.append(store_missing)
        poll_type = config_value()
        poll_type["api"]["website_poll_seconds"] = "60"
        bad_values.append(poll_type)
        for index, value in enumerate(bad_values):
            with self.subTest(index=index):
                with tempfile.TemporaryDirectory() as temp:
                    path = Path(temp) / "config.json"
                    write_json(path, value)
                    with self.assertRaises(CanonicalDataError):
                        load_config(path)

    def test_env_file_is_literal_non_overwriting_and_rejects_invalid_names(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "local.env"
            path.write_text(
                "# local publisher credentials\n"
                "RMV2_EXISTING=must-not-overwrite\n"
                "RMV2_LITERAL=$(not executed);still literal\n",
                encoding="utf-8",
            )
            path.chmod(0o600)
            with mock.patch.dict(os.environ, {"RMV2_EXISTING": "preserved"}, clear=False):
                os.environ.pop("RMV2_LITERAL", None)
                load_env_file(path)
                self.assertEqual(os.environ["RMV2_EXISTING"], "preserved")
                self.assertEqual(
                    os.environ["RMV2_LITERAL"], "$(not executed);still literal"
                )
                os.environ.pop("RMV2_LITERAL", None)
            path.write_text("BAD-NAME=value\n", encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaises(CanonicalDataError):
                load_env_file(path)


class AdapterTests(unittest.TestCase):
    def test_publisher_client_blocks_missing_required_secret_before_network(self):
        source = source_config()
        source["secret_env"] = "RMV2_TEST_REQUIRED_SECRET"
        source["secret_required"] = True
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RMV2_TEST_REQUIRED_SECRET", None)
            with self.assertRaises(SourceBlocked):
                adapters.PublisherHttpClient().fetch(source)

    def test_response_validation_rejects_html_wrong_type_empty_and_non_200(self):
        source = source_config()
        accepted = HttpResponse(
            source["endpoint"], 200, {"content-type": "application/json; charset=utf-8"}, b"{}"
        )
        adapters.validate_response(source, accepted)
        rejected = (
            HttpResponse(source["endpoint"], 200, {"content-type": "text/html"}, b"<html>x"),
            HttpResponse(source["endpoint"], 200, {"content-type": "application/json"}, b""),
            HttpResponse(source["endpoint"], 500, {"content-type": "application/json"}, b"{}"),
        )
        for response in rejected:
            with self.subTest(response=response):
                with self.assertRaises(SourceUnavailable):
                    adapters.validate_response(source, response)

    def test_redirect_handler_blocks_non_https_and_off_allowlist_redirects(self):
        handler = adapters.UnsafeRedirectHandler(["allowed.example"])
        for url in ("http://allowed.example/data", "https://evil.example/data"):
            with self.subTest(url=url):
                with self.assertRaises(SourceBlocked):
                    handler.redirect_request(None, None, 302, "redirect", {}, url)

    def test_nyfed_adapter_preserves_clocks_mode_provenance_and_units(self):
        source = source_config()
        records = adapters.parse_nyfed_reference_rate_json(
            source, nyfed_body(), FIXED_TIME_1
        )
        self.assertEqual(len(records), 2)
        by_id = {record["series_id"]: record for record in records}
        rate = by_id["nyfed_test.SOFR.percentRate"]
        self.assertEqual(rate["value"], "3.65")
        self.assertEqual(rate["unit"], "percent")
        self.assertEqual(rate["observation_period"], "2026-07-28")
        self.assertEqual(rate["available_at"], FIXED_TIME_1)
        self.assertEqual(rate["information_set_mode"], "current_revised")
        self.assertEqual(rate["publisher_release_clock"], "publisher clock")
        self.assertEqual(rate["provenance_url"], source["endpoint"])

    def test_fred_graph_adapter_preserves_missing_values_and_provider_status(self):
        source = fred_source_config()
        body = (
            "observation_date,CPFF\n"
            "2026-07-27,0.23\n"
            "2026-07-28,\n"
            "2026-07-29,-0.01\n"
        ).encode("utf-8")
        records = adapters.parse_fred_graph_csv(
            source, body, FIXED_TIME_1
        )
        self.assertEqual(len(records), 3)
        self.assertEqual(
            [record["series_id"] for record in records],
            ["CPFF", "CPFF", "CPFF"],
        )
        self.assertEqual(records[0]["value"], "0.23")
        self.assertIsNone(records[1]["value"])
        self.assertEqual(records[1]["value_status"], "unavailable")
        self.assertEqual(records[2]["value"], "-0.01")
        self.assertTrue(all(
            record["provider_vintage_kind"] == "current_revised"
            for record in records
        ))
        self.assertTrue(all(
            record["strict_publisher_first_release_proven"] is False
            for record in records
        ))
        self.assertTrue(all(
            record["release_at"] is None
            for record in records
        ))
        self.assertEqual(
            adapters.normalize(source, body, FIXED_TIME_1),
            records,
        )

    def test_fred_graph_adapter_rejects_schema_aliases_and_bad_values(self):
        source = fred_source_config()
        invalid_bodies = (
            b"DATE,CPFF\n2026-07-29,0.1\n",
            b"observation_date,OTHER\n2026-07-29,0.1\n",
            b"observation_date,CPFF\n2026-07-29,NaN\n",
            b"observation_date,CPFF\n2026-07-29,0.1,extra\n",
            (
                b"observation_date,CPFF\n"
                b"2026-07-29,0.1\n"
                b"2026-07-29,0.2\n"
            ),
            b"observation_date,CPFF\n2026-02-30,0.1\n",
            b"observation_date,CPFF\n2026-07-29,\n",
        )
        for body in invalid_bodies:
            with self.subTest(body=body):
                with self.assertRaises(SourceUnavailable):
                    adapters.parse_fred_graph_csv(
                        source, body, FIXED_TIME_1
                    )
        source["series"]["unexpected"] = "not allowed"
        with self.assertRaises(SourceUnavailable):
            adapters.parse_fred_graph_csv(
                source,
                b"observation_date,CPFF\n2026-07-29,0.1\n",
                FIXED_TIME_1,
            )

    def test_treasury_bls_and_dol_adapters_normalize_without_inventing_release_clocks(self):
        treasury = source_config("treasury_test", "treasury_yield_xml")
        treasury["endpoint"] = "https://markets.newyorkfed.org/treasury.xml"
        xml = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"
 xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
 xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
 <entry><content><m:properties>
  <d:NEW_DATE>2026-07-28T00:00:00</d:NEW_DATE>
  <d:BC_10YEAR>4.33</d:BC_10YEAR>
 </m:properties></content></entry>
</feed>"""
        treasury_records = adapters.parse_treasury_yield_xml(
            treasury, xml, FIXED_TIME_1
        )
        self.assertEqual(treasury_records[0]["value"], "4.33")
        self.assertIsNone(treasury_records[0]["release_at"])

        bls = source_config("bls_test", "bls_json")
        bls["series"] = {
            "items": [{"label": "Payrolls", "series_id": "CESX", "unit": "thousands"}]
        }
        bls_payload = canonical_json_bytes({
            "Results": {
                "series": [{
                    "data": [{
                        "footnotes": [{"code": "P", "text": "Preliminary"}],
                        "period": "M06",
                        "value": "159000",
                        "year": "2026",
                    }],
                    "seriesID": "CESX",
                }]
            },
            "status": "REQUEST_SUCCEEDED",
        })
        bls_record = adapters.parse_bls_json(bls, bls_payload, FIXED_TIME_1)[0]
        self.assertEqual(bls_record["observation_period"], "2026-06")
        self.assertFalse(bls_record["latest_observation"])
        self.assertTrue(bls_record["preliminary"])
        self.assertEqual(bls_record["publisher_footnotes"][0]["code"], "P")

        dol = source_config("dol_test", "dol_eta539_csv")
        dol["series"] = {"retention_rows_per_state": 1}
        csv_bytes = (
            "st,rptdate,c2,c3,c8,c17,c18,c19,c20,c21,c22,c23\n"
            "CA,07/25/2026,07/18/2026,42000,350000,340000,18400000,"
            "8.28,7.53,109.96,F,07/26/2026\n"
            "CA,07/26/2026,07/19/2026,43000,351000,341000,18410000,"
            "8.31,7.56,109.92,F,07/27/2026\n"
        ).encode("utf-8")
        dol_records = adapters.parse_dol_eta539_csv(dol, csv_bytes, FIXED_TIME_1)
        self.assertEqual(len(dol_records), 7)
        self.assertTrue(all(record["state"] == "CA" for record in dol_records))
        self.assertTrue(all(record["observation_period"] == "2026-07-19" for record in dol_records))
        self.assertTrue(all(record["publisher_report_date"] == "2026-07-26" for record in dol_records))
        by_suffix = {
            record["series_id"].rsplit(".", 1)[-1]: record
            for record in dol_records
        }
        self.assertEqual(
            by_suffix["insured_unemployment_rate_current_13_week"]["value"],
            "8.31",
        )
        self.assertEqual(
            by_suffix["insured_unemployment_rate_current_13_week"]["unit"],
            "percent",
        )
        self.assertEqual(
            by_suffix["current_rate_as_percent_of_prior_year_average"]["value"],
            "109.92",
        )
        self.assertEqual(by_suffix["covered_employment"]["unit"], "persons")

    def test_bls_nyfed_and_dol_publisher_schema_tokens_are_typed(self):
        bls = source_config("bls_test", "bls_json")
        bls["series"] = {
            "items": [{"label": "Payrolls", "series_id": "CESX", "unit": "thousands"}]
        }

        def bls_bytes(latest_marker, data_row=True, footnote=None):
            row = {
                "footnotes": [footnote] if footnote is not None else [],
                "period": "M06",
                "value": "159000",
                "year": "2026",
            }
            if latest_marker is not ...:
                row["latest"] = latest_marker
            return canonical_json_bytes({
                "Results": {
                    "series": [{
                        "data": [row if data_row else "bad"],
                        "seriesID": "CESX",
                    }]
                },
                "status": "REQUEST_SUCCEEDED",
            })

        self.assertTrue(
            adapters.parse_bls_json(
                bls, bls_bytes("true"), FIXED_TIME_1
            )[0]["latest_observation"]
        )
        self.assertFalse(
            adapters.parse_bls_json(
                bls, bls_bytes(...), FIXED_TIME_1
            )[0]["latest_observation"]
        )
        self.assertFalse(
            adapters.parse_bls_json(
                bls, bls_bytes(None), FIXED_TIME_1
            )[0]["latest_observation"]
        )
        for invalid in ("false", "TRUE", 1, {}, True, False):
            with self.subTest(bls_latest=invalid):
                with self.assertRaises(SourceUnavailable):
                    adapters.parse_bls_json(
                        bls, bls_bytes(invalid), FIXED_TIME_1
                    )
        for body in (
            bls_bytes(..., data_row=False),
            bls_bytes(..., footnote="bad"),
        ):
            with self.assertRaises(SourceUnavailable):
                adapters.parse_bls_json(bls, body, FIXED_TIME_1)

        nyfed = source_config()
        with self.assertRaises(SourceUnavailable):
            adapters.parse_nyfed_reference_rate_json(
                nyfed, b'{"refRates":["bad"]}', FIXED_TIME_1
            )

        dol = source_config("dol_test", "dol_eta539_csv")
        dol["series"] = {"retention_rows_per_state": 1}
        bad_count = (
            "st,rptdate,c2,c3,c8,c17,c18,c19,c20,c21,c22,c23\n"
            "CA,07/26/2026,07/19/2026,43.5,351000,341000,18410000,"
            "8.31,7.56,109.92,F,07/27/2026\n"
        ).encode("utf-8")
        bad_rate = (
            "st,rptdate,c2,c3,c8,c17,c18,c19,c20,c21,c22,c23\n"
            "CA,07/26/2026,07/19/2026,43000,351000,341000,18410000,"
            "NaN,7.56,109.92,F,07/27/2026\n"
        ).encode("utf-8")
        for body in (bad_count, bad_rate):
            with self.assertRaises(SourceUnavailable):
                adapters.parse_dol_eta539_csv(dol, body, FIXED_TIME_1)

    def test_adapters_fail_closed_on_malformed_or_semantically_empty_inputs(self):
        source = source_config()
        cases = (
            lambda: adapters.parse_nyfed_reference_rate_json(
                source, b'{"refRates":[]}', FIXED_TIME_1
            ),
            lambda: adapters.parse_treasury_yield_xml(
                source, b"<not-feed/>", FIXED_TIME_1
            ),
            lambda: adapters.parse_bls_json(
                source, b'{"status":"REQUEST_FAILED"}', FIXED_TIME_1
            ),
            lambda: adapters.parse_dol_eta539_csv(
                source, b"st,rptdate\nCA,2026-01-01\n", FIXED_TIME_1
            ),
        )
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(SourceUnavailable):
                    case()

    def test_raw_capture_is_explicitly_unavailable_and_unknown_adapter_is_rejected(self):
        source = source_config("raw_test", "raw_capture")
        record = adapters.parse_raw_capture(source, b"opaque", FIXED_TIME_1)[0]
        self.assertIsNone(record["value"])
        self.assertEqual(record["value_status"], "unavailable")
        self.assertEqual(record["unit"], "publisher bytes")
        source["adapter"] = "unknown"
        with self.assertRaises(CanonicalDataError):
            adapters.normalize(source, b"opaque", FIXED_TIME_1)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_registry(self.root)
        self.config = config_value()
        self.store = LiveStore(self.root, self.config)
        self.store.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_content_addressed_objects_are_immutable_deduplicated_and_read_only(self):
        digest, path = self.store.store_source_object(b"publisher bytes")
        again_digest, again_path = self.store.store_source_object(b"publisher bytes")
        self.assertEqual((again_digest, again_path), (digest, path))
        self.assertEqual(path.read_bytes(), b"publisher bytes")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o444)
        with self.assertRaises(CanonicalDataError):
            self.store._write_immutable(path, b"different bytes")

        normalized = {"records": [], "schema_version": "test"}
        normalized_digest, normalized_path = self.store.store_normalized(normalized)
        self.assertEqual(read_json(normalized_path), normalized)
        self.assertEqual(
            normalized_digest,
            hashlib.sha256(canonical_json_bytes(normalized)).hexdigest(),
        )

    def test_refresh_lock_is_exclusive_and_released(self):
        with self.store.refresh_lock():
            with self.assertRaises(RuntimeError):
                with self.store.refresh_lock():
                    pass
        with self.store.refresh_lock():
            pass

    def test_publish_generation_keeps_current_previous_lkg_and_exact_pointer(self):
        snapshot1 = self._snapshot(FIXED_TIME_1, "receipt-1")
        pointer1 = self.store.publish_generation(
            snapshot1, self._status(FIXED_TIME_1), self._coverage(FIXED_TIME_1)
        )
        snapshot1_bytes = canonical_json_bytes(snapshot1)
        self.assertEqual(
            pointer1["snapshot_sha256"], hashlib.sha256(snapshot1_bytes).hexdigest()
        )
        self.assertEqual(pointer1["generation_sha256"], pointer1["manifest_sha256"])
        self.assertEqual(
            (self.store.public / "live_snapshot.json").read_bytes(), snapshot1_bytes
        )
        self.assertEqual(
            (self.store.public / "live_snapshot.lkg.json").read_bytes(), snapshot1_bytes
        )

        snapshot2 = self._snapshot(FIXED_TIME_2, "receipt-2")
        self.store.publish_generation(
            snapshot2, self._status(FIXED_TIME_2), self._coverage(FIXED_TIME_2)
        )
        self.assertEqual(
            (self.store.public / "live_snapshot.previous.json").read_bytes(),
            snapshot1_bytes,
        )
        self.assertEqual(
            read_json(self.store.public / "live_snapshot.lkg.json"), snapshot2
        )
        pointer = read_json(self.store.public / "latest.pointer.json")
        generation = self.store.root / "generations" / pointer["generation_sha256"]
        self.assertTrue((generation / "snapshot.json").is_file())
        self.assertTrue((generation / "status.json").is_file())
        self.assertTrue((generation / "coverage.json").is_file())
        self.assertTrue((generation / "manifest.json").is_file())

    def test_safe_public_read_rejects_symlink_hardlink_and_escape(self):
        root = self.store.public
        target = root / "value.json"
        target.write_bytes(b"{}")
        self.assertEqual(safe_regular_file(target, root), b"{}")
        symlink = root / "alias.json"
        symlink.symlink_to(target)
        with self.assertRaises(CanonicalDataError):
            safe_regular_file(symlink, root)
        hardlink = root / "hard.json"
        os.link(str(target), str(hardlink))
        with self.assertRaises(CanonicalDataError):
            safe_regular_file(target, root)
        outside = self.root / "outside.json"
        outside.write_bytes(b"{}")
        with self.assertRaises(CanonicalDataError):
            safe_regular_file(outside, root)

    def test_store_paths_cannot_escape_project_root(self):
        bad = config_value()
        bad["store"]["root"] = "../escape"
        with self.assertRaises(CanonicalDataError):
            LiveStore(self.root, bad)

    @staticmethod
    def _snapshot(generated_at, receipt):
        return {
            "generated_at": generated_at,
            "schema_version": "recession-monitor-v2.live-snapshot.v1",
            "series": {},
            "sources": [],
        }

    @staticmethod
    def _status(generated_at):
        return {
            "generated_at": generated_at,
            "schema_version": "recession-monitor-v2.live-status.v1",
        }

    @staticmethod
    def _coverage(generated_at):
        return {
            "generated_at": generated_at,
            "schema_version": "recession-monitor-v2.source-coverage.v1",
        }


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_registry(self.root)
        self.config = config_value()

    def tearDown(self):
        self.temp.cleanup()

    def test_successful_refresh_publishes_provenance_but_never_binds_scientific_outputs(self):
        client = FakeHttpClient()
        pipeline = RefreshPipeline(
            self.root, self.config, client, clock=lambda: FIXED_TIME_1
        )
        result = pipeline.refresh()
        self.assertEqual(result["snapshot_source_count"], 1)
        self.assertEqual(result["outcomes"][0]["outcome"], "success")
        self.assertEqual(client.calls, ["nyfed_test"])
        snapshot = read_json(self.root / "public" / "live_snapshot.json")
        status = read_json(self.root / "public" / "operational_status.json")
        self.assertEqual(snapshot["data_policy"]["ai_dependency"], "none")
        self.assertEqual(
            snapshot["data_policy"]["scientific_model_binding"], "not_authorized"
        )
        self.assertTrue(snapshot["data_policy"]["current_revised_is_not_strict_first_release"])
        self.assertFalse(status["scientific_outputs_updated"])
        self.assertTrue(status["no_ai"])
        self.assertEqual(status["service_state"], "ready")
        source = snapshot["sources"][0]
        normalized = pipeline.store.read_normalized(source["normalized_sha256"])
        record = normalized["records"][0]
        self.assertEqual(record["source_bytes_sha256"], source["source_bytes_sha256"])
        self.assertEqual(record["retrieved_at"], FIXED_TIME_1)

    def test_pipeline_reuses_verified_generation_while_pointer_bytes_are_unchanged(self):
        pipeline = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient(),
            clock=lambda: FIXED_TIME_1,
        )
        pipeline.refresh()
        with mock.patch(
            "live_data.rmv2_live.pipeline.read_verified_generation",
            wraps=read_verified_generation,
        ) as verifier:
            first = pipeline._current_generation_binding()
            second = pipeline._current_generation_binding()
        self.assertEqual(first, second)
        self.assertEqual(verifier.call_count, 1)

    def test_verify_oracle_rejects_post_warm_immutable_evidence_corruption(self):
        # F1: the hot generation-read paths (pipeline tick, live server,
        # post-publish readback) authenticate against the content-addressed
        # binding attestation and do NOT re-hash the (multi-GB, weekly-vintage)
        # immutable evidence of unchanged sources on every operation — that
        # O(store) full closure moved to the `attest_bindings=False` oracle
        # (`rmv2_live verify`). This test pins the relocated contract: the
        # attested hot path stays serviceable, and the full oracle rejects the
        # same-size corruption of an immutable source object.
        pipeline = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient(),
            clock=lambda: FIXED_TIME_1,
        )
        pipeline.refresh()
        pipeline._current_generation_binding()
        # Warm the content-addressed attestation for the active bindings.
        for binding in pipeline.build_snapshot(
            FIXED_TIME_1, use_projection_cache=True
        )["sources"]:
            pipeline.store.attest_source_binding(binding)
        head = pipeline.store.read_source_head("nyfed_test")
        raw_path = (
            pipeline.store.root / "objects" / "sha256" /
            head["source_bytes_sha256"][:2] /
            (head["source_bytes_sha256"] + ".bin")
        )
        raw_path.chmod(0o644)
        corrupted = bytearray(raw_path.read_bytes())
        corrupted[0] = (corrupted[0] + 1) % 256
        raw_path.write_bytes(bytes(corrupted))
        # The full-closure oracle re-reads and re-hashes the evidence and MUST
        # reject the corruption.
        with self.assertRaises(CanonicalDataError):
            read_verified_generation(
                pipeline.store.public,
                pipeline.store.root / "generations",
                attest_bindings=False,
            )

    def test_failed_refresh_preserves_last_good_head_and_data_with_typed_attempt(self):
        first = RefreshPipeline(
            self.root, self.config, FakeHttpClient(), clock=lambda: FIXED_TIME_1
        )
        first.refresh()
        prior_head = first.store.read_source_head("nyfed_test")
        prior_latest = read_json(self.root / "public" / "live_snapshot.json")["series"]

        failed = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient(error=SourceUnavailable("publisher timeout")),
            clock=lambda: FIXED_TIME_2,
        )
        result = failed.refresh()
        self.assertEqual(result["outcomes"][0]["outcome"], "failed")
        self.assertEqual(failed.store.read_source_head("nyfed_test"), prior_head)
        current = read_json(self.root / "public" / "live_snapshot.json")
        self.assertEqual(current["series"], prior_latest)
        status = failed.store.read_source_status("nyfed_test")
        self.assertEqual(status["last_success_at"], FIXED_TIME_1)
        self.assertEqual(status["error"]["type"], "SourceUnavailable")
        attempts = list((failed.store.root / "attempts" / "nyfed_test").glob("*.json"))
        self.assertEqual(len(attempts), 1)
        self.assertEqual(read_json(attempts[0])["outcome"], "failed")

    def test_failed_health_survives_a_later_not_due_scheduler_tick(self):
        first = RefreshPipeline(
            self.root, self.config, FakeHttpClient(), clock=lambda: FIXED_TIME_1
        )
        first.refresh()
        pointer_before = read_json(
            self.root / "public" / "latest.pointer.json"
        )

        failed = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient(error=SourceUnavailable("publisher timeout")),
            clock=lambda: FIXED_TIME_2,
        )
        failed.refresh()

        scheduler = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient(error=AssertionError("not-due source was fetched")),
            clock=lambda: FIXED_TIME_3,
        )
        result = scheduler.refresh(due_only=True)

        self.assertEqual(result["outcomes"], [{
            "outcome": "not_due",
            "source_id": "nyfed_test",
        }])
        self.assertIsNone(result["pointer"])
        self.assertEqual(
            read_json(self.root / "public" / "latest.pointer.json"),
            pointer_before,
        )
        operational = read_json(
            self.root / "public" / "operational_status.json"
        )
        self.assertEqual(operational["latest_attempt_counts"], {"not_due": 1})
        self.assertEqual(
            operational["last_refresh_state_counts"],
            operational["latest_attempt_counts"],
        )
        self.assertEqual(
            operational["current_source_health"],
            {"nyfed_test": "failed"},
        )
        self.assertEqual(
            operational["current_source_health_counts"],
            {"failed": 1},
        )
        self.assertEqual(operational["service_state"], "degraded")

    def test_stranded_source_head_is_published_on_the_next_not_due_tick(self):
        first = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient({"nyfed_test": nyfed_body("3.65")}),
            clock=lambda: FIXED_TIME_1,
        )
        first.refresh()
        pointer_before = read_json(
            self.root / "public" / "latest.pointer.json"
        )

        crashing = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient({"nyfed_test": nyfed_body("3.70")}),
            clock=lambda: FIXED_TIME_2,
        )
        with mock.patch.object(
            crashing.store,
            "publish_generation",
            side_effect=RuntimeError("injected crash before generation commit"),
        ):
            with self.assertRaises(RuntimeError):
                crashing.refresh()

        stranded_head = crashing.store.read_source_head("nyfed_test")
        old_generation = read_verified_generation(
            crashing.store.public,
            crashing.store.root / "generations",
        )
        self.assertNotEqual(
            stranded_head["receipt_sha256"],
            old_generation["manifest"]["source_head_receipt_sha256"][
                "nyfed_test"
            ],
        )
        self.assertEqual(
            read_json(self.root / "public" / "latest.pointer.json"),
            pointer_before,
        )

        recovery = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient(error=AssertionError("not-due source was fetched")),
            clock=lambda: FIXED_TIME_3,
        )
        result = recovery.refresh(due_only=True)
        self.assertEqual(result["outcomes"][0]["outcome"], "not_due")
        self.assertIsNotNone(result["pointer"])
        self.assertNotEqual(result["pointer"], pointer_before)
        generation = read_verified_generation(
            recovery.store.public,
            recovery.store.root / "generations",
        )
        runtime_map = {
            source_id: head["receipt_sha256"]
            for source_id, head in recovery.store.all_source_heads().items()
        }
        snapshot_map = {
            source["source_id"]: source["receipt_sha256"]
            for source in generation["members"]["snapshot.json"]["sources"]
        }
        self.assertEqual(
            generation["manifest"]["source_head_receipt_sha256"],
            runtime_map,
        )
        self.assertEqual(snapshot_map, runtime_map)
        operational = read_json(
            self.root / "public" / "operational_status.json"
        )
        self.assertIn(
            "source_head_generation_diverged",
            operational["generation_advance_reasons"],
        )
        self.assertFalse(operational["generation_recovery_required"])
        self.assertEqual(operational["service_state"], "ready")

    def test_stranded_head_recovery_rejects_missing_evidence_and_keeps_lkg(self):
        first = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient({"nyfed_test": nyfed_body("3.65")}),
            clock=lambda: FIXED_TIME_1,
        )
        first.refresh()
        pointer_before = read_json(
            self.root / "public" / "latest.pointer.json"
        )

        crashing = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient({"nyfed_test": nyfed_body("3.70")}),
            clock=lambda: FIXED_TIME_2,
        )
        with mock.patch.object(
            crashing.store,
            "publish_generation",
            side_effect=RuntimeError("injected crash before generation commit"),
        ):
            with self.assertRaises(RuntimeError):
                crashing.refresh()
        stranded_head = crashing.store.read_source_head("nyfed_test")
        normalized_path = (
            crashing.store.root / "normalized" / "sha256" /
            stranded_head["normalized_sha256"][:2] /
            (stranded_head["normalized_sha256"] + ".json")
        )
        normalized_path.unlink()

        recovery = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient(error=AssertionError("not-due source was fetched")),
            clock=lambda: FIXED_TIME_3,
        )
        with self.assertRaises(CanonicalDataError):
            recovery.refresh(due_only=True)
        self.assertEqual(
            read_json(self.root / "public" / "latest.pointer.json"),
            pointer_before,
        )
        operational = read_json(
            self.root / "public" / "operational_status.json"
        )
        self.assertTrue(operational["generation_recovery_required"])
        self.assertEqual(operational["service_state"], "degraded")

    def test_head_normalized_drift_cannot_bypass_receipt_binding(self):
        first = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient({"nyfed_test": nyfed_body("3.65")}),
            clock=lambda: FIXED_TIME_1,
        )
        first.refresh()
        pointer_before = read_json(
            self.root / "public" / "latest.pointer.json"
        )
        head = first.store.read_source_head("nyfed_test")
        original_receipt = head["receipt_sha256"]
        altered = copy.deepcopy(
            first.store.read_normalized(head["normalized_sha256"])
        )
        altered["records"][0]["value"] = "999.0"
        altered_digest, _ = first.store.store_normalized(altered)
        head["normalized_sha256"] = altered_digest
        first.store.write_source_head("nyfed_test", head)

        recovery = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient(error=AssertionError("not-due source was fetched")),
            clock=lambda: "2026-07-29T12:01:00Z",
        )
        with mock.patch(
            "live_data.rmv2_live.pipeline.SNAPSHOT_MATERIALIZER_VERSION",
            "latest_only.receipt_binding_test",
        ):
            with self.assertRaises(CanonicalDataError):
                recovery.refresh(due_only=True)

        self.assertEqual(
            read_json(self.root / "public" / "latest.pointer.json"),
            pointer_before,
        )
        self.assertEqual(
            recovery.store.read_source_head("nyfed_test")["receipt_sha256"],
            original_receipt,
        )
        generation = read_verified_generation(
            recovery.store.public,
            recovery.store.root / "generations",
        )
        served = next(iter(
            generation["members"]["snapshot.json"]["series"].values()
        ))
        self.assertNotEqual(served["latest"]["value"], "999.0")
        operational = read_json(
            self.root / "public" / "operational_status.json"
        )
        self.assertTrue(operational["generation_recovery_required"])
        self.assertEqual(operational["service_state"], "degraded")

    def test_blocked_source_without_prior_data_publishes_status_but_no_snapshot(self):
        client = FakeHttpClient(error=SourceBlocked("missing required secret"))
        pipeline = RefreshPipeline(
            self.root, self.config, client, clock=lambda: FIXED_TIME_1
        )
        result = pipeline.refresh()
        self.assertEqual(result["outcomes"][0]["outcome"], "blocked")
        self.assertIsNone(result["pointer"])
        self.assertFalse((self.root / "public" / "live_snapshot.json").exists())
        status = read_json(self.root / "public" / "operational_status.json")
        self.assertEqual(status["service_state"], "awaiting_first_success")
        self.assertFalse(status["scientific_outputs_updated"])

    def test_due_only_skips_recent_attempt_and_unknown_source_ids_fail_closed(self):
        client = FakeHttpClient()
        pipeline = RefreshPipeline(
            self.root, self.config, client, clock=lambda: FIXED_TIME_1
        )
        pipeline.refresh()
        matrix_before = (
            self.root / "live_data" / "catalog" / "source_matrix.v1.json"
        ).read_bytes()
        with mock.patch.object(
            pipeline,
            "build_snapshot",
            side_effect=AssertionError(
                "a no-change scheduler tick must not rebuild the snapshot"
            ),
        ):
            result = pipeline.refresh(due_only=True)
        self.assertEqual(result["outcomes"][0]["outcome"], "not_due")
        self.assertIsNone(result["pointer"])
        operational = read_json(
            self.root / "public" / "operational_status.json"
        )
        self.assertFalse(operational["generation_advanced"])
        self.assertEqual(
            (
                self.root / "live_data" / "catalog" /
                "source_matrix.v1.json"
            ).read_bytes(),
            matrix_before,
        )
        self.assertEqual(client.calls, ["nyfed_test"])
        with self.assertRaises(ValueError):
            pipeline.refresh(source_ids=["not-configured"])

    def test_public_snapshot_keeps_latest_only_and_normalized_store_keeps_history(self):
        body = canonical_json_bytes({
            "refRates": [
                {
                    "effectiveDate": "2026-07-27",
                    "percentRate": "3.60",
                    "revisionIndicator": "",
                    "type": "SOFR",
                    "volumeInBillions": "2050",
                },
                {
                    "effectiveDate": "2026-07-28",
                    "percentRate": "3.65",
                    "revisionIndicator": "",
                    "type": "SOFR",
                    "volumeInBillions": "2100",
                },
            ],
        })
        pipeline = RefreshPipeline(
            self.root,
            self.config,
            FakeHttpClient({"nyfed_test": body}),
            clock=lambda: FIXED_TIME_1,
        )
        pipeline.refresh()

        snapshot = read_json(self.root / "public" / "live_snapshot.json")
        source = snapshot["sources"][0]
        normalized = pipeline.store.read_normalized(source["normalized_sha256"])
        self.assertEqual(len(normalized["records"]), 4)
        self.assertEqual(snapshot["full_history_record_count"], 4)
        self.assertEqual(snapshot["projected_record_count"], 2)
        self.assertEqual(
            snapshot["snapshot_projection"],
            {
                "full_history_location": (
                    "content_addressed_normalized_source_objects"
                ),
                "observations_per_series": 1,
                "projection": "latest_admissible_observation_only",
            },
        )
        for item in snapshot["series"].values():
            self.assertEqual(len(item["observations"]), 1)
            self.assertEqual(item["latest"], item["observations"][0])
            self.assertEqual(
                item["latest"]["observation_period"],
                "2026-07-28",
            )

    def test_coverage_distinguishes_live_rights_target_and_unparsed_states(self):
        config = config_value()
        config["sources"][0]["adapter"] = "raw_capture"
        client = FakeHttpClient({"nyfed_test": b"opaque publisher workbook"})
        pipeline = RefreshPipeline(
            self.root, config, client, clock=lambda: FIXED_TIME_1
        )
        pipeline.refresh()
        coverage = read_json(self.root / "public" / "source_coverage.json")
        by_id = {row["source_id"]: row["live_state"] for row in coverage["rows"]}
        self.assertEqual(
            by_id["nyfed_reference_rates"], "captured_unparsed_not_admissible"
        )
        self.assertEqual(by_id["licensed_source"], "blocked_rights")
        self.assertEqual(by_id["target_source"], "quarantined_target_bearing")


class ApiDisconnectUnitTests(unittest.TestCase):
    def test_client_disconnect_during_response_is_an_expected_noop(self):
        handler = object.__new__(LiveDataApiHandler)
        handler.command = "GET"
        handler.send_response = mock.Mock()
        handler.send_header = mock.Mock()
        handler.end_headers = mock.Mock()
        handler.wfile = mock.Mock()
        handler.wfile.write.side_effect = BrokenPipeError("client disconnected")
        handler._send_json(200, {"ok": True})
        self.assertEqual(handler.wfile.write.call_count, 1)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_registry(self.root)
        self.store = LiveStore(self.root, config_value())
        self.store.initialize()
        self.public = self.store.public
        self._publish_api_fixtures()
        self.server = create_server(
            "127.0.0.1",
            0,
            self.public,
            self.store.root / "generations",
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def _publish_api_fixtures(self):
        status = {
            "generated_at": FIXED_TIME_1,
            "no_ai": True,
            "schema_version": "recession-monitor-v2.live-status.v1",
            "scientific_outputs_updated": False,
            "service_state": "ready",
        }
        snapshot = {
            "generated_at": FIXED_TIME_1,
            "schema_version": "recession-monitor-v2.live-snapshot.v1",
            "series": {
                "source.series": {
                    "latest": {"value": "3.65"},
                    "observations": [{"value": "3.65"}],
                    "series_id": "source.series",
                    "source_id": "source",
                    "unit": "percent",
                },
            },
            "sources": [],
        }
        coverage = {
            "rows": [],
            "schema_version": "recession-monitor-v2.source-coverage.v1",
        }
        self.store.publish_generation(snapshot, status, coverage)

    def request(self, method, path, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        merged = {"Host": "127.0.0.1:%d" % self.port}
        merged.update(headers or {})
        connection.request(method, path, headers=merged)
        response = connection.getresponse()
        body = response.read()
        result = (
            response.status,
            {key.lower(): value for key, value in response.getheaders()},
            body,
        )
        connection.close()
        return result

    def test_health_snapshot_sources_series_and_head_routes_are_read_only_json(self):
        cases = (
            ("/healthz", "recession-monitor-v2.health.v1"),
            ("/api/v1/status", "recession-monitor-v2.live-status.v1"),
            ("/api/v1/bundle", "recession-monitor-v2.live-api-bundle.v2"),
            ("/api/v1/snapshot", "recession-monitor-v2.live-snapshot.v1"),
            ("/api/v1/sources", "recession-monitor-v2.source-coverage.v1"),
        )
        for path, schema in cases:
            with self.subTest(path=path):
                status, headers, body = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertEqual(strict_json_loads(body)["schema_version"], schema)
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
        status, _, body = self.request("GET", "/api/v1/series/source.series")
        self.assertEqual(status, 200)
        self.assertEqual(strict_json_loads(body)["latest"]["value"], "3.65")
        status, headers, body = self.request("HEAD", "/api/v1/status")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertGreater(int(headers["content-length"]), 0)

    def test_origin_and_host_controls_allow_only_file_and_loopback_origins(self):
        for origin in ("null", "http://127.0.0.1:8080", "http://localhost"):
            with self.subTest(origin=origin):
                status, headers, _ = self.request(
                    "GET", "/api/v1/status", {"Origin": origin}
                )
                self.assertEqual(status, 200)
                self.assertEqual(headers["access-control-allow-origin"], origin)
        status, _, body = self.request(
            "GET", "/api/v1/status", {"Origin": "https://evil.example"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(strict_json_loads(body)["error"]["code"], "forbidden")
        status, _, body = self.request(
            "GET", "/api/v1/status", {"Host": "evil.example"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(strict_json_loads(body)["error"]["code"], "forbidden")

    def test_method_path_and_missing_series_controls_fail_closed(self):
        for method in ("POST", "PUT", "DELETE"):
            with self.subTest(method=method):
                status, _, body = self.request(method, "/api/v1/status")
                self.assertEqual(status, 405)
                self.assertEqual(
                    strict_json_loads(body)["error"]["code"], "method_not_allowed"
                )
        status, _, body = self.request("GET", "/api/v1/series/missing")
        self.assertEqual(status, 404)
        self.assertEqual(strict_json_loads(body)["error"]["code"], "series_not_found")
        status, _, body = self.request("GET", "/api/v1/series/bad%2Fpath")
        self.assertEqual(status, 400)
        self.assertEqual(strict_json_loads(body)["error"]["code"], "invalid_series_id")
        status, _, body = self.request("GET", "/unknown")
        self.assertEqual(status, 404)
        self.assertEqual(strict_json_loads(body)["error"]["code"], "not_found")

    def test_forbidden_methods_still_enforce_host_and_origin_security(self):
        status, _, body = self.request(
            "POST",
            "/api/v1/status",
            {"Host": "evil.example", "Origin": "https://evil.example"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(strict_json_loads(body)["error"]["code"], "forbidden")

    def test_preflight_is_narrow_and_external_bind_is_prohibited(self):
        status, headers, body = self.request(
            "OPTIONS", "/api/v1/status", {"Origin": "null"}
        )
        self.assertEqual(status, 204)
        self.assertEqual(body, b"")
        self.assertEqual(headers["access-control-allow-methods"], "GET, HEAD, OPTIONS")
        self.assertEqual(headers["access-control-allow-origin"], "null")
        with self.assertRaises(ValueError):
            create_server("0.0.0.0", 0, self.public)

    def test_invalid_or_missing_local_state_is_typed_and_never_followed(self):
        pointer = read_json(self.public / "latest.pointer.json")
        generation = (
            self.store.root / "generations" / pointer["generation_sha256"]
        )
        (generation / "snapshot.json").unlink()
        status, _, body = self.request("GET", "/api/v1/snapshot")
        self.assertEqual(status, 500)
        self.assertEqual(
            strict_json_loads(body)["error"]["code"], "invalid_local_state"
        )
        (generation / "snapshot.json").write_bytes(
            (self.public / "live_snapshot.json").read_bytes()
        )
        target = self.store.root / "generations" / "elsewhere.json"
        target.write_bytes(b"{}")
        (generation / "status.json").unlink()
        (generation / "status.json").symlink_to(target)
        status, _, body = self.request("GET", "/api/v1/status")
        self.assertEqual(status, 500)
        self.assertEqual(strict_json_loads(body)["error"]["code"], "invalid_local_state")

    def test_only_absent_public_pointer_is_snapshot_unavailable(self):
        (self.public / "latest.pointer.json").unlink()
        status, _, body = self.request("GET", "/api/v1/snapshot")
        self.assertEqual(status, 503)
        self.assertEqual(
            strict_json_loads(body)["error"]["code"],
            "snapshot_unavailable",
        )

    def test_atomic_bundle_rejects_pointer_snapshot_mismatch(self):
        pointer_path = self.public / "latest.pointer.json"
        pointer = read_json(pointer_path)
        pointer["snapshot_sha256"] = "f" * 64
        atomic_write_json(pointer_path, pointer)
        status, _, body = self.request("GET", "/api/v1/bundle")
        self.assertEqual(status, 500)
        self.assertEqual(strict_json_loads(body)["error"]["code"], "invalid_local_state")


class StaticIntegrationContractTests(unittest.TestCase):
    def test_live_subsystem_has_no_ai_client_imports_or_ai_service_endpoints(self):
        prohibited_imports = {
            "anthropic",
            "cohere",
            "gemini",
            "google.generativeai",
            "openai",
        }
        prohibited_hosts = (
            "api.anthropic.com",
            "api.openai.com",
            "generativelanguage.googleapis.com",
        )
        package = PROJECT_ROOT / "live_data" / "rmv2_live"
        imports = set()
        combined = ""
        for path in sorted(package.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            combined += "\n" + source.lower()
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
        self.assertFalse(prohibited_imports.intersection(imports))
        for host in prohibited_hosts:
            self.assertNotIn(host, combined)
        config = read_json(PROJECT_ROOT / "live_data" / "config" / "sources.v1.json")
        self.assertTrue(all(source["endpoint"].startswith("https://") for source in config["sources"]))
        self.assertFalse(any(
            any(host in source["endpoint"] for host in prohibited_hosts)
            for source in config["sources"]
        ))

    def test_website_bridge_uses_loopback_read_only_api_and_preserves_offline_fallback(self):
        html = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        bridge_present = (
            "127.0.0.1:8792" in html
            or "/api/v1/snapshot" in html
            or "rmv2-live" in html.lower()
        )
        if not bridge_present:
            self.skipTest("website live-data bridge has not been added yet")
        self.assertIn("127.0.0.1:8792", html)
        self.assertIn("/api/v1/bundle", html)
        self.assertIn("recession-monitor-v2.live-api-bundle.v2", html)
        self.assertIn("fetch(", html)
        self.assertIn("scientific_outputs_updated!==false", html)
        self.assertIn('scientific_model_binding!=="not_authorized"', html)
        self.assertIn("RMV2_LIVE_SOURCE_POINTER", html)
        self.assertIn("rmv2-live-source-update", html)
        self.assertIn("current_source_health_counts", html)
        self.assertIn("latest_attempt_counts", html)
        self.assertRegex(
            html.lower(),
            r"(offline|last[- ]known[- ]good|embedded|snapshot unavailable)",
        )
        self.assertNotIn("api.openai.com", html.lower())
        self.assertNotIn("api.anthropic.com", html.lower())

    def test_website_publisher_state_fails_closed_on_operational_degradation(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required to execute the display-state helper")
        html = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        start = html.index("function derivePublisherDataDisplayState")
        end = html.index("function fetchJson", start)
        helper = html[start:end]
        cases = [
            [
                {
                    "service_state": "ready",
                    "generation_recovery_required": False,
                    "snapshot_source_count": 53,
                },
                {"healthy": 53},
                "ready",
            ],
            [
                {
                    "service_state": "degraded",
                    "generation_recovery_required": True,
                    "snapshot_source_count": 53,
                },
                {"healthy": 53},
                "stale",
            ],
            [
                {
                    "service_state": "ready",
                    "generation_recovery_required": False,
                    "snapshot_source_count": 53,
                },
                {"healthy": 52, "awaiting_first_success": 1},
                "stale",
            ],
            [
                {
                    "service_state": "ready",
                    "generation_recovery_required": False,
                    "snapshot_source_count": 53,
                },
                {"healthy": 52, "recovery_pending": 1},
                "stale",
            ],
            [
                {
                    "service_state": "ready",
                    "generation_recovery_required": False,
                    "snapshot_source_count": 53,
                },
                {},
                "stale",
            ],
            [
                {
                    "service_state": "ready",
                    "generation_recovery_required": False,
                    "snapshot_source_count": 53,
                },
                {"not_due": 53},
                "stale",
            ],
            [
                {
                    "service_state": "ready",
                    "generation_recovery_required": False,
                    "snapshot_source_count": 53,
                },
                {"healthy": 52},
                "stale",
            ],
        ]
        script = (
            helper
            + "\nconst cases="
            + json.dumps(cases, separators=(",", ":"))
            + ";\nfor(const row of cases){"
            + "const got=derivePublisherDataDisplayState(row[0],row[1]);"
            + "if(got!==row[2])throw new Error(JSON.stringify({row:row,got:got}));"
            + "}\n"
        )
        result = subprocess.run(
            [node],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_embedded_scientific_monitor_is_frozen_while_publisher_service_is_live(self):
        html = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(
            'data-scientific-state="frozen-embedded-snapshot"',
            html,
        )
        self.assertIn(
            "Scientific monitor snapshot: frozen as published Jul 29, 2026",
            html,
        )
        self.assertIn(
            "The publisher-data service updates independently",
            html,
        )
        for prohibited in (
            "United States &middot; live",
            "Every number recomputed daily",
            "Live status &amp; the record",
            "The watch today &#8212; live",
            "floored by live stress",
            "today&#8217;s reading is the live number above it",
            "recomputed on every refresh",
            "Data refreshes run three times daily",
        ):
            self.assertNotIn(prohibited, html)

    def test_launchd_contract_is_loopback_no_ai_and_has_deterministic_environment(self):
        candidates = sorted((PROJECT_ROOT / "live_data").rglob("*.plist"))
        if not candidates:
            self.skipTest("launchd service definition has not been added yet")
        self.assertEqual(
            [path.name for path in candidates],
            [
                "com.anthonyhall.recession-monitor-v2.data-autopilot.plist",
                "com.anthonyhall.recession-monitor-v2.live-data.plist",
                "com.anthonyhall.recession-monitor-v2.watchdog.plist",
            ],
            "exactly three reviewed RESIDENT launchd agents may exist: the one "
            "resident live-data service, the one one-shot data autopilot, and "
            "the one read-only hang watchdog (health probe + kickstart, never a "
            "writer). The gated admission runner is NOT among them: it is an "
            "on-demand, operator-triggered batch writer "
            "(live_data/scripts/admission_runner.command), never a scheduled "
            "launchd job. A StartInterval admission-runner tick was a SECOND, "
            "uncoordinated writer that raced a manual batch (PHASE2 B1.3 root "
            "cause); its plist is quarantined under _quarantined_plists/.",
        )
        service_plists = [
            path for path in candidates
            if path.name.endswith(".live-data.plist")
        ]
        self.assertEqual(len(service_plists), 1)
        # The admission runner must NOT be installed as a launchd job at all.
        # It is the single sanctioned store writer, but invoked on-demand by an
        # operator, never resident and never on a StartInterval. It is also
        # absent from the resident quiesce set AGENT_LABELS (it cannot quiesce
        # itself, and start_agents must never re-bootstrap it).
        admission_plists = [
            path for path in candidates
            if path.name.endswith(".admission-runner.plist")
        ]
        self.assertEqual(
            admission_plists, [],
            "admission-runner must not be installed as a launchd job; it is "
            "on-demand only and its plist lives under _quarantined_plists/",
        )
        # The watchdog is a reviewed non-writer: it must not carry the resident
        # service verb, must not be a second scheduler/writer, and stays AI-free.
        watchdog_plists = [
            path for path in candidates
            if path.name.endswith(".watchdog.plist")
        ]
        self.assertEqual(len(watchdog_plists), 1)
        with watchdog_plists[0].open("rb") as handle:
            watchdog_value = plistlib.load(handle)
        watchdog_args = watchdog_value.get("ProgramArguments", [])
        watchdog_joined = " ".join(str(item) for item in watchdog_args).lower()
        self.assertIn("watchdog.sh", watchdog_joined)
        self.assertNotIn("service", watchdog_args)
        self.assertNotIn("caffeinate", watchdog_joined)
        self.assertNotIn("openai", watchdog_joined)
        self.assertNotIn("anthropic", watchdog_joined)
        self.assertFalse(watchdog_value.get("KeepAlive"))
        self.assertTrue(watchdog_value.get("StartInterval"))
        with service_plists[0].open("rb") as handle:
            value = plistlib.load(handle)
        arguments = value.get("ProgramArguments", [])
        joined = " ".join(str(item) for item in arguments).lower()
        self.assertTrue(value.get("RunAtLoad"))
        self.assertTrue(value.get("KeepAlive"))
        self.assertIn("service", arguments)
        self.assertNotIn("caffeinate", joined)
        self.assertNotIn("openai", joined)
        self.assertNotIn("anthropic", joined)
        environment = value.get("EnvironmentVariables", {})
        self.assertEqual(environment.get("PYTHONHASHSEED"), "0")
        self.assertEqual(environment.get("PYTHONDONTWRITEBYTECODE"), "1")
        self.assertEqual(environment.get("TZ"), "UTC")
        scripts = PROJECT_ROOT / "live_data" / "scripts"
        install = (scripts / "install_launchd.sh").read_text(encoding="utf-8")
        refresh = (scripts / "refresh_now.sh").read_text(encoding="utf-8")
        uninstall = (scripts / "uninstall_launchd.sh").read_text(encoding="utf-8")
        self.assertIn("launchctl bootstrap", install)
        self.assertIn("launchctl kickstart", install)
        self.assertIn("BOOTSTRAP_ATTEMPTS=5", install)
        self.assertIn("launchctl print", install)
        self.assertIn("/bin/sleep 1", install)
        self.assertIn("LaunchAgent bootstrap failed after", install)
        self.assertIn("live_data.rmv2_live", refresh)
        self.assertIn("refresh", refresh)
        self.assertNotIn("caffeinate", install + refresh + uninstall)
        self.assertIn("Stored observations, receipts, snapshots, and logs were not deleted", uninstall)


if __name__ == "__main__":
    unittest.main()
