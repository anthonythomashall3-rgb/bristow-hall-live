"""B-LAND-3 §1 — offline acquisition-receipt schema variant + additive verify
closure extension, and the offline BINDING path (source object + normalized +
offline receipt + source head), proven end-to-end into a published generation.

Owner ruling 2026-08-05 (Option a): an ADDITIVE offline receipt-schema variant
plus an ADDITIVE verify-closure extension. The offline receipt is the SINGLE
provenance home (§24 one-home) — no sidecar, no fabricated http receipt.

Proofs:
  v1 UNCHANGED  a real live_http (acquisition-receipt.v1) binding still verifies
                byte-for-byte; a v1 receipt missing a required field still FAILS.
  OFFLINE OK    an offline (offline-acquisition-receipt.v1) binding verifies via
                verify_source_binding AND the strict verify_offline_source_binding,
                and publishes into a real generation that read_verified_generation
                re-authenticates in the full raw->normalized->receipt->binding
                closure.
  (a)           an offline receipt missing a per-file source sha FAILS.
  (b)           an offline receipt carrying an http field FAILS.
  (c)           a live v1 receipt missing a v1 field still FAILS (v1 closure intact).
  (d)           a fabricated live (v1) receipt for an offline object FAILS the
                strict offline verify (kind mismatch with provenance).
  ROUND-TRIP    landed observations == the in-window CSV data cells.
  GATE          the append-only .DEEPASOF family-prefix gate still red-bars a
                second same-base deep candidate after the first is admitted.
"""
from __future__ import absolute_import

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import feed_factory  # noqa: E402
from live_data.rmv2_live import vintage_csv_transcoder as vct  # noqa: E402
from live_data.rmv2_live.adapters import HttpResponse  # noqa: E402
from live_data.rmv2_live.canonical import CanonicalDataError  # noqa: E402
from live_data.rmv2_live.pipeline import RefreshPipeline  # noqa: E402
from live_data.rmv2_live.store import (  # noqa: E402
    OFFLINE_ACQUISITION_RECEIPT_SCHEMA,
    canonical_json_bytes,
    read_json,
    read_verified_generation,
    source_binding_from_head,
)

from live_data.rmv2_live.offline_binding import (  # noqa: E402
    bind_offline_vintage,
    build_offline_receipt,
)

ATTEMPTED_AT = "2026-08-05T12:00:00Z"
AS_OF = "2026-08-05T00:00:00Z"

# NFCI vintages: two in the deep window [2000-01-01, 2019-12-31] + one after.
NFCI_VINTAGES = {
    "NFCI_2011-06-20.csv": [("2011-06-10", "-0.20"), ("2011-06-17", "-0.18")],
    "NFCI_2015-01-09.csv": [("2015-01-02", "-0.65"), ("2015-01-09", "-0.66"),
                            ("2010-01-08", "-0.10")],
    "NFCI_2025-01-03.csv": [("2025-01-03", "-0.40")],  # out of deep window
}
NFCI_IN_WINDOW_ROWS = 2 + 3  # only the two in-window files' data cells land


def _write_nfci_corpus(dirpath, vintages=None):
    vintages = vintages if vintages is not None else NFCI_VINTAGES
    paths = []
    for name, rows in vintages.items():
        base, vintage = name[:-4].split("_")
        col = "%s_%s" % (base, vintage.replace("-", ""))
        text = "observation_date,%s\n" % col
        text += "".join("%s,%s\n" % (d, v) for d, v in rows)
        p = Path(dirpath) / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return paths


def _deep_source(base="NFCI", suffix=""):
    return {
        "adapter": "fred_json_api_vintages_deep",
        "allowed_hosts": ["api.stlouisfed.org"],
        "coverage_source_ids": ["alfred_fred_vintages"],
        "enabled": True,
        "endpoint": (
            "https://api.stlouisfed.org/fred/series/observations?series_id=%s"
            "&file_type=json&output_type=2&realtime_start=2000-01-01"
            "&realtime_end=2019-12-31" % base
        ),
        "expected_content_types": ["application/json"],
        "frequency": "weekly",
        "information_set_mode": "archive_snapshot_asof",
        "label": "%s (ALFRED reconstructed vintage matrix) [DEEP 2000-2019]" % base,
        "max_bytes": 33554432,
        "method_version": "fred_%s_api_vintages_deep%s.v1" % (base.lower(), suffix),
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Bank of St. Louis provider (ALFRED)",
        "publisher_release_clock": "provider vintage availability is series-specific",
        "rights_status": "FRED_terms_and_underlying_publisher_rights_control",
        "secret_env": "FRED_API_KEY",
        "secret_required": True,
        "series": {
            "label": "National Financial Conditions Index",
            "series_id": base,
            "unit": "Index",
        },
        "source_id": "fred_%s_api_vintages_deep%s" % (base.lower(), suffix),
        "value_status": "actual",
    }


def _registry(root):
    text = (
        "source_id,access_class,coverage,frequency,primary_url,publisher,"
        "rights_status,typical_release_or_availability\n"
        "nyfed_reference_rates,A,current,current,"
        "https://markets.newyorkfed.org,New York Fed,public,daily\n"
        "alfred_fred_vintages,B,current,monthly,https://alfred.stlouisfed.org,"
        "Federal Reserve Bank of St. Louis,public,irregular\n"
    )
    (Path(root) / "registry.csv").write_text(text, encoding="utf-8")
    catalog = Path(root) / "data_vault" / "catalog"
    catalog.mkdir(parents=True, exist_ok=True)
    header = (
        "schema_version,source_id,family,publisher,measure,frequency,coverage,"
        "typical_release_or_availability,revision_and_vintage_behavior,role,"
        "access_class,rights_status,primary_url,notes\n"
    )
    rows = (
        "recession-monitor-v2.external-source-registry.v1,nyfed_reference_rates,"
        "funding,New_York_Fed,SOFR,daily,SOFR_2018+,SOFR_0800_ET,"
        "thresholded_revisions,construction_candidate,A,NY_Fed_terms,"
        "https://www.newyorkfed.org/markets/reference-rates,\n"
        "recession-monitor-v2.external-source-registry.v1,alfred_fred_vintages,"
        "provider_vintage,Federal_Reserve_Bank_of_St_Louis,provider_snapshots,"
        "series_specific,series_specific,API_availability,provider_vintages,"
        "discovery_and_provider_reconstruction,B,"
        "underlying_publisher_rights_still_control,"
        "https://fred.stlouisfed.org/docs/api/fred/realtime_period.html,\n"
    )
    (catalog / "external_source_registry.csv").write_text(
        header + rows, encoding="utf-8")


def _nyfed_source():
    return {
        "adapter": "nyfed_reference_rate_json",
        "allowed_hosts": ["markets.newyorkfed.org"],
        "coverage_source_ids": ["nyfed_reference_rates"],
        "enabled": True,
        "endpoint": "https://markets.newyorkfed.org/example.json",
        "expected_content_types": ["application/json"],
        "frequency": "daily_business_day",
        "information_set_mode": "current_revised",
        "label": "NY Fed reference rates",
        "max_bytes": 100000,
        "method_version": "nyfed_reference_rate_json.v1",
        "poll_seconds": 300,
        "publisher": "New York Fed",
        "publisher_release_clock": "publisher clock",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {},
        "source_id": "nyfed_reference_rates",
        "value_status": "actual",
    }


def _config(sources):
    return {
        "api": {"host": "127.0.0.1", "port": 8792, "website_poll_seconds": 60},
        "catalog_registry": "registry.csv",
        "schema_version": "recession-monitor-v2.live-data-config.v1",
        "service": {"refresh_tick_seconds": 60},
        "sources": list(sources),
        "store": {"public": "public", "root": "store", "runtime": "runtime"},
    }


def _nyfed_body():
    return canonical_json_bytes({
        "refRates": [{
            "effectiveDate": "2026-07-28",
            "percentRate": "3.65",
            "revisionIndicator": "",
            "type": "SOFR",
            "volumeInBillions": "2100",
        }],
    })


class SeedHttpClient(object):
    def __init__(self):
        self.calls = []

    def fetch(self, source, now=None, conditional_headers=None):
        self.calls.append(source["source_id"])
        return HttpResponse(
            source["endpoint"], 200,
            {"content-type": "application/json", "etag": '"seed"'},
            _nyfed_body(), request_headers=conditional_headers,
        )


class ExplodingHttpClient(object):
    def fetch(self, *args, **kwargs):
        raise AssertionError("offline binding attempted a network fetch")


def _seed_generation(root):
    _registry(root)
    config = _config([_nyfed_source()])
    pipeline = RefreshPipeline(root, config, SeedHttpClient())
    pipeline.refresh()
    return config, pipeline


class OfflineBindingBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config, self.pipeline = _seed_generation(self.root)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        self.csv_paths = _write_nfci_corpus(self.corpus)

    def tearDown(self):
        self.temp.cleanup()

    def _bind_nfci(self):
        source = _deep_source()
        outcome = bind_offline_vintage(
            self.pipeline, source, self.csv_paths, AS_OF,
        )
        return source, outcome


class V1UnchangedTests(OfflineBindingBase):
    def test_live_v1_binding_still_verifies(self):
        head = self.pipeline.store.read_source_head("nyfed_reference_rates")
        binding = source_binding_from_head("nyfed_reference_rates", head)
        evidence = self.pipeline.store.verify_source_binding(binding)
        self.assertEqual(
            evidence["receipt"]["schema_version"],
            "recession-monitor-v2.acquisition-receipt.v1",
        )

    def test_live_v1_receipt_missing_field_still_fails(self):
        # (c) — the v1 closed schema is intact: drop a required field, re-store,
        # rebind, and the closure must still reject it.
        head = self.pipeline.store.read_source_head("nyfed_reference_rates")
        binding = source_binding_from_head("nyfed_reference_rates", head)
        receipt = self.pipeline.store.verify_source_binding(binding)["receipt"]
        broken = dict(receipt)
        del broken["rights_status"]
        digest, _ = self.pipeline.store.store_receipt(
            "nyfed_reference_rates", broken)
        tampered = dict(binding)
        tampered["receipt_sha256"] = digest
        with self.assertRaises(CanonicalDataError):
            self.pipeline.store.verify_source_binding(tampered)


class OfflineAcceptedTests(OfflineBindingBase):
    def test_offline_binding_verifies_generic_and_strict(self):
        source, outcome = self._bind_nfci()
        self.assertEqual(outcome["record_count"], NFCI_IN_WINDOW_ROWS)
        head = self.pipeline.store.read_source_head(source["source_id"])
        self.assertIsNotNone(head)
        binding = source_binding_from_head(source["source_id"], head)
        evidence = self.pipeline.store.verify_source_binding(binding)
        self.assertEqual(
            evidence["receipt"]["schema_version"],
            OFFLINE_ACQUISITION_RECEIPT_SCHEMA,
        )
        # strict offline verify accepts the offline receipt
        self.pipeline.store.verify_offline_source_binding(binding)
        # source head carries no http validators
        self.assertIsNone(head["etag"])
        self.assertIsNone(head["last_modified"])

    def test_offline_zero_network(self):
        self.pipeline.http_client = ExplodingHttpClient()
        _, outcome = self._bind_nfci()
        self.assertEqual(outcome["record_count"], NFCI_IN_WINDOW_ROWS)


class OfflinePublishRoundTripTests(OfflineBindingBase):
    def test_publish_generation_reverifies_offline_binding(self):
        source, outcome = self._bind_nfci()
        # admit the source into the active config, then publish a generation
        # over all runtime heads (nyfed live + NFCI offline).
        self.pipeline.config["sources"].append(source)
        snapshot = self.pipeline.build_snapshot(ATTEMPTED_AT)
        coverage = self.pipeline.build_coverage(ATTEMPTED_AT)
        status = self.pipeline.build_status(
            ATTEMPTED_AT, [], snapshot, coverage)
        status["source_matrix"] = {
            "csv_bytes": 0, "csv_sha256": "0" * 64,
            "definition_sha256": "0" * 64, "json_bytes": 0,
            "json_sha256": "0" * 64, "row_count": 0,
        }
        self.pipeline.store.publish_generation(snapshot, status, coverage)
        # full-closure re-authentication (attest_bindings=False) accepts the
        # offline binding alongside the live one.
        generation = read_verified_generation(
            self.pipeline.store.public,
            self.pipeline.store.root / "generations",
            materialize_members=("snapshot.json",),
        )
        bound_ids = {
            s["source_id"]
            for s in generation["members"]["snapshot.json"]["sources"]
        }
        self.assertIn(source["source_id"], bound_ids)
        self.assertIn("nyfed_reference_rates", bound_ids)

    def test_round_trip_landed_equals_in_window_cells(self):
        _, outcome = self._bind_nfci()
        # only the two in-window vintage files' data cells land.
        self.assertEqual(outcome["record_count"], NFCI_IN_WINDOW_ROWS)
        self.assertEqual(outcome["files_bound"], 3)  # all fed files recorded
        # every landed series id is on the .DEEPASOF family.
        for series_id in outcome["landed_series"]:
            self.assertIn(".DEEPASOF", series_id)


class OfflineReceiptFailCaseTests(OfflineBindingBase):
    def _offline_binding_with_receipt(self, mutate):
        """Bind NFCI, then replace its receipt with a mutated one and return the
        rebound binding pointing at the mutated receipt."""
        source, outcome = self._bind_nfci()
        head = self.pipeline.store.read_source_head(source["source_id"])
        binding = source_binding_from_head(source["source_id"], head)
        receipt = self.pipeline.store.verify_source_binding(binding)["receipt"]
        mutated = mutate(dict(receipt))
        digest, _ = self.pipeline.store.store_receipt(
            source["source_id"], mutated)
        rebound = dict(binding)
        rebound["receipt_sha256"] = digest
        return rebound

    def test_offline_missing_per_file_source_sha_fails(self):
        # (a)
        def mutate(receipt):
            files = [dict(f) for f in receipt["source_files"]]
            del files[0]["source_sha256"]
            receipt["source_files"] = files
            return receipt
        rebound = self._offline_binding_with_receipt(mutate)
        with self.assertRaises(CanonicalDataError):
            self.pipeline.store.verify_source_binding(rebound)

    def test_offline_carrying_http_field_fails(self):
        # (b)
        def mutate(receipt):
            receipt["response"] = {
                "content_length": 1, "content_type": "application/json",
                "etag": None, "last_modified": None, "status": 200,
            }
            return receipt
        rebound = self._offline_binding_with_receipt(mutate)
        with self.assertRaises(CanonicalDataError):
            self.pipeline.store.verify_source_binding(rebound)


class FabricatedLiveReceiptTests(OfflineBindingBase):
    def test_fabricated_live_receipt_for_offline_object_fails_strict(self):
        # (d) — a structurally valid v1 http receipt is fabricated for the
        # offline object (correct hashes, plausible http blocks). The generic
        # verify would accept its shape, but the STRICT offline verify rejects
        # it: an offline binding must carry the offline receipt schema.
        source, outcome = self._bind_nfci()
        head = self.pipeline.store.read_source_head(source["source_id"])
        binding = source_binding_from_head(source["source_id"], head)
        source_object_len = outcome["source_bytes_length"]
        fabricated = {
            "clocks": {
                "provider_available_at": AS_OF,
                "publisher_released_at": None,
                "retrieved_at": binding["retrieved_at"],
                "validated_at": binding["retrieved_at"],
            },
            "information_set_mode": "archive_snapshot_asof",
            "normalized_sha256": binding["normalized_sha256"],
            "outcome": "retrieved_and_validated",
            "predecessor_receipt_sha256": None,
            "publisher": source["publisher"],
            "request": {
                "body_sha256": None,
                "conditional_headers": {},
                "method": "GET",
                "parameters": {},
                "url": source["endpoint"],
            },
            "response": {
                "content_length": source_object_len,
                "content_type": "application/json",
                "etag": None,
                "last_modified": None,
                "status": 200,
            },
            "rights_status": source["rights_status"],
            "schema_version": "recession-monitor-v2.acquisition-receipt.v1",
            "source_bytes_sha256": binding["source_bytes_sha256"],
            "source_id": source["source_id"],
        }
        digest, _ = self.pipeline.store.store_receipt(
            source["source_id"], fabricated)
        rebound = dict(binding)
        rebound["receipt_sha256"] = digest
        # the fabricated v1 receipt is structurally valid (generic accepts it)…
        self.pipeline.store.verify_source_binding(rebound)
        # …but the strict offline verify rejects the kind mismatch.
        with self.assertRaises(CanonicalDataError):
            self.pipeline.store.verify_offline_source_binding(rebound)


class OfflineProvenanceReceiptSchemaTests(unittest.TestCase):
    """build_offline_receipt is the single provenance home: refuse a record that
    is missing a per-file source sha or the transcoder version."""

    def _files(self):
        return [
            {"base": "NFCI", "vintage": "20110620",
             "source_path": "/vault/NFCI_2011-06-20.csv",
             "source_sha256": "b" * 64, "row_count": 2},
        ]

    def test_build_offline_receipt_is_offline_kind_no_http(self):
        receipt = build_offline_receipt(
            source=_deep_source(), source_bytes_sha256="c" * 64,
            normalized_sha256="d" * 64, file_provenance=self._files(),
            response_schema_sha256="a" * 64, source_bytes_length=42,
            as_of=AS_OF, predecessor_receipt_sha256=None,
        )
        self.assertEqual(
            receipt["schema_version"], OFFLINE_ACQUISITION_RECEIPT_SCHEMA)
        self.assertEqual(
            receipt["acquisition_kind"], "offline_vintage_admission")
        self.assertNotIn("request", receipt)
        self.assertNotIn("response", receipt)
        self.assertEqual(
            receipt["transcoder"]["parser_version"],
            vct.TRANSCODER_PARSER_VERSION,
        )


class AppendOnlyGateReproofTests(OfflineBindingBase):
    def test_second_same_base_deep_candidate_is_rejected(self):
        # bind + admit NFCI, publish a generation so its .DEEPASOF family is
        # active, then a second deep candidate for the SAME base (different
        # source_id) must red-bar on the append-only family-prefix gate.
        source, _ = self._bind_nfci()
        self.pipeline.config["sources"].append(source)
        snapshot = self.pipeline.build_snapshot(ATTEMPTED_AT)
        coverage = self.pipeline.build_coverage(ATTEMPTED_AT)
        status = self.pipeline.build_status(
            ATTEMPTED_AT, [], snapshot, coverage)
        status["source_matrix"] = {
            "csv_bytes": 0, "csv_sha256": "0" * 64,
            "definition_sha256": "0" * 64, "json_bytes": 0,
            "json_sha256": "0" * 64, "row_count": 0,
        }
        self.pipeline.store.publish_generation(snapshot, status, coverage)
        second = _deep_source(suffix="_dup")  # same base NFCI, new source_id
        with self.assertRaises(feed_factory.CanonicalDataError):
            feed_factory._validate_source_candidate(
                self.pipeline.project_root, self.pipeline.config, second)

    def test_second_provider_tagged_deep_candidate_is_accepted(self):
        # B-LAND-3D: after ALFRED's NFCI .DEEPASOF family is active, a SECOND
        # provider's deep candidate for the SAME base carrying a provider tag is
        # admissible (one-per-base-PER-PROVIDER). Its family prefix is
        # NFCI.<TAG>.DEEPASOF, disjoint from the primary NFCI.DEEPASOF family.
        source, _ = self._bind_nfci()
        self.pipeline.config["sources"].append(source)
        snapshot = self.pipeline.build_snapshot(ATTEMPTED_AT)
        coverage = self.pipeline.build_coverage(ATTEMPTED_AT)
        status = self.pipeline.build_status(
            ATTEMPTED_AT, [], snapshot, coverage)
        status["source_matrix"] = {
            "csv_bytes": 0, "csv_sha256": "0" * 64,
            "definition_sha256": "0" * 64, "json_bytes": 0,
            "json_sha256": "0" * 64, "row_count": 0,
        }
        self.pipeline.store.publish_generation(snapshot, status, coverage)
        second = _deep_source(suffix="_fredmd")  # same base NFCI, new source_id
        second["vintage_provider_tag"] = "FREDMD"
        candidate = feed_factory._validate_source_candidate(
            self.pipeline.project_root, self.pipeline.config, second)
        self.assertIn(second, candidate["sources"])

    def test_same_provider_tag_duplicate_still_rejected(self):
        # A duplicate of the SAME provider-tagged lane (same base, same tag)
        # must still red-bar: the tag scopes the gate per provider, it does not
        # disable it.
        source, _ = self._bind_nfci()
        first = _deep_source(suffix="_fredmd")
        first["vintage_provider_tag"] = "FREDMD"
        bind_offline_vintage(
            self.pipeline, first, self.csv_paths, AS_OF,
        )
        self.pipeline.config["sources"].append(source)
        self.pipeline.config["sources"].append(first)
        snapshot = self.pipeline.build_snapshot(ATTEMPTED_AT)
        coverage = self.pipeline.build_coverage(ATTEMPTED_AT)
        status = self.pipeline.build_status(
            ATTEMPTED_AT, [], snapshot, coverage)
        status["source_matrix"] = {
            "csv_bytes": 0, "csv_sha256": "0" * 64,
            "definition_sha256": "0" * 64, "json_bytes": 0,
            "json_sha256": "0" * 64, "row_count": 0,
        }
        self.pipeline.store.publish_generation(snapshot, status, coverage)
        dup = _deep_source(suffix="_fredmd2")
        dup["vintage_provider_tag"] = "FREDMD"
        with self.assertRaises(feed_factory.CanonicalDataError):
            feed_factory._validate_source_candidate(
                self.pipeline.project_root, self.pipeline.config, dup)


from live_data.rmv2_live import fredmd_panel  # noqa: E402


def _write_fredmd_panels(dirpath):
    """Two FRED-MD panels: a pre-2000 vintage (dropped by the deep gate) and an
    in-window 2001 vintage. Multi-series so the base-column selection is real."""
    panels = {
        "1999-08.csv": (
            "sasdate,RPI,W875RX1,CLAIMSx\n"
            "Transform:,5,5,5\n"
            "01/01/1999,1000.0,900.0,300.0\n"
        ),
        "2001-06.csv": (
            "sasdate,RPI,W875RX1,CLAIMSx\n"
            "Transform:,5,5,5\n"
            "01/01/1999,1000.2,900.2,300.2\n"
            "01/01/2001,1100.0,950.0,320.0\n"
        ),
    }
    paths = []
    for name, text in panels.items():
        p = Path(dirpath) / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return sorted(paths)


class FredmdPanelBindingTests(OfflineBindingBase):
    """B-LAND-3C-R2: the FRED-MD panel transcoder binds through the SAME
    offline binder + proven deep parser, tracing provenance to original panels
    and recording the fredmd parser_version in the offline receipt."""

    def _panel_source(self, base):
        source = _deep_source(base=base, suffix="_fredmd")
        # panels are named-file archival monthly releases (nominal HTTPS endpoint;
        # archival is never fetched). The base id may be a FRED-MD NEAR construct.
        source["method_version"] = "fred_%s_fredmd_panel_deep.v1" % base.lower()
        return source

    def test_fredmd_panel_binds_and_records_its_transcoder(self):
        panels = _write_fredmd_panels(self.root / "corpus")
        source = self._panel_source("W875RX1")
        outcome = bind_offline_vintage(
            self.pipeline, source, panels, AS_OF, transcoder=fredmd_panel,
        )
        # DEFINITION CHANGE (B-LAND-5-R2, owner-ruled 2026-08-06): deep floor
        # widened below 2000, so BOTH the 1999-08 and 2001-06 vintages survive.
        # 2001-06 carries two dated cells (1999-01 + 2001-01) = 2 records;
        # 1999-08 carries only the 1999-01 cell (2001-01 not yet existent) = 1;
        # total 3. See deep_vintage_window.v1.json.
        self.assertEqual(outcome["record_count"], 3)
        self.assertEqual(
            set(outcome["landed_series"]),
            {"W875RX1.DEEPASOF19990801", "W875RX1.DEEPASOF20010601"})
        head = self.pipeline.store.read_source_head(source["source_id"])
        binding = source_binding_from_head(source["source_id"], head)
        receipt = self.pipeline.store.verify_offline_source_binding(binding)
        self.assertIn(
            "fredmd_panel",
            receipt["receipt"]["transcoder"]["parser_version"],
        )
        # provenance traces the ORIGINAL panel files (not derived CSVs)
        source_files = receipt["receipt"]["source_files"]
        self.assertTrue(
            all(f["source_path"].endswith(".csv") for f in source_files))
        self.assertEqual({f["base"] for f in source_files}, {"W875RX1"})

    def test_fredmd_panel_zero_network(self):
        panels = _write_fredmd_panels(self.root / "corpus")
        self.pipeline.http_client = ExplodingHttpClient()
        source = self._panel_source("CLAIMSx")
        outcome = bind_offline_vintage(
            self.pipeline, source, panels, AS_OF, transcoder=fredmd_panel,
        )
        # CLAIMSx keeps its OWN suffixed id (NEAR class) -- never aliased to ICSA.
        # DEFINITION CHANGE (B-LAND-5-R2, owner-ruled 2026-08-06): deep floor
        # widened below 2000, so the 1999-08 vintage is now admitted too.
        self.assertEqual(
            set(outcome["landed_series"]),
            {"CLAIMSx.DEEPASOF19990801", "CLAIMSx.DEEPASOF20010601"})


if __name__ == "__main__":
    unittest.main()
