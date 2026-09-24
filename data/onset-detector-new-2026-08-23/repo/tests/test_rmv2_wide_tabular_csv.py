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
from live_data.rmv2_live.config import load_config


RETRIEVED_AT = "2026-07-30T05:45:00Z"
CONFIG_PATH = PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"


def source_config():
    return {
        "adapter": "tabular_csv",
        "allowed_hosts": ["publisher.example"],
        "coverage_source_ids": ["survey_family"],
        "enabled": True,
        "endpoint": "https://publisher.example/survey.csv",
        "expected_content_types": ["text/csv"],
        "frequency": "monthly",
        "information_set_mode": "current_revised",
        "label": "Wide survey",
        "max_bytes": 1000000,
        "method_version": "wide_survey.v1",
        "poll_seconds": 3600,
        "publisher": "Publisher",
        "publisher_release_clock": "monthly",
        "rights_status": "public_source",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "date_column": "surveyDate",
            "date_format": "%Y-%m-%d",
            "expected_header": [
                "surveyDate",
                "CURRENT_DOWN",
                "CURRENT_DIFFUSION",
                "FUTURE_DIFFUSION",
            ],
            "items": [
                {
                    "column": "CURRENT_DIFFUSION",
                    "forecast_horizon": None,
                    "label": "Current diffusion index",
                    "series_id": "SURVEY.CURRENT",
                    "unit": "diffusion index points",
                    "value_status": "model_estimate",
                },
                {
                    "column": "FUTURE_DIFFUSION",
                    "forecast_horizon": "six_month_expectation",
                    "label": "Future diffusion expectation",
                    "series_id": "SURVEY.FUTURE",
                    "unit": "diffusion index points",
                    "value_status": "forecast",
                },
            ],
            "missing_tokens": ["", "ND"],
        },
        "source_id": "wide_survey_current",
        "value_status": "model_estimate",
    }


def fixture():
    return (
        "surveyDate,CURRENT_DOWN,CURRENT_DIFFUSION,FUTURE_DIFFUSION\n"
        "2026-06-30,12.0,-1.5,ND\n"
        "2026-07-31,10.0,2.5,8.0\n"
    ).encode("utf-8")


BDS_HEADER = [
    "year",
    "firms",
    "estabs",
    "emp",
    "denom",
    "estabs_entry",
    "estabs_entry_rate",
    "estabs_exit",
    "estabs_exit_rate",
    "job_creation",
    "job_creation_births",
    "job_creation_continuers",
    "job_creation_rate_births",
    "job_creation_rate",
    "job_destruction",
    "job_destruction_deaths",
    "job_destruction_continuers",
    "job_destruction_rate_deaths",
    "job_destruction_rate",
    "net_job_creation",
    "net_job_creation_rate",
    "reallocation_rate",
    "firmdeath_firms",
    "firmdeath_estabs",
    "firmdeath_emp",
]


def bds_source_config():
    return {
        "adapter": "tabular_csv",
        "allowed_hosts": ["www2.census.gov"],
        "coverage_source_ids": ["census_bds"],
        "enabled": True,
        "endpoint": (
            "https://www2.census.gov/programs-surveys/bds/"
            "tables/time-series/2023/bds2023.csv"
        ),
        "expected_content_types": ["text/csv"],
        "frequency": "annual",
        "information_set_mode": "current_revised",
        "label": "Census BDS national annual realized-damage rates",
        "max_bytes": 100000,
        "method_version": "census_bds_national_2023_csv.current_revised.v1",
        "poll_seconds": 604800,
        "publisher": "U.S. Census Bureau",
        "publisher_release_clock": "annual publisher schedule",
        "rights_status": (
            "public_government_data_with_attribution_and_disclosure_controls"
        ),
        "secret_env": None,
        "secret_required": False,
        "series": {
            "date_column": "year",
            "date_format": "%Y",
            "expected_header": BDS_HEADER,
            "items": [
                {
                    "column": "estabs_exit_rate",
                    "forecast_horizon": None,
                    "label": "Establishment exit rate",
                    "series_id": "CENSUS.BDS.NATIONAL.ESTABS_EXIT_RATE",
                    "unit": "percent of average establishment count",
                    "value_status": "actual",
                },
                {
                    "column": "job_destruction_rate_deaths",
                    "forecast_horizon": None,
                    "label": "Job destruction rate from establishment deaths",
                    "series_id": (
                        "CENSUS.BDS.NATIONAL."
                        "JOB_DESTRUCTION_RATE_DEATHS"
                    ),
                    "unit": "percent of DHS employment denominator",
                    "value_status": "actual",
                },
                {
                    "column": "job_destruction_rate",
                    "forecast_horizon": None,
                    "label": "Total job destruction rate",
                    "series_id": "CENSUS.BDS.NATIONAL.JOB_DESTRUCTION_RATE",
                    "unit": "percent of DHS employment denominator",
                    "value_status": "actual",
                },
            ],
            "missing_tokens": [""],
        },
        "source_id": "census_bds_national_current",
        "value_status": "actual",
    }


def bds_fixture():
    first = [
        "1978", "500", "600", "700", "650", "10", "1.0", "20",
        "2.5", "30", "12", "18", "1.2", "3.0", "40", "15", "25",
        "1.5", "4.0", "-10", "-1.0", "7.0", "5", "8", "9",
    ]
    second = [
        "1979", "510", "610", "710", "660", "11", "1.1", "21",
        "2.6", "31", "13", "18", "1.3", "3.1", "41", "16", "25",
        "1.6", "4.1", "-10", "-1.0", "7.2", "6", "9", "10",
    ]
    return (
        ",".join(BDS_HEADER) + "\n" +
        ",".join(first) + "\n" +
        ",".join(second) + "\n"
    ).encode("utf-8")


class WideTabularCsvTests(unittest.TestCase):
    def test_full_header_is_verified_while_only_owned_fields_are_projected(self):
        records = adapters.normalize(source_config(), fixture(), RETRIEVED_AT)
        self.assertEqual(len(records), 4)
        self.assertEqual(
            {record["series_id"] for record in records},
            {"SURVEY.CURRENT", "SURVEY.FUTURE"},
        )
        self.assertTrue(all(
            record["publisher_field"] != "CURRENT_DOWN"
            for record in records
        ))
        self.assertEqual(records[1]["value_status"], "unavailable")
        self.assertEqual(records[-1]["value_status"], "forecast")
        self.assertEqual(records[-1]["forecast_horizon"], "six_month_expectation")
        self.assertIsNone(records[-1]["forecast_origin"])
        self.assertIsNone(records[-1]["release_at"])
        self.assertEqual(records[-1]["available_at"], RETRIEVED_AT)

    def test_header_reorder_extra_column_and_unowned_projection_fail_closed(self):
        source = source_config()
        bad_header = fixture().replace(
            b"surveyDate,CURRENT_DOWN,CURRENT_DIFFUSION,FUTURE_DIFFUSION",
            b"surveyDate,CURRENT_DIFFUSION,CURRENT_DOWN,FUTURE_DIFFUSION",
            1,
        )
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source, bad_header, RETRIEVED_AT)

        extra = fixture().replace(
            b"FUTURE_DIFFUSION\n",
            b"FUTURE_DIFFUSION,EXTRA\n",
            1,
        )
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source, extra, RETRIEVED_AT)

        source = copy.deepcopy(source)
        source["series"]["items"][0]["column"] = "NOT_IN_HEADER"
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source, fixture(), RETRIEVED_AT)

    def test_nyfed_business_leaders_contract_has_exact_65_to_16_projection(self):
        config = load_config(CONFIG_PATH)
        source = next(
            item for item in config["sources"]
            if item["source_id"] == "nyfed_business_leaders_current"
        )
        self.assertEqual(len(source["series"]["expected_header"]), 65)
        self.assertEqual(len(source["series"]["items"]), 16)
        self.assertEqual(
            len(source["series"]["expected_header"]),
            len(set(source["series"]["expected_header"])),
        )
        self.assertEqual(
            len(source["series"]["items"]),
            len({
                item["series_id"]
                for item in source["series"]["items"]
            }),
        )

    def test_bds_exact_25_column_contract_projects_only_three_damage_rates(self):
        records = adapters.normalize(
            bds_source_config(),
            bds_fixture(),
            RETRIEVED_AT,
        )
        self.assertEqual(len(records), 6)
        self.assertEqual(
            {record["series_id"] for record in records},
            {
                "CENSUS.BDS.NATIONAL.ESTABS_EXIT_RATE",
                "CENSUS.BDS.NATIONAL.JOB_DESTRUCTION_RATE_DEATHS",
                "CENSUS.BDS.NATIONAL.JOB_DESTRUCTION_RATE",
            },
        )
        self.assertEqual(
            {record["observation_period"] for record in records},
            {"1978-01-01", "1979-01-01"},
        )
        self.assertTrue(all(
            record["value_status"] == "actual"
            for record in records
        ))
        self.assertTrue(all(
            record["release_at"] is None and
            record["forecast_origin"] is None
            for record in records
        ))
        self.assertTrue(all(
            record["publisher_field"] not in {
                "firms",
                "estabs_entry_rate",
                "firmdeath_firms",
                "net_job_creation_rate",
            }
            for record in records
        ))

    def test_bds_header_date_duplicate_and_selected_value_drift_fail_closed(self):
        source = bds_source_config()
        body = bds_fixture()
        cases = (
            body.replace(
                b"year,firms,estabs",
                b"year,estabs,firms",
                1,
            ),
            body.replace(b"1978,", b"78,", 1),
            body + body.splitlines(keepends=True)[1],
            body.replace(b",2.5,30,", b",NaN,30,", 1),
        )
        for case in cases:
            with self.subTest(case=case[:60]):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(source, case, RETRIEVED_AT)


if __name__ == "__main__":
    unittest.main()
