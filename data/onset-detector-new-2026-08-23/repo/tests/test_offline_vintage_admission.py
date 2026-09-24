"""B-LAND-2 §1 — the offline-admission acquisition kind (transport + provenance).

Lands audited on-disk ALFRED vintage CSVs into the live store as the source
OBJECT with a TRUTHFUL, DISTINCT offline provenance record (per-file source
sha256 + transcoder parser_version + emitted response_schema sha256 + as-of
stamp + information-set mode), via ZERO network — the transcoder output body IS
the store object, and the existing deep parser round-trips it.

Scope boundary (measured wall #4, filed as a DECISION blocker): binding the
landed object into a published generation requires the CLOSED acquisition-
receipt.v1 schema (store.verify_source_binding enforces an exact key set with
mandatory http request/response blocks). A truthful offline receipt has no
field there, so binding would demand either a null/synthetic http receipt
(a §1.1 FABRICATION-class defect) or a change to the verify closure (§3
forbids weakening verify). This module therefore stops at honest transport +
provenance and does NOT emit a bound receipt / source head — that is the
owner-adjudicated remainder.

Proofs (owner's five, §1.2), adapted to transport+provenance:
 (a) admission succeeds with valid CSV; the store object is byte-retrievable
     and the offline provenance record is stored and round-trips.
 (b) the provenance schema REFUSES a record missing a source sha or the
     transcoder version.
 (c) the offline path makes ZERO network calls — an exploding http client on
     the existing client seam is never touched.
 (d) the append-only family gate (_validate_source_candidate) still rejects
     collisions; the new kind does not bypass it, and writes nothing on reject.
 (e) the provenance record marks the acquisition kind distinctly from a live
     fetch (no http request/response block; a distinct schema_version) — and
     no source head is bound (the wall).
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
from live_data.rmv2_live.pipeline import RefreshPipeline  # noqa: E402
from live_data.rmv2_live.store import canonical_json_bytes, read_json  # noqa: E402

from live_data.rmv2_live.offline_admission import (  # noqa: E402
    OFFLINE_ACQUISITION_KIND,
    OFFLINE_PROVENANCE_SCHEMA,
    OfflineProvenanceError,
    admit_offline_vintage,
    validate_offline_provenance,
)

ATTEMPTED_AT = "2026-08-05T12:00:00Z"

# NFCI vintages: two in the deep window [2000-01-01, 2019-12-31] + one after
# (2020+, owned by the shallow .ASOF lane -> contributes zero landed rows, but
# is still transcoded so its file provenance is recorded, never silently
# dropped).
NFCI_VINTAGES = {
    "NFCI_2011-06-20.csv": [("2011-06-10", "-0.20"), ("2011-06-17", "-0.18")],
    "NFCI_2015-01-09.csv": [("2015-01-02", "-0.65"), ("2015-01-09", "-0.66"),
                            ("2010-01-08", "-0.10")],
    "NFCI_2025-01-03.csv": [("2025-01-03", "-0.40")],  # out of deep window
}
NFCI_IN_WINDOW_ROWS = 2 + 3  # only the two in-window files' data rows land


def _write_nfci_corpus(dirpath):
    paths = []
    for name, rows in NFCI_VINTAGES.items():
        base, vintage = name[:-4].split("_")
        col = "%s_%s" % (base, vintage.replace("-", ""))
        text = "observation_date,%s\n" % col
        text += "".join("%s,%s\n" % (d, v) for d, v in rows)
        p = Path(dirpath) / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return paths


def _deep_source(base="NFCI", suffix=""):
    """A fully-valid deep-vintage config source (mirrors the six admitted deep
    bases), NOT yet present in the active config — an onboarding candidate."""
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
    # (1) the config catalog registry the refresh/coverage path reads
    text = (
        "source_id,access_class,coverage,frequency,primary_url,publisher,"
        "rights_status,typical_release_or_availability\n"
        "nyfed_reference_rates,A,current,current,"
        "https://markets.newyorkfed.org,New York Fed,public,daily\n"
        "alfred_fred_vintages,B,current,monthly,https://alfred.stlouisfed.org,"
        "Federal Reserve Bank of St. Louis,public,irregular\n"
    )
    (Path(root) / "registry.csv").write_text(text, encoding="utf-8")
    # (2) the data-vault external source registry the append-only family gate
    # (_validate_family_bindings) reads — real rows for the two families used.
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
    """Serves the single nyfed body needed to seed a real active generation so
    the append-only gate can authenticate it. Records every fetch."""

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
    """Any network touch is a test failure."""

    def fetch(self, *args, **kwargs):
        raise AssertionError("offline admission attempted a network fetch")


def _seed_generation(root, extra_sources=()):
    """Publish a real, authenticated active generation from a live-ish refresh,
    so the append-only gate can authenticate it. Returns (config, pipeline)."""
    _registry(root)
    config = _config([_nyfed_source(), *extra_sources])
    pipeline = RefreshPipeline(root, config, SeedHttpClient())
    pipeline.refresh()
    return config, pipeline


class ProvenanceSchemaTests(unittest.TestCase):
    """(b) — the provenance record schema, independent of any store."""

    def _valid(self):
        return {
            "acquisition_kind": OFFLINE_ACQUISITION_KIND,
            "as_of": ATTEMPTED_AT,
            "information_set_mode": "archive_snapshot_asof",
            "record_count": 5,
            "response_schema_sha256": "a" * 64,
            "schema_version": OFFLINE_PROVENANCE_SCHEMA,
            "source_bytes_sha256": "c" * 64,
            "source_files": [
                {"source_path": "/vault/NFCI_2011-06-20.csv",
                 "source_sha256": "b" * 64, "base": "NFCI",
                 "vintage": "20110620", "row_count": 2},
            ],
            "source_id": "fred_nfci_api_vintages_deep",
            "transcoder_parser_version": vct.TRANSCODER_PARSER_VERSION,
        }

    def test_valid_provenance_accepted(self):
        self.assertIsNone(validate_offline_provenance(self._valid()))

    def test_missing_transcoder_version_refused(self):
        record = self._valid()
        del record["transcoder_parser_version"]
        with self.assertRaises(OfflineProvenanceError):
            validate_offline_provenance(record)

    def test_missing_per_file_source_sha_refused(self):
        record = self._valid()
        del record["source_files"][0]["source_sha256"]
        with self.assertRaises(OfflineProvenanceError):
            validate_offline_provenance(record)

    def test_empty_source_files_refused(self):
        record = self._valid()
        record["source_files"] = []
        with self.assertRaises(OfflineProvenanceError):
            validate_offline_provenance(record)


class OfflineAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config, self.pipeline = _seed_generation(self.root)
        self.corpus = Path(self.temp.name) / "corpus"
        self.corpus.mkdir()
        self.csv_paths = _write_nfci_corpus(self.corpus)

    def tearDown(self):
        self.temp.cleanup()

    def test_admission_stores_retrievable_object_and_provenance(self):
        source = _deep_source()
        outcome = admit_offline_vintage(
            self.pipeline, source, self.csv_paths, ATTEMPTED_AT,
        )
        self.assertEqual(outcome["outcome"], "admitted_offline")
        self.assertEqual(outcome["acquisition_kind"], OFFLINE_ACQUISITION_KIND)
        # per-file round-trip: landed observations == in-window data rows
        self.assertEqual(outcome["record_count"], NFCI_IN_WINDOW_ROWS)
        # the transcoder output body IS the store object, byte-retrievable
        digest = outcome["source_bytes_sha256"]
        obj = self.pipeline.store.root / "objects" / "sha256" / digest[:2] / (
            digest + ".bin")
        body, _ = vct.transcode_base(self.csv_paths)
        self.assertEqual(obj.read_bytes(), vct.body_bytes(body))
        # the offline provenance record is stored and round-trips
        prov = read_json(outcome["provenance_path"])
        self.assertIsNone(validate_offline_provenance(prov))
        self.assertEqual(prov["source_bytes_sha256"], digest)
        self.assertEqual(len(prov["source_files"]), 3)  # all three files recorded
        # the wall: nothing was bound (no source head, no fabricated receipt)
        self.assertIsNone(self.pipeline.store.read_source_head(source["source_id"]))

    def test_offline_path_makes_zero_network_calls(self):
        source = _deep_source()
        # swap the seam to a client that fails on any fetch; admission must
        # still succeed -> it never touched the network.
        self.pipeline.http_client = ExplodingHttpClient()
        outcome = admit_offline_vintage(
            self.pipeline, source, self.csv_paths, ATTEMPTED_AT,
        )
        self.assertEqual(outcome["outcome"], "admitted_offline")

    def test_gate_not_bypassed_and_writes_nothing_on_reject(self):
        source = _deep_source()
        # put the candidate id into the active config: the append-only gate's
        # first check must fire and admission must refuse and write nothing.
        config = _config([_nyfed_source(), source])
        pipeline = RefreshPipeline(self.root, config, ExplodingHttpClient())
        objects_before = list(
            (pipeline.store.root / "objects").rglob("*.bin")
        )
        with self.assertRaises(feed_factory.CanonicalDataError):
            admit_offline_vintage(pipeline, source, self.csv_paths, ATTEMPTED_AT)
        self.assertIsNone(pipeline.store.read_source_head(source["source_id"]))
        self.assertEqual(
            list((pipeline.store.root / "objects").rglob("*.bin")),
            objects_before,
        )

    def test_provenance_record_is_distinct_from_a_live_fetch_receipt(self):
        source = _deep_source()
        outcome = admit_offline_vintage(
            self.pipeline, source, self.csv_paths, ATTEMPTED_AT,
        )
        prov = read_json(outcome["provenance_path"])
        # distinct schema + explicit offline kind (never the http acquisition
        # receipt schema); no fabricated http request/response block.
        self.assertEqual(prov["schema_version"], OFFLINE_PROVENANCE_SCHEMA)
        self.assertNotEqual(
            prov["schema_version"], "recession-monitor-v2.acquisition-receipt.v1")
        self.assertEqual(prov["acquisition_kind"], OFFLINE_ACQUISITION_KIND)
        self.assertNotIn("request", prov)
        self.assertNotIn("response", prov)
        # truthful provenance carried: transcoder identity + distinct file shas
        self.assertEqual(
            prov["transcoder_parser_version"], vct.TRANSCODER_PARSER_VERSION)
        shas = {f["source_sha256"] for f in prov["source_files"]}
        self.assertEqual(len(shas), 3)  # three distinct on-disk vintages
        self.assertEqual(prov["information_set_mode"], "archive_snapshot_asof")


if __name__ == "__main__":
    unittest.main()
