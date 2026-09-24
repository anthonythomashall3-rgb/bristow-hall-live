from __future__ import absolute_import

import copy
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable
from live_data.rmv2_live.canonical import read_json
from live_data.rmv2_live.config import load_config


RETRIEVED_AT = "2026-07-30T05:33:00Z"
CONFIG_PATH = PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"


def series_config():
    return {
        "date_frequency": "quarterly",
        "expected_columns": ["BANK_TIGHT_N.Q", "BANK_DEMAND_N.Q"],
        "expected_currency": "NA",
        "expected_multiplier": "1",
        "expected_unit": "Percentage",
        "identifier_prefix": "SLOOS/SLOOS/",
        "missing_tokens": ["", "NA"],
        "series_id_prefix": "FED.SLOOS.",
    }


def source_config():
    return {
        "adapter": "fed_ddp_csv",
        "allowed_hosts": ["www.federalreserve.gov"],
        "coverage_source_ids": ["fed_sloos"],
        "enabled": True,
        "endpoint": "https://www.federalreserve.gov/data.csv",
        "expected_content_types": ["text/csv"],
        "frequency": "quarterly",
        "information_set_mode": "current_revised",
        "label": "Federal Reserve survey",
        "max_bytes": 1000000,
        "method_version": "fed_sloos_ddp_current.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Board",
        "publisher_release_clock": "quarterly America/New_York",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": series_config(),
        "source_id": "fed_sloos_current",
        "value_status": "actual",
    }


def fixture():
    return (
        "Series Description,Tightening standards,Stronger demand\n"
        "Unit:,Percentage,Percentage\n"
        "Multiplier:,1,1\n"
        "Currency:,NA,NA\n"
        "Unique Identifier:,SLOOS/SLOOS/BANK_TIGHT_N.Q,"
        "SLOOS/SLOOS/BANK_DEMAND_N.Q\n"
        "Time Period,BANK_TIGHT_N.Q,BANK_DEMAND_N.Q\n"
        "2025Q4,12.5,NA\n"
        "2026Q1,-3.0,5\n"
    ).encode("utf-8")


def currency_series_config():
    return {
        "date_frequency": "monthly",
        "expected_columns": ["B1001NCBAM", "B1002NCBAM"],
        "expected_currency": "USD",
        "expected_multiplier": "1000000",
        "expected_unit": "Currency",
        "identifier_prefix": "H8/H8/",
        "missing_tokens": ["", "NA"],
        "series_id_prefix": "FED.H8.",
    }


def currency_source_config():
    source = source_config()
    source["series"] = currency_series_config()
    source["coverage_source_ids"] = ["fed_h8"]
    source["source_id"] = "fed_h8_monthly_current"
    source["frequency"] = "monthly"
    return source


def currency_fixture():
    return (
        "Series Description,Bank credit SA,Securities SA\n"
        "Unit:,Currency,Currency\n"
        "Multiplier:,1000000,1000000\n"
        "Currency:,USD,USD\n"
        "Unique Identifier: ,H8/H8/B1001NCBAM,H8/H8/B1002NCBAM\n"
        "Time Period,B1001NCBAM,B1002NCBAM\n"
        "1947-01,109116.7,82379.3\n"
        "1947-02,108530.3,NA\n"
    ).encode("utf-8")


class FedDdpCurrencyUnitTests(unittest.TestCase):
    """Unit derivation: currency DDP packages (H.8) must not be mislabeled percent."""

    def test_currency_package_emits_derived_currency_unit(self):
        source = currency_source_config()
        source["series"]["expected_unique_identifier_label"] = "Unique Identifier: "
        records = adapters.normalize(source, currency_fixture(), RETRIEVED_AT)
        self.assertEqual(sorted({r["unit"] for r in records}), ["USD_millions"])
        self.assertEqual(records[0]["series_id"], "FED.H8.B1001NCBAM")
        self.assertEqual(records[0]["value"], "109116.7")

    def test_percent_family_unit_is_unchanged(self):
        records = adapters.normalize(source_config(), fixture(), RETRIEVED_AT)
        self.assertEqual(sorted({r["unit"] for r in records}), ["percent"])

    def test_unsupported_currency_scale_fails_closed(self):
        source = currency_source_config()
        source["series"] = copy.deepcopy(source["series"])
        source["series"]["expected_unique_identifier_label"] = "Unique Identifier: "
        source["series"]["expected_multiplier"] = "1000"
        variant = currency_fixture().replace(b"Multiplier:,1000000,1000000",
                                              b"Multiplier:,1000,1000", 1)
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source, variant, RETRIEVED_AT)


class FedDdpAdapterTests(unittest.TestCase):
    def test_exact_ddp_envelope_projects_available_and_unavailable_values(self):
        records = adapters.normalize(source_config(), fixture(), RETRIEVED_AT)
        self.assertEqual(len(records), 4)
        self.assertEqual(records[0]["series_id"], "FED.SLOOS.BANK_TIGHT_N.Q")
        self.assertEqual(records[0]["observation_period"], "2025-10-01")
        self.assertEqual(records[0]["publisher_period"], "2025Q4")
        self.assertEqual(records[0]["value"], "12.5")
        self.assertEqual(records[0]["value_status"], "actual")
        self.assertEqual(records[1]["value"], None)
        self.assertEqual(records[1]["value_status"], "unavailable")
        self.assertEqual(records[-1]["observation_period"], "2026-01-01")
        self.assertFalse(records[-1]["strict_publisher_first_release_proven"])

    def test_metadata_schema_changes_fail_closed(self):
        mutations = (
            (b"Unit:", b"Units:"),
            (b"Percentage", b"Percent"),
            (b"Multiplier:,1,1", b"Multiplier:,1,1000"),
            (b"Currency:,NA,NA", b"Currency:,USD,NA"),
            (b"SLOOS/SLOOS/BANK_TIGHT_N.Q", b"SLOOS/SLOOS/OTHER_N.Q"),
            (b"Time Period,BANK_TIGHT_N.Q,BANK_DEMAND_N.Q",
             b"Time Period,BANK_DEMAND_N.Q,BANK_TIGHT_N.Q"),
        )
        for before, after in mutations:
            with self.subTest(before=before):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(
                        source_config(),
                        fixture().replace(before, after, 1),
                        RETRIEVED_AT,
                    )

    def test_noncanonical_value_duplicate_period_and_bad_quarter_fail_closed(self):
        mutations = (
            (b"12.5", b" 12.5"),
            (b"12.5", b"ND"),
            (b"2026Q1", b"2026Q5"),
            (b"2026Q1,-3.0,5", b"2025Q4,-3.0,5"),
        )
        for before, after in mutations:
            with self.subTest(before=before):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(
                        source_config(),
                        fixture().replace(before, after, 1),
                        RETRIEVED_AT,
                    )

    def test_config_contract_and_live_sloos_definition_are_exact(self):
        config = load_config(CONFIG_PATH)
        source = next(
            item for item in config["sources"]
            if item["source_id"] == "fed_sloos_current"
        )
        self.assertEqual(source["coverage_source_ids"], ["fed_sloos"])
        self.assertEqual(source["adapter"], "fed_ddp_csv")
        self.assertEqual(len(source["series"]["expected_columns"]), 33)
        self.assertEqual(
            len(source["series"]["expected_columns"]),
            len(set(source["series"]["expected_columns"])),
        )

    def test_unknown_series_metadata_key_is_rejected(self):
        source = source_config()
        source["series"] = copy.deepcopy(source["series"])
        source["series"]["default"] = "forbidden"
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source, fixture(), RETRIEVED_AT)

    def test_explicit_publisher_unique_identifier_label_variant_is_exact(self):
        source = source_config()
        source["series"] = copy.deepcopy(source["series"])
        source["series"]["expected_unique_identifier_label"] = (
            "Unique Identifier: "
        )
        variant = fixture().replace(
            b"Unique Identifier:,",
            b"Unique Identifier: ,",
            1,
        )
        records = adapters.normalize(source, variant, RETRIEVED_AT)
        self.assertEqual(len(records), 4)
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source, fixture(), RETRIEVED_AT)


if __name__ == "__main__":
    unittest.main()
