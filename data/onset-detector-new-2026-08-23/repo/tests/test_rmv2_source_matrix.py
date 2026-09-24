from __future__ import absolute_import

import copy
import csv
import io
import json
import os
import re
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.canonical import (
    CanonicalDataError,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    strict_json_loads,
)
from live_data.rmv2_live.config import load_config
from live_data.rmv2_live.matrix import (
    MATRIX_FIELDS,
    build_source_matrix,
    write_source_matrix,
)
from live_data.rmv2_live.pipeline import RefreshPipeline


FIXED_TIME = "2026-07-29T12:00:00Z"
CONFIG_PATH = PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"
PLANNED_PATH = (
    PROJECT_ROOT / "live_data" / "config" / "planned_sources.v1.json"
)
REGISTRY_PATH = (
    PROJECT_ROOT / "data_vault" / "catalog" /
    "external_source_registry.csv"
)
ENV_EXAMPLE_PATH = PROJECT_ROOT / "live_data" / "config" / "local.env.example"

PLANNED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "scope",
    "sources",
)
PLANNED_SOURCE_FIELDS = (
    "source_id",
    "registry_status",
    "enabled",
    "publisher",
    "endpoint",
    "endpoint_status",
    "auth_env",
    "cadence",
    "release_timezone",
    "release_clock",
    "observation_period",
    "revision_policy",
    "rights",
    "parser_version",
    "role",
    "clock_notes",
    "split_or_bias_guard",
    "coverage_source_family_ids",
)
REQUIRED_AUTH_ENVS = frozenset((
    "BEA_API_KEY",
    "CENSUS_API_KEY",
    "EIA_API_KEY",
    "FRED_API_KEY",
))
# D0 UNFREEZE THE REGISTRY: the row/reservation counts are no longer pinned to
# hand-typed literals (== 190 / == 134 / == 66 / == 390 / == 53). A hand-typed
# count reds the suite on any legitimate new source, which froze acquisition.
# They are replaced by (a) cross-checks against the actual inputs — a count that
# equals len(config["sources"]) cannot be satisfied by typing a number — and
# (b) never-decrease floors recorded, with provenance:derived, in
# source_registry_growth_floors.v1.json. Growth is allowed; a removed source, a
# renamed id, or a decreased count still reds the suite (proven, D0 §2.4).
GROWTH_FLOORS_PATH = (
    PROJECT_ROOT / "live_data" / "config" /
    "source_registry_growth_floors.v1.json"
)
# Naming contracts (fixed sets, not counts): the only record kinds the matrix
# may emit and the only statuses a planned reservation may carry. A renamed or
# new kind/status reds here — this stays fixed on purpose (D0 §1.2 contract).
ALLOWED_RECORD_KINDS = frozenset((
    "active_collector",
    "registered_source_family",
    "reserved_collector",
))
ALLOWED_RESERVATION_STATUSES = frozenset((
    "RESERVED_CREDENTIAL_BOUND_NOT_ENABLED",
    "RESERVED_LOWER_PRIORITY_NOT_ENABLED",
    "RESERVED_NOT_ENABLED",
))


def _growth_floors():
    return read_json(GROWTH_FLOORS_PATH)

NEW_FREE_SOURCE_FAMILY_IDS = frozenset((
    "atlanta_wage_growth_tracker",
    "bls_bed",
    "bls_laus",
    "bls_mxp",
    "bls_work_stoppages",
    "cdc_provisional_deaths",
    "census_acs",
    "census_bds",
    "census_btos",
    "census_hps_htops",
    "census_qfr",
    "census_qss",
    "census_qtax",
    "census_qwi",
    "census_saipe",
    "cfpb_complaints",
    "cfpb_mortgage_performance",
    "cftc_cot",
    "dallas_tmos",
    "dallas_tssos",
    "eia_930",
    "fed_ach",
    "fed_chargeoff_delinquency",
    "fed_cp",
    "fed_dsr",
    "fed_fci_g",
    "fed_scoos",
    "fed_sfos",
    "fema_disasters",
    "ffiec_hmda",
    "fhwa_tvt",
    "fhwa_ucr",
    "hud_fha_multifamily",
    "hud_fha_single_family",
    "kansascity_mfg",
    "ncua_call_reports",
    "noaa_storm_events",
    "nyfed_business_leaders",
    "nyfed_empire",
    "nyfed_gscpi",
    "nyfed_primary_dealers",
    "nyfed_sce",
    "philly_mbos",
    "philly_nmbos",
    "richmond_mfg",
    "richmond_services",
    "sba_7a_504",
    "treasury_auction",
    "treasury_debt_penny",
    "treasury_mts",
    "treasury_tic",
    "treasury_ui_advances",
    "tsa_throughput",
    "uscourts_bankruptcy",
    "usda_food_price_outlook",
    "usda_snap",
))

NEW_RESERVATION_IDS = frozenset((
    "bls_mxp",
    "cftc_cot",
    "fed_cp",
    "fed_dsr",
    "fed_fci_g",
    "fed_scoos",
    "fed_sfos",
    "ffiec_hmda",
    "hud_fha_multifamily",
    "hud_fha_single_family",
    "ncua_call_reports",
    "nyfed_primary_dealers",
    "sba_7a_504",
    "treasury_tic",
    "usda_food_price_outlook",
))

DISTINCT_EXISTING_RESERVATION_IDS = (
    NEW_FREE_SOURCE_FAMILY_IDS - NEW_RESERVATION_IDS
)
ACTIVATED_EXISTING_RESERVATION_IDS = frozenset((
    "census_bds",
    "fed_cp",
    "fed_dsr",
))

RIGHTS_BLOCKED_SOURCE_FAMILY_IDS = frozenset((
    "cboe_vix",
    "freddie_pmms",
    "ice_bofa_spreads",
    "michigan_consumers",
    "moody_corporate_yields",
    "nasdaq_equity",
    "sp_equity",
))


def _registry_rows():
    with REGISTRY_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _copy_project_inputs(root, planned):
    root = Path(root)
    registry_target = (
        root / "data_vault" / "catalog" /
        "external_source_registry.csv"
    )
    registry_target.parent.mkdir(parents=True, exist_ok=True)
    registry_target.write_bytes(REGISTRY_PATH.read_bytes())

    planned_target = (
        root / "live_data" / "config" / "planned_sources.v1.json"
    )
    planned_target.parent.mkdir(parents=True, exist_ok=True)
    planned_target.write_bytes(canonical_json_bytes(planned))


def _build_isolated_matrix(root, planned=None):
    config = load_config(CONFIG_PATH)
    planned = copy.deepcopy(
        planned if planned is not None else read_json(PLANNED_PATH)
    )
    _copy_project_inputs(root, planned)
    pipeline = RefreshPipeline(
        root,
        config,
        clock=lambda: FIXED_TIME,
    )
    pipeline.store.initialize()
    coverage = pipeline.build_coverage(FIXED_TIME)
    matrix = build_source_matrix(
        root,
        config,
        pipeline.store,
        coverage,
        FIXED_TIME,
    )
    return matrix


class SourceMatrixExactSetTests(unittest.TestCase):
    def test_exact_registered_active_and_reserved_row_closure(self):
        config = load_config(CONFIG_PATH)
        planned = read_json(PLANNED_PATH)
        floors = _growth_floors()
        n_registry = len(_registry_rows())
        # Archival (frozen-admission) rows are config-known runtime heads that are
        # never fetched; they are NOT active collectors and are excluded from the
        # active_collector lane (B-LAND-3B; the record-kind set stays fixed).
        archival_ids = {
            source["source_id"]
            for source in config["sources"]
            if source.get("archival")
        }
        n_active = len(config["sources"]) - len(archival_ids)
        n_planned = len(planned["sources"])

        # Never-decrease floors (recorded outside the test, provenance:derived):
        # a removed or renamed source drops the count below its low-water mark.
        self.assertGreaterEqual(
            n_registry, floors["count_floors"]["registered_source_family"]
        )
        self.assertGreaterEqual(
            n_active, floors["count_floors"]["active_collector"]
        )
        self.assertGreaterEqual(
            n_planned, floors["count_floors"]["reserved_collector"]
        )
        # Append-only ids (§7.3): every previously-seen source_id must still be
        # present. A rename or deletion leaves a recorded id unaccounted for.
        self.assertEqual(
            set(floors["append_only_source_ids"]["registered_source_family"])
            - {row["source_id"] for row in _registry_rows()},
            set(),
        )
        self.assertEqual(
            set(floors["append_only_source_ids"]["active_collector"])
            - {row["source_id"] for row in config["sources"]},
            set(),
        )
        self.assertEqual(
            set(floors["append_only_source_ids"]["reserved_collector"])
            - {row["source_id"] for row in planned["sources"]},
            set(),
        )

        with tempfile.TemporaryDirectory() as temp:
            matrix = _build_isolated_matrix(temp, planned)

        self.assertEqual(
            matrix["schema_version"],
            "recession-monitor-v2.source-acquisition-matrix.v1",
        )
        # Record-kind set is a fixed contract; each count is cross-checked
        # against the actual input length (cannot be a hand-typed number); the
        # reported counts equal the true per-kind tally of the rows.
        self.assertEqual(set(matrix["counts"]), set(ALLOWED_RECORD_KINDS))
        self.assertEqual(
            matrix["counts"]["registered_source_family"], n_registry
        )
        self.assertEqual(matrix["counts"]["active_collector"], n_active)
        # Exact-set closure for the archival class: active_collector rows are
        # exactly the NON-archival config sources; no archival id leaks in.
        active_row_ids = {
            row["source_id"]
            for row in matrix["rows"]
            if row["record_kind"] == "active_collector"
        }
        self.assertEqual(active_row_ids & archival_ids, set())
        self.assertEqual(
            active_row_ids,
            {
                source["source_id"]
                for source in config["sources"]
                if not source.get("archival")
            },
        )
        self.assertEqual(matrix["counts"]["reserved_collector"], n_planned)
        self.assertEqual(
            matrix["counts"],
            dict(Counter(row["record_kind"] for row in matrix["rows"])),
        )
        # Total rows equal the sum over kinds and never fall below the floor.
        self.assertEqual(len(matrix["rows"]), sum(matrix["counts"].values()))
        self.assertGreaterEqual(
            len(matrix["rows"]), floors["count_floors"]["matrix_rows"]
        )
        self.assertEqual(matrix["field_order"], list(MATRIX_FIELDS))
        self.assertEqual(len(MATRIX_FIELDS), len(set(MATRIX_FIELDS)))
        for row in matrix["rows"]:
            self.assertEqual(set(row), set(MATRIX_FIELDS))
        self.assertEqual(
            len({
                (row["record_kind"], row["source_id"])
                for row in matrix["rows"]
            }),
            len(matrix["rows"]),
        )
        content_preimage = dict(matrix)
        del content_preimage["matrix_content_sha256"]
        self.assertEqual(
            matrix["matrix_content_sha256"],
            sha256_bytes(canonical_json_bytes(content_preimage)),
        )

    def test_planned_rows_are_unique_disabled_unparsed_and_resolved(self):
        planned = read_json(PLANNED_PATH)
        self.assertEqual(tuple(planned), PLANNED_TOP_LEVEL_FIELDS)
        self.assertEqual(
            planned["schema_version"],
            "recession-monitor-v2.planned-source-reservations.v1",
        )
        rows = planned["sources"]
        source_ids = [row["source_id"] for row in rows]
        registered_ids = {
            row["source_id"]
            for row in _registry_rows()
        }

        floors = _growth_floors()
        self.assertGreaterEqual(
            len(source_ids), floors["count_floors"]["reserved_collector"]
        )
        self.assertEqual(len(source_ids), len(set(source_ids)))
        # Append-only: every previously-reserved id must still be present.
        self.assertEqual(
            set(floors["append_only_source_ids"]["reserved_collector"])
            - set(source_ids),
            set(),
        )
        # Status names are a fixed contract; the statuses partition the rows
        # (sum == total, so no unclassified row hides); each status count never
        # decreases below its recorded floor.
        status_counts = Counter(row["registry_status"] for row in rows)
        self.assertTrue(
            set(status_counts).issubset(ALLOWED_RESERVATION_STATUSES)
        )
        self.assertEqual(sum(status_counts.values()), len(source_ids))
        for status, floor in floors["reservation_status_floors"].items():
            self.assertGreaterEqual(status_counts.get(status, 0), floor)
        for row in rows:
            self.assertEqual(tuple(row), PLANNED_SOURCE_FIELDS)
            self.assertFalse(row["enabled"])
            self.assertIsNone(row["parser_version"])
            self.assertEqual(
                len(row["coverage_source_family_ids"]),
                len(set(row["coverage_source_family_ids"])),
            )
            self.assertTrue(
                set(row["coverage_source_family_ids"]).issubset(
                    registered_ids
                ),
                row["source_id"],
            )
            self.assertTrue(
                row["coverage_source_family_ids"],
                row["source_id"],
            )

        rows_by_id = {row["source_id"]: row for row in rows}
        for source_id in (
            (
                DISTINCT_EXISTING_RESERVATION_IDS -
                ACTIVATED_EXISTING_RESERVATION_IDS
            ) | (
                NEW_RESERVATION_IDS -
                ACTIVATED_EXISTING_RESERVATION_IDS
            )
        ):
            self.assertEqual(
                rows_by_id[source_id]["coverage_source_family_ids"],
                [source_id],
            )
        # This row was activated on 2026-07-31 as the standalone legacy feed
        # treasury_dts_federal_tax_deposits_legacy. While it is still a
        # reservation it must bind to the treasury_dts family.
        legacy_reservation = rows_by_id.get(
            "treasury_dts_withheld_income_employment_taxes_legacy"
        )
        if legacy_reservation is not None:
            self.assertEqual(
                legacy_reservation["coverage_source_family_ids"],
                ["treasury_dts"],
            )

    def test_free_source_family_expansion_and_rights_blocks_are_exact(self):
        registry = {
            row["source_id"]: row
            for row in _registry_rows()
        }
        self.assertEqual(
            NEW_FREE_SOURCE_FAMILY_IDS.difference(registry),
            set(),
        )
        for source_id in NEW_FREE_SOURCE_FAMILY_IDS:
            self.assertIn(registry[source_id]["access_class"], {"A", "B"})
            self.assertNotIn(
                "license_required",
                registry[source_id]["rights_status"],
            )

        self.assertEqual(
            {
                source_id
                for source_id, row in registry.items()
                if row["access_class"] == "C"
            },
            RIGHTS_BLOCKED_SOURCE_FAMILY_IDS,
        )
        # B-RIGHTS-1 — OWNER_RULING_20260808_PUBLISH_ALL_GOOD_DATA.md re-authors
        # this pin (§18.1, never deleted). The 7 stay access_class C (reserved
        # collectors, NOT enabled) but their raw publication is now PERMITTED:
        # each carries publish_class `publish_all_good_data`. They remain
        # disjoint from forward collection coverage below.
        for source_id in RIGHTS_BLOCKED_SOURCE_FAMILY_IDS:
            self.assertEqual(
                registry[source_id]["publish_class"],
                "publish_all_good_data",
            )
        config = load_config(CONFIG_PATH)
        planned = read_json(PLANNED_PATH)
        forward_coverage = {
            family_id
            for source in (
                list(config["sources"]) + list(planned["sources"])
            )
            for family_id in (
                source["coverage_source_ids"]
                if "coverage_source_ids" in source
                else source["coverage_source_family_ids"]
            )
        }
        self.assertTrue(
            RIGHTS_BLOCKED_SOURCE_FAMILY_IDS.isdisjoint(forward_coverage),
        )
        self.assertEqual(
            (
                NEW_RESERVATION_IDS - ACTIVATED_EXISTING_RESERVATION_IDS
            ).difference({
                row["source_id"] for row in planned["sources"]
            }),
            set(),
        )

    def test_fred_current_routes_cover_exact_twentynine_series_without_vintage_laundering(self):
        config = load_config(CONFIG_PATH)
        planned = read_json(PLANNED_PATH)
        registered_ids = {
            row["source_id"]
            for row in _registry_rows()
        }
        active = [
            row for row in config["sources"]
            if row["adapter"] == "fred_graph_csv"
        ]
        expected = {
            "CPFF": (["fred_current_provider"], "actual"),
            "M2REAL": (["fred_current_provider"], "actual"),
            "NFCICREDIT": (["fred_current_provider"], "actual"),
            "NFCILEVERAGE": (["fred_current_provider"], "actual"),
            "NFCIRISK": (["fred_current_provider"], "actual"),
            "T5YIFR": (["fred_current_provider"], "actual"),
            "TRUCKD11": (["fred_current_provider"], "actual"),
            "CFNAI": (
                ["fred_current_provider", "chicago_cfnai"],
                "model_estimate",
            ),
            "CFNAIMA3": (
                ["fred_current_provider", "chicago_cfnai"],
                "model_estimate",
            ),
            "NFCI": (
                ["fred_current_provider", "chicago_nfci"],
                "model_estimate",
            ),
            "STLFSI4": (
                ["fred_current_provider", "stlouis_stlfsi"],
                "model_estimate",
            ),
            "WEI": (
                ["fred_current_provider", "dallas_wei"],
                "model_estimate",
            ),
            "RIFSPPNAAD90NB": (
                ["fred_current_provider", "fed_cp"],
                "actual",
            ),
            "RIFSPPFAAD90NB": (
                ["fred_current_provider", "fed_cp"],
                "actual",
            ),
            "RIFSPPNA2P2D90NB": (
                ["fred_current_provider", "fed_cp"],
                "actual",
            ),
            "TDSP": (
                ["fred_current_provider", "fed_dsr"],
                "actual",
            ),
            "MDSP": (
                ["fred_current_provider", "fed_dsr"],
                "actual",
            ),
            "CDSP": (
                ["fred_current_provider", "fed_dsr"],
                "actual",
            ),
            # +11 receipted FRED current-lane admissions (continuations #1-#10);
            # each bare-series (no *.ASOF*), current_revised, receipted; no vintage
            # laundering — GDPC1.ASOF* stays on the separate fred_json_api_vintages lane.
            "AMTMNO": (["fred_current_provider"], "actual"),
            "AMTMUO": (["fred_current_provider"], "actual"),
            "ANFCI": (["fred_current_provider"], "actual"),
            "BOGZ1FL893064105Q": (["fred_current_provider"], "actual"),
            "CMRMTSPL": (["fred_current_provider"], "actual"),
            "GACDFSA066MSFRBPHI": (["fred_current_provider"], "actual"),
            "IPG3361T3S": (["fred_current_provider"], "actual"),
            "IPMAN": (["fred_current_provider"], "actual"),
            "MCUMFN": (["fred_current_provider"], "actual"),
            "NCBEILQ027S": (["fred_current_provider"], "actual"),
            "NOCDFSA066MSFRBPHI": (["fred_current_provider"], "actual"),
        }
        # Structural anti-laundering guard (preserved, not weakened): no current-lane
        # series may be a vintage (*.ASOF*), and the vintage lane must be excluded here.
        self.assertTrue(
            all(".ASOF" not in row["series"]["series_id"] for row in active),
            "vintage-laundering: a *.ASOF* series leaked into the FRED current lane",
        )
        self.assertEqual(
            {row["series"]["series_id"] for row in active},
            set(expected),
        )
        self.assertEqual(len(active), len(expected))
        self.assertIn("fred_current_provider", registered_ids)
        for row in active:
            series_id = row["series"]["series_id"]
            self.assertEqual(
                row["coverage_source_ids"],
                expected[series_id][0],
            )
            self.assertEqual(row["value_status"], expected[series_id][1])
            self.assertEqual(
                row["information_set_mode"],
                "current_revised",
            )
            self.assertEqual(
                row["rights_status"],
                "FRED_terms_and_underlying_publisher_rights_control",
            )
            self.assertIn(
                "exact underlying publisher release time remains null",
                row["publisher_release_clock"],
            )
        fred_api = next(
            row for row in planned["sources"]
            if row["source_id"] == "fred_current_api"
        )
        self.assertEqual(
            fred_api["coverage_source_family_ids"],
            ["fred_current_provider"],
        )
        self.assertIn(
            "does not establish publisher first release",
            fred_api["revision_policy"],
        )

    def test_exact_four_no_key_official_tabular_collectors_are_active(self):
        config = load_config(CONFIG_PATH)
        sources = {
            row["source_id"]: row
            for row in config["sources"]
        }
        expected = {
            "chicago_cfsec_current": {
                "adapter": "tabular_csv",
                "coverage": ["chicago_cfsec"],
                "endpoint": (
                    "https://api.data.chicagofed.org/CFSEC/"
                    "cfsec-activity-index-csv.csv"
                ),
                "statuses": {"model_estimate"},
            },
            "chicago_carts_current": {
                "adapter": "tabular_csv",
                "coverage": ["chicago_carts"],
                "endpoint": (
                    "https://api.data.chicagofed.org/CARTS/"
                    "retail_and_food_services_sales_ex_auto.csv"
                ),
                "statuses": {"actual", "forecast", "model_estimate"},
            },
            "bts_tsi_current": {
                "adapter": "socrata_json",
                "coverage": ["bts_tsi"],
                "endpoint": (
                    "https://data.bts.gov/resource/bw6n-ddqk.json"
                    "?$limit=50000&$order=obs_date"
                ),
                "statuses": {"model_estimate"},
            },
            "census_bds_national_current": {
                "adapter": "tabular_csv",
                "coverage": ["census_bds"],
                "endpoint": (
                    "https://www2.census.gov/programs-surveys/bds/"
                    "tables/time-series/2023/bds2023.csv"
                ),
                "statuses": {"actual"},
            },
        }
        self.assertEqual(
            set(expected).intersection(sources),
            set(expected),
        )
        for source_id, contract in expected.items():
            source = sources[source_id]
            self.assertTrue(source["enabled"])
            self.assertEqual(source["adapter"], contract["adapter"])
            self.assertEqual(
                source["coverage_source_ids"],
                contract["coverage"],
            )
            self.assertEqual(source["endpoint"], contract["endpoint"])
            self.assertEqual(
                {item["value_status"] for item in source["series"]["items"]},
                contract["statuses"],
            )
            self.assertEqual(source["information_set_mode"], "current_revised")
            self.assertFalse(source["secret_required"])
            self.assertIsNone(source["secret_env"])

        registry = {
            row["source_id"]: row
            for row in _registry_rows()
        }
        self.assertEqual(registry["bts_tsi"]["access_class"], "A")
        self.assertEqual(registry["chicago_carts"]["access_class"], "B")
        self.assertEqual(registry["chicago_cfsec"]["access_class"], "B")
        planned = {
            row["source_id"]: row
            for row in read_json(PLANNED_PATH)["sources"]
        }
        for source_id in ("bts_tsi", "chicago_carts", "chicago_cfsec"):
            self.assertEqual(
                planned[source_id]["coverage_source_family_ids"],
                [source_id],
            )
        self.assertNotIn("census_bds", planned)

    def test_bls_mxp_headline_current_route_is_exact_and_bulk_lane_remains_reserved(self):
        config = load_config(CONFIG_PATH)
        sources = {
            row["source_id"]: row
            for row in config["sources"]
        }
        source = sources["bls_mxp_current"]
        self.assertEqual(source["adapter"], "bls_json")
        self.assertEqual(source["coverage_source_ids"], ["bls_mxp"])
        self.assertEqual(
            source["endpoint"],
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        )
        self.assertEqual(source["frequency"], "monthly")
        self.assertEqual(source["information_set_mode"], "current_revised")
        self.assertEqual(source["secret_env"], "BLS_API_KEY")
        self.assertFalse(source["secret_required"])
        self.assertEqual(source["series"]["history_years"], 3)
        self.assertEqual(
            source["series"]["items"],
            [
                {
                    "label": (
                        "Monthly import price index for BEA End Use, "
                        "All commodities, not seasonally adjusted"
                    ),
                    "series_id": "EIUIR",
                    "unit": "index 2000=100",
                },
                {
                    "label": (
                        "Monthly export price index for BEA End Use, "
                        "All commodities, not seasonally adjusted"
                    ),
                    "series_id": "EIUIQ",
                    "unit": "index 2000=100",
                },
            ],
        )
        planned = {
            row["source_id"]: row
            for row in read_json(PLANNED_PATH)["sources"]
        }
        self.assertIn("bls_mxp", planned)
        self.assertFalse(planned["bls_mxp"]["enabled"])
        self.assertIsNone(planned["bls_mxp"]["parser_version"])

    def test_federal_reserve_dsr_current_route_replaces_exact_reservation(self):
        config = load_config(CONFIG_PATH)
        sources = {
            row["source_id"]: row
            for row in config["sources"]
        }
        source = sources["fed_dsr_current"]
        self.assertEqual(source["adapter"], "fed_ddp_csv")
        self.assertEqual(source["coverage_source_ids"], ["fed_dsr"])
        self.assertEqual(source["frequency"], "quarterly")
        self.assertEqual(source["information_set_mode"], "current_revised")
        self.assertEqual(source["method_version"], "fed_dsr_ddp_current_method.v1")
        self.assertEqual(
            source["endpoint"],
            (
                "https://www.federalreserve.gov/datadownload/Output.aspx?"
                "rel=DSR&series=e38200c11a744800391ad51150cee181&"
                "lastobs=&from=&to=&filetype=csv&label=include&"
                "layout=seriescolumn&type=package"
            ),
        )
        self.assertEqual(
            source["series"]["expected_columns"],
            [
                "DSR_RATIO",
                "MORTGAGE_DSR_RATIO",
                "CONSUMER_DSR_RATIO",
            ],
        )
        self.assertEqual(
            source["series"]["expected_unique_identifier_label"],
            "Unique Identifier: ",
        )
        self.assertFalse(source["secret_required"])
        self.assertIsNone(source["secret_env"])
        planned_ids = {
            row["source_id"]
            for row in read_json(PLANNED_PATH)["sources"]
        }
        self.assertNotIn("fed_dsr", planned_ids)

    def test_federal_reserve_cp_current_route_replaces_exact_reservation(self):
        config = load_config(CONFIG_PATH)
        sources = {
            row["source_id"]: row
            for row in config["sources"]
        }
        source = sources["fed_cp_rates_current"]
        self.assertEqual(source["adapter"], "fed_ddp_csv")
        self.assertEqual(source["coverage_source_ids"], ["fed_cp"])
        self.assertEqual(source["frequency"], "daily_business_day")
        self.assertEqual(source["information_set_mode"], "current_revised")
        self.assertEqual(
            source["method_version"],
            "fed_cp_rates_ddp_last270.current_revised.v1",
        )
        self.assertEqual(
            source["endpoint"],
            (
                "https://www.federalreserve.gov/datadownload/Output.aspx?"
                "rel=CP&series=593ce926936cbd64b3c79b960a792b85&"
                "lastobs=270&from=&to=&filetype=csv&label=include&"
                "layout=seriescolumn&type=package"
            ),
        )
        self.assertEqual(len(source["series"]["expected_columns"]), 24)
        self.assertEqual(
            source["series"]["expected_columns"][:2],
            ["RIFSPPNAAD01_N.B", "RIFSPPNAAD07_N.B"],
        )
        self.assertEqual(
            source["series"]["expected_columns"][-2:],
            ["RIFSPPAAAD60_N.B", "RIFSPPAAAD90_N.B"],
        )
        self.assertEqual(
            source["series"]["series_id_prefix"],
            "FED.CP.RATES.",
        )
        self.assertEqual(
            source["series"]["expected_unique_identifier_label"],
            "Unique Identifier:",
        )
        self.assertFalse(source["secret_required"])
        self.assertIsNone(source["secret_env"])
        planned_ids = {
            row["source_id"]
            for row in read_json(PLANNED_PATH)["sources"]
        }
        self.assertNotIn("fed_cp", planned_ids)

    def test_exact_three_keyless_fiscaldata_collectors_are_active(self):
        config = load_config(CONFIG_PATH)
        sources = {
            row["source_id"]: row
            for row in config["sources"]
        }
        expected = {
            "treasury_debt_penny": {
                "coverage": ["treasury_debt_penny"],
                "date_fields": ["record_date"],
                "dimensions": [],
                "identity": ["record_date", "src_line_nbr"],
                "item_fields": {
                    "debt_held_public_amt",
                    "intragov_hold_amt",
                    "tot_pub_debt_out_amt",
                },
            },
            "treasury_ui_advances": {
                "coverage": ["treasury_ui_advances"],
                "date_fields": ["record_date"],
                "dimensions": ["state_nm", "src_line_nbr"],
                "identity": [
                    "record_date",
                    "state_nm",
                    "src_line_nbr",
                ],
                "item_fields": {
                    "interest_rate_pct",
                    "outstanding_advance_bal",
                    "advance_auth_month_amt",
                    "gross_advance_draws_month_amt",
                    "interest_accrued_fytd_amt",
                    "interest_paid_amt",
                },
            },
            "treasury_auction": {
                "coverage": ["treasury_auction"],
                "date_fields": [
                    "record_date",
                    "announcemt_date",
                    "auction_date",
                    "issue_date",
                    "maturity_date",
                ],
                "dimensions": ["cusip"],
                "identity": ["cusip", "auction_date"],
                "item_fields": {
                    "offering_amt",
                    "total_tendered",
                    "total_accepted",
                    "bid_to_cover_ratio",
                    "high_yield",
                    "high_discnt_rate",
                    "high_investment_rate",
                    "high_price",
                    "direct_bidder_accepted",
                    "indirect_bidder_accepted",
                    "primary_dealer_accepted",
                    "soma_accepted",
                    "noncomp_accepted",
                    "fima_noncomp_accepted",
                    "treas_retail_accepted",
                },
            },
        }
        self.assertEqual(set(expected).intersection(sources), set(expected))
        for source_id, contract in expected.items():
            source = sources[source_id]
            self.assertEqual(source["adapter"], "fiscaldata_json")
            self.assertTrue(source["enabled"])
            self.assertFalse(source["secret_required"])
            self.assertIsNone(source["secret_env"])
            self.assertEqual(
                source["information_set_mode"],
                "current_revised",
            )
            self.assertEqual(
                source["coverage_source_ids"],
                contract["coverage"],
            )
            self.assertEqual(
                source["series"]["date_fields"],
                contract["date_fields"],
            )
            self.assertEqual(
                source["series"]["dimension_fields"],
                contract["dimensions"],
            )
            self.assertEqual(
                source["series"]["identity_fields"],
                contract["identity"],
            )
            self.assertEqual(
                {item["field"] for item in source["series"]["items"]},
                contract["item_fields"],
            )
            self.assertEqual(source["series"]["missing_tokens"], ["null"])
            self.assertIn("page%5Bsize%5D=10000", source["endpoint"])
            self.assertIn("{year}-01-01", source["endpoint"])
        auction_items = {
            item["field"]: item
            for item in sources["treasury_auction"]["series"]["items"]
        }
        self.assertEqual(
            auction_items["offering_amt"]["event_date_field"],
            "announcemt_date",
        )
        for field, item in auction_items.items():
            if field != "offering_amt":
                self.assertEqual(item["event_date_field"], "auction_date")

    def test_philly_mbos_diffusion_history_is_active_and_not_national(self):
        config = load_config(CONFIG_PATH)
        sources = {
            row["source_id"]: row
            for row in config["sources"]
        }
        source = sources["philly_mbos_diffusion_current"]
        self.assertEqual(source["adapter"], "tabular_csv")
        self.assertTrue(source["enabled"])
        self.assertEqual(source["coverage_source_ids"], ["philly_mbos"])
        self.assertEqual(
            source["endpoint"],
            (
                "https://www.philadelphiafed.org/-/media/FRBP/Assets/"
                "Surveys-And-Data/MBOS/Historical-Data/"
                "Diffusion-Indexes/bos_dif.csv?sc_lang=en"
            ),
        )
        self.assertEqual(
            source["series"]["date_format"],
            "month_abbrev_two_digit_year_pivot_1968",
        )
        self.assertEqual(source["series"]["date_column"], "DATE")
        self.assertEqual(len(source["series"]["items"]), 21)
        self.assertEqual(
            {item["value_status"] for item in source["series"]["items"]},
            {"model_estimate"},
        )
        self.assertEqual(
            {item["column"] for item in source["series"]["items"]},
            {
                "GAC", "NOC", "SHC", "UOC", "DTC", "IVC", "PPC",
                "PRC", "NEC", "AWC", "GAF", "NOF", "SHF", "UOF",
                "DTF", "IVF", "PPF", "PRF", "NEF", "AWF", "CEF",
            },
        )
        self.assertEqual(source["information_set_mode"], "current_revised")
        self.assertIn(
            "regional",
            source["publisher_release_clock"],
        )
        self.assertFalse(source["secret_required"])
        self.assertIsNone(source["secret_env"])

    def test_tsa_web_table_scraper_is_active_observed_and_recent_era_only(self):
        config = load_config(CONFIG_PATH)
        source = next(
            row for row in config["sources"]
            if row["source_id"] == "tsa_throughput_current"
        )
        self.assertEqual(source["adapter"], "tsa_passenger_html")
        self.assertTrue(source["enabled"])
        self.assertEqual(source["coverage_source_ids"], ["tsa_throughput"])
        self.assertEqual(
            source["endpoint"],
            "https://www.tsa.gov/travel/passenger-volumes?page=0",
        )
        self.assertEqual(source["expected_content_types"], ["text/html"])
        self.assertEqual(source["frequency"], "daily")
        self.assertEqual(source["value_status"], "actual")
        self.assertEqual(source["information_set_mode"], "current_revised")
        self.assertEqual(source["series"], {})
        self.assertIn(
            "not total passenger travel",
            source["publisher_release_clock"],
        )
        self.assertFalse(source["secret_required"])
        self.assertIsNone(source["secret_env"])

    def test_free_official_financial_housing_and_banking_feeds_are_active(self):
        config = load_config(CONFIG_PATH)
        sources = {
            row["source_id"]: row
            for row in config["sources"]
        }
        expected = {
            "fdic_banking_aggregate_quarterly": (
                "fdic_aggregate_json",
                ["fdic_qbp"],
                "https://api.fdic.gov/banks/financials?fields=REPDTE"
            ),
            "fhfa_hpi_monthly_us": (
                "fhfa_hpi_csv",
                ["fhfa_hpi"],
                "https://www.fhfa.gov/hpi/download/monthly/hpi_master.csv",
            ),
            "ofr_fsi_daily": (
                "ofr_fsi_csv",
                ["ofr_fsi"],
                "https://www.financialresearch.gov/financial-stress-index/"
                "data/fsi.csv",
            ),
        }
        for source_id, contract in expected.items():
            with self.subTest(source_id=source_id):
                source = sources[source_id]
                adapter, coverage, endpoint_prefix = contract
                self.assertEqual(source["adapter"], adapter)
                self.assertEqual(source["coverage_source_ids"], coverage)
                self.assertTrue(source["endpoint"].startswith(endpoint_prefix))
                self.assertTrue(source["enabled"])
                self.assertEqual(
                    source["information_set_mode"],
                    "current_revised",
                )
                self.assertEqual(source["series"], {})
                self.assertFalse(source["secret_required"])
                self.assertIsNone(source["secret_env"])

    def test_cdc_respiratory_status_lanes_are_separate_and_exact(self):
        config = load_config(CONFIG_PATH)
        sources = {
            row["source_id"]: row
            for row in config["sources"]
        }
        expected = {
            "cdc_resp_preliminary_current": (
                "mpgq-jmmr",
                "current_revised",
            ),
            "cdc_resp_final_current": (
                "ua7e-t2fy",
                "current_revised",
            ),
            "cdc_resp_publication_history": (
                "rhwp-grxi",
                "archive_snapshot_asof",
            ),
        }
        self.assertEqual(set(expected).intersection(sources), set(expected))
        for source_id, contract in expected.items():
            dataset_id, information_set_mode = contract
            source = sources[source_id]
            self.assertEqual(source["adapter"], "socrata_json")
            self.assertEqual(source["coverage_source_ids"], ["cdc_respviruses"])
            self.assertIn(
                "https://data.cdc.gov/resource/%s.json" % dataset_id,
                source["endpoint"],
            )
            self.assertIn("jurisdiction%3D%27USA%27", source["endpoint"])
            self.assertEqual(source["series"]["identity_field"], "weekendingdate")
            self.assertEqual(len(source["series"]["items"]), 7)
            self.assertEqual(
                {item["value_status"] for item in source["series"]["items"]},
                {"actual"},
            )
            self.assertEqual(
                source["information_set_mode"],
                information_set_mode,
            )
            self.assertFalse(source["secret_required"])
        registry = {
            row["source_id"]: row
            for row in _registry_rows()
        }
        self.assertEqual(registry["cdc_respviruses"]["access_class"], "A")
        planned = {
            row["source_id"]: row
            for row in read_json(PLANNED_PATH)["sources"]
        }
        self.assertEqual(
            planned["cdc_respviruses"]["coverage_source_family_ids"],
            ["cdc_respviruses"],
        )

    def test_credentials_are_names_only_and_never_secret_values(self):
        planned_bytes = PLANNED_PATH.read_bytes()
        planned = strict_json_loads(planned_bytes)
        auth_envs = {
            row["auth_env"]
            for row in planned["sources"]
            if row["auth_env"] is not None
        }
        self.assertEqual(auth_envs, REQUIRED_AUTH_ENVS)
        for auth_env in auth_envs:
            self.assertRegex(auth_env, r"^[A-Z][A-Z0-9_]*$")
        for row in planned["sources"]:
            endpoint_lower = row["endpoint"].lower()
            self.assertNotIn("api_key=", endpoint_lower)
            self.assertNotIn("apikey=", endpoint_lower)
            self.assertNotIn("user_id=", endpoint_lower)
            self.assertNotIn("token=", endpoint_lower)

        sentinels = {
            name: "RMV2_TEST_SECRET_VALUE_%s" % name
            for name in REQUIRED_AUTH_ENVS
        }
        with mock.patch.dict(os.environ, sentinels, clear=False):
            for value in sentinels.values():
                self.assertNotIn(value.encode("utf-8"), planned_bytes)

        env_rows = [
            line.strip()
            for line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(
            {line.split("=", 1)[0] for line in env_rows},
            REQUIRED_AUTH_ENVS | {"BLS_API_KEY"},
        )
        self.assertTrue(all(line.endswith("=") for line in env_rows))

    def test_dol_operational_release_and_archive_lanes_are_not_aliased(self):
        config = load_config(CONFIG_PATH)
        planned = read_json(PLANNED_PATH)
        active_by_id = {
            row["source_id"]: row
            for row in config["sources"]
        }
        planned_by_id = {
            row["source_id"]: row
            for row in planned["sources"]
        }
        eta = active_by_id["dol_eta539_live"]
        release = active_by_id[
            "dol_ui_national_weekly_release_current"
        ]
        archive = planned_by_id[
            "dol_ui_national_weekly_release_archive"
        ]

        self.assertEqual(
            {
                eta["source_id"],
                release["source_id"],
                archive["source_id"],
            },
            {
                "dol_eta539_live",
                "dol_ui_national_weekly_release_current",
                "dol_ui_national_weekly_release_archive",
            },
        )
        self.assertEqual(
            len({
                eta["endpoint"],
                release["endpoint"],
                archive["endpoint"],
            }),
            3,
        )
        self.assertEqual(eta["adapter"], "dol_eta539_csv")
        self.assertEqual(eta["information_set_mode"], "current_revised")
        self.assertEqual(release["adapter"], "raw_capture")
        self.assertTrue(release["enabled"])
        self.assertIn(
            "distinct from the Thursday 08:30 national release",
            eta["publisher_release_clock"],
        )
        self.assertIn(
            "Thursday 08:30 America/New_York",
            release["publisher_release_clock"],
        )
        self.assertFalse(archive["enabled"])
        self.assertIn("three non-aliased lanes", archive[
            "split_or_bias_guard"
        ])

    def test_treasury_dts_legacy_and_current_concepts_are_disjoint(self):
        config = load_config(CONFIG_PATH)
        planned = read_json(PLANNED_PATH)
        active_by_id = {
            row["source_id"]: row
            for row in config["sources"]
        }
        planned_by_id = {
            row["source_id"]: row
            for row in planned["sources"]
        }
        # The legacy concept was a reservation until it was onboarded as its
        # own active feed on 2026-07-31. Disjointness is the invariant, not
        # which config the legacy lane happens to live in.
        legacy = (
            planned_by_id.get(
                "treasury_dts_withheld_income_employment_taxes_legacy"
            ) or
            active_by_id["treasury_dts_federal_tax_deposits_legacy"]
        )
        current = active_by_id[
            "treasury_dts_withheld_individual_fica_current"
        ]

        self.assertNotIn(current["source_id"], planned_by_id)
        self.assertNotEqual(legacy["source_id"], current["source_id"])
        self.assertNotEqual(legacy["endpoint"], current["endpoint"])
        self.assertIn(
            "2023-02-1",
            legacy.get("observation_period") or legacy["label"],
        )
        self.assertEqual(current["adapter"], "treasury_dts_json")
        self.assertTrue(current["enabled"])
        self.assertEqual(
            current["method_version"],
            "treasury_dts_withheld_individual_fica_current.v1",
        )
        self.assertIn(
            "transaction_catg:eq:Taxes%20-%20Withheld%20Individual%2FFICA",
            current["endpoint"],
        )
        # A reservation carries the no-splice rule in split_or_bias_guard;
        # once activated, the same rule lives in the feed's label and its
        # publisher_release_clock. Assert the rule, not the field name.
        legacy_text = " ".join(
            str(legacy.get(field) or "")
            for field in (
                "split_or_bias_guard",
                "label",
                "publisher_release_clock",
                "method_version",
            )
        )
        self.assertIn("Withheld Income and Employment Taxes", legacy_text)
        self.assertIn(
            "Taxes - Withheld Individual/FICA",
            current["label"],
        )
        self.assertTrue(
            "Never splice silently" in legacy_text or
            "legacy" in legacy_text.lower(),
        )
        self.assertEqual(
            current["coverage_source_ids"],
            ["treasury_dts"],
        )


class SourceMatrixSerializationTests(unittest.TestCase):
    def test_json_and_csv_receipt_hashes_and_byte_counts_reproduce(self):
        with tempfile.TemporaryDirectory() as temp:
            matrix = _build_isolated_matrix(temp)
            first = write_source_matrix(temp, matrix)
            json_path = (
                Path(temp) / "live_data" / "catalog" /
                "source_matrix.v1.json"
            )
            csv_path = (
                Path(temp) / "live_data" / "catalog" /
                "source_matrix.v1.csv"
            )
            json_bytes = json_path.read_bytes()
            csv_bytes = csv_path.read_bytes()

            self.assertEqual(first["json_bytes"], len(json_bytes))
            self.assertEqual(first["json_sha256"], sha256_bytes(json_bytes))
            self.assertEqual(first["csv_bytes"], len(csv_bytes))
            self.assertEqual(first["csv_sha256"], sha256_bytes(csv_bytes))
            self.assertEqual(first["row_count"], len(matrix["rows"]))
            self.assertEqual(first["json_path"], str(json_path))

            json_value = strict_json_loads(json_bytes)
            self.assertEqual(
                json_value["csv_bytes"],
                len(csv_bytes),
            )
            self.assertEqual(
                json_value["csv_sha256"],
                sha256_bytes(csv_bytes),
            )
            csv_rows = list(csv.reader(
                io.StringIO(csv_bytes.decode("utf-8"))
            ))
            self.assertEqual(tuple(csv_rows[0]), MATRIX_FIELDS)
            self.assertEqual(len(csv_rows) - 1, first["row_count"])

            second = write_source_matrix(temp, matrix)
            self.assertEqual(second, first)
            self.assertEqual(json_path.read_bytes(), json_bytes)
            self.assertEqual(csv_path.read_bytes(), csv_bytes)

    def test_duplicate_or_extra_key_planned_inputs_fail_closed(self):
        planned = read_json(PLANNED_PATH)
        duplicate = copy.deepcopy(planned)
        duplicate["sources"].append(
            copy.deepcopy(duplicate["sources"][0])
        )
        extra_key = copy.deepcopy(planned)
        extra_key["sources"][0]["unexpected"] = "must fail"

        cases = (
            ("duplicate_source_id", duplicate),
            ("extra_row_key", extra_key),
        )
        for label, value in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temp:
                    with self.assertRaises(CanonicalDataError):
                        _build_isolated_matrix(temp, value)


if __name__ == "__main__":
    unittest.main()
