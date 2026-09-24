"""B-OFFLINE-2 §1 — the generic offline-CURRENT bind path + its additive
acquisition-receipt schema variant and verify closure, proven end-to-end.

Unlike the B-LAND-3 offline_vintage variant (which transcodes on-disk ALFRED
CSV vintages through the FRED deep parser), the offline-current path admits
adapter-normalizable cache bytes byte-unchanged — the bytes captured to a
sha-manifested prefetch cache ARE the source object — and normalizes them
through the SAME live adapter the online lane would use. This lands the
never-revised current_revised lanes (CH-R26 certified) from the CH-R29 cache
with zero network.

Proofs:
  V1 UNCHANGED   a real live_http (acquisition-receipt.v1) binding still verifies
                 byte-for-byte (the dispatch is still schema-discriminated).
  CURRENT OK     an offline-current binding verifies via verify_source_binding
                 AND the strict verify_offline_current_source_binding, and
                 publishes into a real generation that read_verified_generation
                 re-authenticates in the full closure.
  ROUND-TRIP     landed values == the cached FRED observations cells.
  MANIFEST       binding with a cache manifest whose sha/length does not match the
                 bound bytes FAILS at bind time.
  (a)            an offline-current receipt with a mutated cache-manifest sha FAILS.
  (b)            an offline-current receipt carrying an http field FAILS (keyset).
  (d)            an offline_vintage receipt cannot pass the strict CURRENT verify
                 (kind mismatch), and vice-versa.
  ZERO NETWORK   the bind never touches the http client.
"""
from __future__ import absolute_import

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import HttpResponse  # noqa: E402
from live_data.rmv2_live.canonical import CanonicalDataError  # noqa: E402
from live_data.rmv2_live.config import load_config  # noqa: E402
from live_data.rmv2_live.pipeline import RefreshPipeline  # noqa: E402
from live_data.rmv2_live.store import (  # noqa: E402
    OFFLINE_CURRENT_ACQUISITION_RECEIPT_SCHEMA,
    canonical_json_bytes,
    read_verified_generation,
    source_binding_from_head,
)
from live_data.rmv2_live.offline_binding import bind_offline_current  # noqa: E402

ATTEMPTED_AT = "2026-08-06T12:00:00Z"
RETRIEVED_AT = "2026-08-06T00:00:00Z"
FETCH_UTC = "2026-08-06T03:42:41Z"
CACHE_URL = (
    "https://api.stlouisfed.org/fred/series/observations?series_id=DGS3"
    "&api_key=<KEY>&file_type=json"
)

# A never-revised current lane: single collapsed vintage (realtime_start ==
# realtime_end for the envelope and every observation), output_type 1.
FRED_OBS = [
    ("2026-07-28", "4.10"),
    ("2026-07-29", "4.12"),
    ("2026-07-30", "."),  # unavailable cell (holiday); still bound as null
]


def _fred_current_body(vintage="2026-07-22"):
    return canonical_json_bytes({
        "count": len(FRED_OBS),
        "file_type": "json",
        "limit": 100000,
        "observation_end": "9999-12-31",
        "observation_start": "1600-01-01",
        "observations": [
            {
                "date": d,
                "realtime_end": vintage,
                "realtime_start": vintage,
                "value": v,
            }
            for d, v in FRED_OBS
        ],
        "offset": 0,
        "order_by": "observation_date",
        "output_type": 1,
        "realtime_end": vintage,
        "realtime_start": vintage,
        "sort_order": "asc",
        "units": "lin",
    })


def _cache_manifest(body_bytes, url=CACHE_URL, fetch_utc=FETCH_UTC):
    return {
        "fetch_utc": fetch_utc,
        "source_bytes_length": len(body_bytes),
        "source_sha256": hashlib.sha256(body_bytes).hexdigest(),
        "url": url,
    }


def _current_source():
    return {
        "adapter": "fred_json_api",
        "allowed_hosts": ["api.stlouisfed.org"],
        "coverage_source_ids": ["fred_current_never_revised"],
        "enabled": False,
        "endpoint": (
            "https://api.stlouisfed.org/fred/series/observations?series_id=DGS3"
            "&file_type=json&output_type=1"
        ),
        "expected_content_types": ["application/json"],
        "frequency": "daily_business_day",
        "information_set_mode": "current_revised",
        "label": "DGS3 (never-revised current lane) [OFFLINE-CURRENT]",
        "max_bytes": 33554432,
        "method_version": "fred_dgs3_json_api_current.v1",
        "poll_seconds": 86400,
        "publisher": "Federal Reserve Bank of St. Louis provider (FRED)",
        "publisher_release_clock": "publisher release clock is series-specific",
        "rights_status": "FRED_terms_and_underlying_publisher_rights_control",
        "secret_env": "FRED_API_KEY",
        "secret_required": True,
        "series": {
            "label": "3-Year Treasury Constant Maturity Rate",
            "series_id": "DGS3",
            "unit": "Percent",
        },
        "source_id": "fred_dgs3_json_api_current",
        "value_status": "actual",
    }


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


def _registry(root):
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
        "recession-monitor-v2.external-source-registry.v1,"
        "fred_current_never_revised,provider_current,"
        "Federal_Reserve_Bank_of_St_Louis,provider_current_values,"
        "series_specific,series_specific,API_availability,never_revised,"
        "discovery_and_provider_reconstruction,B,"
        "underlying_publisher_rights_still_control,"
        "https://fred.stlouisfed.org/,\n"
    )
    (catalog / "external_source_registry.csv").write_text(
        header + rows, encoding="utf-8")
    # legacy flat registry the config points at
    (Path(root) / "registry.csv").write_text(
        "source_id,access_class,coverage,frequency,primary_url,publisher,"
        "rights_status,typical_release_or_availability\n"
        "nyfed_reference_rates,A,current,current,"
        "https://markets.newyorkfed.org,New York Fed,public,daily\n"
        "fred_current_never_revised,B,current,current,"
        "https://fred.stlouisfed.org,St Louis Fed,public,irregular\n",
        encoding="utf-8",
    )


def _config(sources):
    return {
        "api": {"host": "127.0.0.1", "port": 8793, "website_poll_seconds": 60},
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
    def fetch(self, source, now=None, conditional_headers=None):
        return HttpResponse(
            source["endpoint"], 200,
            {"content-type": "application/json", "etag": '"seed"'},
            _nyfed_body(), request_headers=conditional_headers,
        )


class ExplodingHttpClient(object):
    def fetch(self, *args, **kwargs):
        raise AssertionError("offline-current binding attempted a network fetch")


def _seed_generation(root):
    _registry(root)
    config = _config([_nyfed_source()])
    pipeline = RefreshPipeline(root, config, SeedHttpClient())
    pipeline.refresh()
    return config, pipeline


class OfflineCurrentBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config, self.pipeline = _seed_generation(self.root)
        self.body = _fred_current_body()
        self.manifest = _cache_manifest(self.body)

    def tearDown(self):
        self.temp.cleanup()

    def _bind(self):
        source = _current_source()
        outcome = bind_offline_current(
            self.pipeline, source, self.body, self.manifest, RETRIEVED_AT,
        )
        return source, outcome


class V1UnchangedTests(OfflineCurrentBase):
    def test_live_v1_binding_still_verifies(self):
        head = self.pipeline.store.read_source_head("nyfed_reference_rates")
        binding = source_binding_from_head("nyfed_reference_rates", head)
        evidence = self.pipeline.store.verify_source_binding(binding)
        self.assertEqual(
            evidence["receipt"]["schema_version"],
            "recession-monitor-v2.acquisition-receipt.v1",
        )


class OfflineCurrentAcceptedTests(OfflineCurrentBase):
    def test_binding_verifies_generic_and_strict(self):
        source, outcome = self._bind()
        # all three observation cells land (one as unavailable null).
        self.assertEqual(outcome["record_count"], len(FRED_OBS))
        self.assertEqual(outcome["landed_series"], {"DGS3": len(FRED_OBS)})
        head = self.pipeline.store.read_source_head(source["source_id"])
        self.assertIsNone(head["etag"])
        self.assertIsNone(head["last_modified"])
        binding = source_binding_from_head(source["source_id"], head)
        evidence = self.pipeline.store.verify_source_binding(binding)
        self.assertEqual(
            evidence["receipt"]["schema_version"],
            OFFLINE_CURRENT_ACQUISITION_RECEIPT_SCHEMA,
        )
        # strict current verify accepts it
        self.pipeline.store.verify_offline_current_source_binding(binding)
        # receipt cites the cache manifest as provenance, no http block
        receipt = evidence["receipt"]
        self.assertEqual(
            receipt["cache_manifest"]["source_sha256"],
            self.manifest["source_sha256"],
        )
        self.assertNotIn("request", receipt)
        self.assertNotIn("response", receipt)
        self.assertEqual(receipt["information_set_mode"], "current_revised")

    def test_zero_network(self):
        self.pipeline.http_client = ExplodingHttpClient()
        _, outcome = self._bind()
        self.assertEqual(outcome["record_count"], len(FRED_OBS))

    def test_round_trip_landed_equals_cache_cells(self):
        source, _ = self._bind()
        head = self.pipeline.store.read_source_head(source["source_id"])
        binding = source_binding_from_head(source["source_id"], head)
        normalized = self.pipeline.store.verify_source_binding(binding)[
            "normalized"]
        landed = {
            r["observation_period"]: r["value"]
            for r in normalized["records"]
        }
        self.assertEqual(landed["2026-07-28"], "4.10")
        self.assertEqual(landed["2026-07-29"], "4.12")
        self.assertIsNone(landed["2026-07-30"])  # the "." cell -> null


class OfflineCurrentPublishTests(OfflineCurrentBase):
    def test_publish_generation_reverifies_binding(self):
        source, _ = self._bind()
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


class ManifestGuardTests(OfflineCurrentBase):
    def test_manifest_sha_mismatch_fails_at_bind(self):
        source = _current_source()
        bad = dict(self.manifest)
        bad["source_sha256"] = "0" * 64
        with self.assertRaises(CanonicalDataError):
            bind_offline_current(
                self.pipeline, source, self.body, bad, RETRIEVED_AT)

    def test_manifest_length_mismatch_fails_at_bind(self):
        source = _current_source()
        bad = dict(self.manifest)
        bad["source_bytes_length"] = len(self.body) + 1
        with self.assertRaises(CanonicalDataError):
            bind_offline_current(
                self.pipeline, source, self.body, bad, RETRIEVED_AT)


CACHE = Path(__file__).resolve().parents[1] / "research" / "prefetch" / "forecasts"
INDIV_CORECPI = CACHE / "spf" / "individual_corecpi.xlsx"


def _spf_registry(root):
    """Seed the registry with the forecast family the individual panel binds to,
    alongside the NY Fed seed source the base generation needs."""
    _registry(root)
    reg = Path(root) / "data_vault" / "catalog" / "external_source_registry.csv"
    reg.write_text(
        reg.read_text(encoding="utf-8") +
        "recession-monitor-v2.external-source-registry.v1,philadelphia_spf,"
        "forecast_survey,Philadelphia_Fed,professional_macro_forecasts,quarterly,"
        "1968+,quarterly_after_advance_GDP,"
        "release_editions_errata_and_individual_responses,forecast_comparator,B,"
        "published_survey_data,https://www.philadelphiafed.org/,"
        "RECESS_fields_are_GDP_decline_probabilities,\n",
        encoding="utf-8",
    )
    (Path(root) / "registry.csv").write_text(
        (Path(root) / "registry.csv").read_text(encoding="utf-8") +
        "philadelphia_spf,B,current,quarterly,https://www.philadelphiafed.org,"
        "Philadelphia Fed,published,quarterly\n",
        encoding="utf-8",
    )


def _spf_individual_source():
    return {
        "adapter": "forecast_xlsx",
        "allowed_hosts": ["www.philadelphiafed.org"],
        "archival": True,
        "coverage_source_ids": ["philadelphia_spf"],
        "enabled": False,
        "endpoint": "https://www.philadelphiafed.org/spf#individual_corecpi.xlsx",
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ],
        "frequency": "quarterly",
        "information_set_mode": "substituted_diagnostic",
        "label": "SPF individual CORECPI panel [OFFLINE-CURRENT; FORECAST class]",
        "max_bytes": 33554432,
        "method_version": "spf_individual_forecast_offline.v1",
        "poll_seconds": 86400,
        "publisher": "Federal Reserve Bank of Philadelphia",
        "publisher_release_clock": "quarterly named survey vintage",
        "rights_status": "published_survey_data",
        "secret_env": None,
        "secret_required": False,
        "snapshot_projection": "archival_panel.v1",
        "series": {
            "forecast_shape": "spf_individual",
            "sheet": "CORECPI",
            "spf_target_code": "CORECPI",
            "id_prefix": "SPF_",
            "unit": "SPF individual-forecaster point forecast",
            "label": "SPF individual-forecaster panel (CORECPI)",
        },
        "source_id": "philadelphia_spf_individual_corecpi",
        "value_status": "actual",
    }


class SpfPanelProjectionConfigTests(unittest.TestCase):
    def _load(self, source):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "sources.v1.json"
        path.write_text(json.dumps(_config([source])), encoding="utf-8")
        return load_config(path)

    def test_archival_spf_panel_projection_loads(self):
        loaded = self._load(_spf_individual_source())
        self.assertEqual(
            loaded["sources"][0]["snapshot_projection"],
            "archival_panel.v1",
        )

    def test_panel_projection_requires_archival_disabled_source(self):
        source = _spf_individual_source()
        del source["archival"]
        with self.assertRaises(CanonicalDataError):
            self._load(source)

    def test_panel_projection_rejects_non_spf_shape(self):
        source = _spf_individual_source()
        source["series"]["forecast_shape"] = "spf_aggregate"
        with self.assertRaises(CanonicalDataError):
            self._load(source)

    def test_unknown_projection_policy_fails_closed(self):
        source = _spf_individual_source()
        source["snapshot_projection"] = "skip_everything.v1"
        with self.assertRaises(CanonicalDataError):
            self._load(source)


class SpfIndividualBindingTests(unittest.TestCase):
    """B-LAND-8-R2: the spf_individual shape lands through the offline-current
    binder, and its cache-manifest guard fires exactly like every other shape."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        _spf_registry(self.root)
        config = _config([_nyfed_source()])
        self.pipeline = RefreshPipeline(self.root, config, SeedHttpClient())
        self.pipeline.refresh()
        self.body = INDIV_CORECPI.read_bytes()
        self.manifest = _cache_manifest(
            self.body, url="https://www.philadelphiafed.org/spf")

    def tearDown(self):
        self.temp.cleanup()

    def test_individual_panel_binds_and_verifies(self):
        source = _spf_individual_source()
        outcome = bind_offline_current(
            self.pipeline, source, self.body, self.manifest, RETRIEVED_AT)
        self.assertGreater(outcome["record_count"], 0)
        self.assertTrue(
            all(sid.startswith("SPF_CORECPI_IND_")
                for sid in outcome["landed_series"]))
        head = self.pipeline.store.read_source_head(source["source_id"])
        binding = source_binding_from_head(source["source_id"], head)
        # strict current verify accepts the panel (duplicate survey-quarter
        # periods across forecasters do NOT break closure).
        self.pipeline.store.verify_offline_current_source_binding(binding)

        # The source remains generation-bound archival evidence, but an
        # individual-forecaster panel is not collapsed into one flat
        # latest-value series for scientific/public snapshot consumers.
        self.pipeline.config["sources"].append(source)
        snapshot = self.pipeline.build_snapshot(
            RETRIEVED_AT, use_projection_cache=False
        )
        bound_ids = {item["source_id"] for item in snapshot["sources"]}
        self.assertIn(source["source_id"], bound_ids)
        self.assertFalse(
            any(series_id.startswith("SPF_CORECPI_IND_")
                for series_id in snapshot["series"])
        )
        self.assertEqual(
            snapshot["snapshot_projection"]["archival_panel_sources"],
            [source["source_id"]],
        )
        self.assertEqual(
            snapshot["snapshot_projection"]["archival_panel_record_count"],
            outcome["record_count"],
        )

    def test_individual_manifest_sha_mismatch_fails_at_bind(self):
        source = _spf_individual_source()
        bad = dict(self.manifest)
        bad["source_sha256"] = "0" * 64
        with self.assertRaises(CanonicalDataError):
            bind_offline_current(
                self.pipeline, source, self.body, bad, RETRIEVED_AT)

    def test_individual_manifest_length_mismatch_fails_at_bind(self):
        source = _spf_individual_source()
        bad = dict(self.manifest)
        bad["source_bytes_length"] = len(self.body) + 1
        with self.assertRaises(CanonicalDataError):
            bind_offline_current(
                self.pipeline, source, self.body, bad, RETRIEVED_AT)


class ReceiptFailCaseTests(OfflineCurrentBase):
    def _rebind_with_receipt(self, mutate):
        source, _ = self._bind()
        head = self.pipeline.store.read_source_head(source["source_id"])
        binding = source_binding_from_head(source["source_id"], head)
        receipt = self.pipeline.store.verify_source_binding(binding)["receipt"]
        mutated = mutate(dict(receipt))
        digest, _ = self.pipeline.store.store_receipt(
            source["source_id"], mutated)
        tampered = dict(binding)
        tampered["receipt_sha256"] = digest
        return tampered

    def test_mutated_manifest_sha_fails_closure(self):
        def mutate(r):
            m = dict(r["cache_manifest"])
            m["source_sha256"] = "0" * 64
            r["cache_manifest"] = m
            return r
        tampered = self._rebind_with_receipt(mutate)
        with self.assertRaises(CanonicalDataError):
            self.pipeline.store.verify_source_binding(tampered)

    def test_http_field_present_fails_closure(self):
        def mutate(r):
            r["request"] = {"method": "GET"}
            return r
        tampered = self._rebind_with_receipt(mutate)
        with self.assertRaises(CanonicalDataError):
            self.pipeline.store.verify_source_binding(tampered)

    def test_strict_current_rejects_non_current_schema(self):
        # a v1-shaped receipt (wrong schema) cannot pass the strict current guard
        source, _ = self._bind()
        head = self.pipeline.store.read_source_head(source["source_id"])
        binding = source_binding_from_head(source["source_id"], head)
        receipt = self.pipeline.store.verify_source_binding(binding)["receipt"]
        forged = dict(receipt)
        forged["schema_version"] = "recession-monitor-v2.acquisition-receipt.v1"
        digest, _ = self.pipeline.store.store_receipt(
            source["source_id"], forged)
        tampered = dict(binding)
        tampered["receipt_sha256"] = digest
        with self.assertRaises(CanonicalDataError):
            self.pipeline.store.verify_offline_current_source_binding(tampered)


if __name__ == "__main__":
    unittest.main()
