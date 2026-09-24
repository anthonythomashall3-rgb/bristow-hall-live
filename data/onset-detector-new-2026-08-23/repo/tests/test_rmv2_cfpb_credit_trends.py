from __future__ import absolute_import

import copy
import csv
import io
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable
from live_data.rmv2_live.config import load_config


RETRIEVED_AT = "2026-07-30T06:00:00Z"
CONFIG_PATH = PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"
HEADER = (
    "month",
    "date",
    "series",
    "subgroup",
    "subgroup_level",
    "loan_type",
    "value_type",
    "value",
    "value_yoy",
)
SERIES_LOANS = (
    ("Credit Tightness Index", ("AUT", "CRC", "MTG")),
    ("Dollar Volume", ("AUT", "CRC", "MTG", "STU")),
    ("Inquiry Index", ("AUT", "CRC", "MTG")),
    ("Originations", ("AUT", "CRC", "MTG", "STU")),
)
VALUE_TYPES = ("Seasonally Adjusted", "Unadjusted")


def source_config():
    return {
        "adapter": "cfpb_credit_trends_csv",
        "allowed_hosts": ["files.consumerfinance.gov"],
        "coverage_source_ids": ["cfpb_credit_trends"],
        "enabled": True,
        "endpoint": (
            "https://files.consumerfinance.gov/data/"
            "consumer-credit-trends/all_data.csv"
        ),
        "expected_content_types": ["text/csv", "application/octet-stream"],
        "frequency": "monthly",
        "information_set_mode": "current_revised",
        "label": "CFPB Consumer Credit Trends national published estimates",
        "max_bytes": 10000000,
        "method_version": "cfpb_credit_trends_national_current.v1",
        "poll_seconds": 21600,
        "publisher": "Consumer Financial Protection Bureau",
        "publisher_release_clock": (
            "monthly; exact publisher release time remains null unless "
            "directly proven"
        ),
        "rights_status": (
            "published_output_with_proprietary_source_microdata"
        ),
        "secret_env": None,
        "secret_required": False,
        "series": {},
        "source_id": "cfpb_credit_trends_current",
        "value_status": "model_estimate",
    }


def fixture(
    date_value="2026-04",
    month_value="315",
    value="10",
    value_yoy=".25",
):
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(HEADER)
    for series, loans in SERIES_LOANS:
        for loan_type in loans:
            for value_type in VALUE_TYPES:
                writer.writerow((
                    month_value,
                    date_value,
                    series,
                    "all",
                    "all",
                    loan_type,
                    value_type,
                    value,
                    value_yoy,
                ))
    return stream.getvalue().encode("utf-8")


class CfpbCreditTrendsTests(unittest.TestCase):
    def test_exact_national_identity_set_projects_value_and_yoy_without_float(self):
        records = adapters.normalize(source_config(), fixture(), RETRIEVED_AT)

        self.assertEqual(len(records), 56)
        self.assertEqual(len({row["series_id"] for row in records}), 56)
        self.assertTrue(all(
            row["observation_period"] == "2026-04-01"
            for row in records
        ))
        self.assertTrue(all(
            row["publisher_revision_status"] ==
            "recent_six_month_values_may_be_nonfinal"
            for row in records
        ))
        value = next(
            row for row in records
            if row["series_id"] ==
            "CFPB.CCT.ORIGINATIONS.AUT.NSA.VALUE"
        )
        yoy = next(
            row for row in records
            if row["series_id"] ==
            "CFPB.CCT.ORIGINATIONS.AUT.NSA.YOY_PCT"
        )
        self.assertEqual(value["value"], "10")
        self.assertEqual(value["unit"], "estimated loan count")
        self.assertEqual(value["value_status"], "model_estimate")
        self.assertEqual(yoy["value"], "0.25")
        self.assertEqual(yoy["unit"], "percent change year over year")
        self.assertFalse(yoy["strict_publisher_first_release_proven"])

    def test_missing_yoy_remains_unavailable_and_non_national_rows_are_not_projected(self):
        body = fixture(value_yoy="")
        extra = (
            "315,2026-04,Originations,score,Near Prime,AUT,"
            "Unadjusted,20,8.5e-06\n"
        ).encode("utf-8")
        records = adapters.normalize(
            source_config(),
            body + extra,
            RETRIEVED_AT,
        )

        self.assertEqual(len(records), 56)
        self.assertEqual(
            sum(row["value_status"] == "unavailable" for row in records),
            28,
        )
        self.assertTrue(all(
            row["publisher_identity"]["subgroup"] == "all"
            for row in records
        ))

    def test_nonfinal_window_is_computed_per_publisher_identity(self):
        body = fixture(date_value="2025-08", month_value="307")
        newer_inquiry = (
            "315,2026-04,Inquiry Index,all,all,AUT,"
            "Seasonally Adjusted,20,.5\n"
        ).encode("utf-8")
        records = adapters.normalize(
            source_config(),
            body + newer_inquiry,
            RETRIEVED_AT,
        )

        older_identity = next(
            row for row in records
            if row["series_id"] ==
            "CFPB.CCT.ORIGINATIONS.AUT.NSA.VALUE"
        )
        old_inquiry = next(
            row for row in records
            if row["series_id"] ==
            "CFPB.CCT.INQUIRY_INDEX.AUT.SA.VALUE" and
            row["publisher_period"] == "2025-08"
        )
        self.assertEqual(
            older_identity["publisher_revision_status"],
            "recent_six_month_values_may_be_nonfinal",
        )
        self.assertEqual(
            old_inquiry["publisher_revision_status"],
            "historical_current_revised_capture",
        )

    def test_schema_identity_date_and_decimal_drift_fail_closed(self):
        duplicate_row = fixture().splitlines()[1] + b"\n"
        mutations = (
            fixture().replace(
                b"month,date,series",
                b"date,month,series",
                1,
            ),
            fixture(month_value="314"),
            fixture(value="NaN"),
            fixture(value="1e"),
            fixture(value="-1"),
            fixture() + (
                b"315,2026-04,Originations,score,620-659,AUT,"
                b"Unadjusted,20,.5\n"
            ),
            fixture() + (
                b"315,2026-04,Inquiry Index,age,30-44,AUT,"
                b"Unadjusted,20,.5\n"
            ),
            fixture() + (
                b"315,2026-04,Originations,map,AL,AUT,"
                b"Unadjusted,20,.5\n"
            ),
            fixture() + (
                b"315,2026-04,Dollar Volume,map,AL,AUT,"
                b"Seasonally Adjusted,20,.5\n"
            ),
            fixture().replace(
                b"Credit Tightness Index,all,all,AUT",
                b"Credit Tightness Index,all,all,STU",
                1,
            ),
            fixture() + duplicate_row,
        )
        for body in mutations:
            with self.subTest(prefix=body[:80]):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(source_config(), body, RETRIEVED_AT)

    def test_source_metadata_must_be_empty_and_exact(self):
        source = source_config()
        source["series"] = {"default": "forbidden"}
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source, fixture(), RETRIEVED_AT)

    def test_live_config_is_exact_and_non_first_release(self):
        config = load_config(CONFIG_PATH)
        source = next(
            item for item in config["sources"]
            if item["source_id"] == "cfpb_credit_trends_current"
        )
        self.assertEqual(source["adapter"], "cfpb_credit_trends_csv")
        self.assertEqual(
            source["coverage_source_ids"],
            ["cfpb_credit_trends"],
        )
        self.assertEqual(source["information_set_mode"], "current_revised")
        self.assertEqual(source["value_status"], "model_estimate")
        self.assertEqual(source["series"], {})


if __name__ == "__main__":
    unittest.main()
