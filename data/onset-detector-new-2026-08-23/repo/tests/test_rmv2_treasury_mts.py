from __future__ import absolute_import

import copy
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable
from live_data.rmv2_live.canonical import read_json


RETRIEVED_AT = "2026-07-30T20:00:00Z"
EXPECTED_TYPES = {
    "classification_desc": "STRING",
    "current_fytd_budget_amt": "CURRENCY",
    "current_month_budget_amt": "CURRENCY",
    "data_type_cd": "STRING",
    "line_code_nbr": "STRING",
    "prior_fytd_budget_amt": "CURRENCY",
    "record_calendar_day": "DAY",
    "record_calendar_month": "MONTH",
    "record_calendar_quarter": "QUARTER",
    "record_calendar_year": "YEAR",
    "record_date": "DATE",
    "record_fiscal_quarter": "QUARTER",
    "record_fiscal_year": "YEAR",
    "record_type_cd": "STRING",
    "src_line_nbr": "INTEGER",
    "table_nbr": "STRING",
}


def source():
    config = read_json(PROJECT_ROOT / "live_data/config/sources.v1.json")
    matches = [
        value for value in config["sources"]
        if value["source_id"] == "treasury_mts_summary_totals"
    ]
    if len(matches) != 1:
        raise AssertionError("Treasury MTS source configuration is not exact")
    return matches[0]


def row(date, line_code, current_month, current_fytd, prior_fytd):
    year, month, day = [int(value) for value in date.split("-")]
    classifications = {
        "20": ("2", "Total Receipts"),
        "50": ("5", "Total Outlays"),
        "80": ("8", "Total Surplus (+) or Deficit (-)"),
    }
    src_line, classification = classifications[line_code]
    fiscal_year = year + 1 if month >= 10 else year
    fiscal_quarter = ((month - 10) % 12) // 3 + 1
    return {
        "classification_desc": classification,
        "current_fytd_budget_amt": current_fytd,
        "current_month_budget_amt": current_month,
        "data_type_cd": "T",
        "line_code_nbr": line_code,
        "prior_fytd_budget_amt": prior_fytd,
        "record_calendar_day": str(day),
        "record_calendar_month": "%02d" % month,
        "record_calendar_quarter": str((month - 1) // 3 + 1),
        "record_calendar_year": str(year),
        "record_date": date,
        "record_fiscal_quarter": str(fiscal_quarter),
        "record_fiscal_year": str(fiscal_year),
        "record_type_cd": "SL",
        "src_line_nbr": src_line,
        "table_nbr": "2",
    }


def valid_rows():
    return [
        row("2026-03-31", "20", "100", "1000", "900"),
        row("2026-03-31", "50", "125", "1250", "1100"),
        row("2026-03-31", "80", "-25", "-250", "-200"),
        row("2026-04-30", "20", "110", "1110", "990"),
        row("2026-04-30", "50", "140", "1390", "1210"),
        row("2026-04-30", "80", "-30", "-280", "-220"),
    ]


def body(rows):
    fields = list(EXPECTED_TYPES)
    payload = {
        "data": rows,
        "links": {
            "first": "",
            "last": "",
            "next": None,
            "prev": None,
            "self": "",
        },
        "meta": {
            "count": str(len(rows)),
            "dataFormats": {field: "String" for field in fields},
            "dataTypes": dict(EXPECTED_TYPES),
            "labels": {field: field for field in fields},
            "total-count": str(len(rows)),
            "total-pages": "1",
        },
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class TreasuryMtsTests(unittest.TestCase):
    def test_valid_totals_emit_nine_stable_series_per_month(self):
        records = adapters.parse_treasury_mts_totals_json(
            source(), body(valid_rows()), RETRIEVED_AT
        )
        self.assertEqual(len(records), 18)
        self.assertEqual(
            sorted({record["series_id"] for record in records}),
            [
                "TREASURY.MTS.DEFICIT_SURPLUS.CURRENT_FYTD",
                "TREASURY.MTS.DEFICIT_SURPLUS.CURRENT_MONTH",
                "TREASURY.MTS.DEFICIT_SURPLUS.PRIOR_FYTD",
                "TREASURY.MTS.OUTLAYS.CURRENT_FYTD",
                "TREASURY.MTS.OUTLAYS.CURRENT_MONTH",
                "TREASURY.MTS.OUTLAYS.PRIOR_FYTD",
                "TREASURY.MTS.RECEIPTS.CURRENT_FYTD",
                "TREASURY.MTS.RECEIPTS.CURRENT_MONTH",
                "TREASURY.MTS.RECEIPTS.PRIOR_FYTD",
            ],
        )
        values = {
            (record["observation_period"], record["series_id"]): record["value"]
            for record in records
        }
        self.assertEqual(
            values[
                (
                    "2026-03-31",
                    "TREASURY.MTS.DEFICIT_SURPLUS.CURRENT_MONTH",
                )
            ],
            "-25",
        )
        self.assertTrue(all(record["value_status"] == "actual" for record in records))
        self.assertTrue(
            all(
                record["provider_vintage_kind"] == "current_revised"
                and record["strict_publisher_first_release_proven"] is False
                for record in records
            )
        )

    def test_missing_or_substituted_total_line_fails_closed(self):
        missing = valid_rows()
        del missing[2]
        with self.assertRaises(SourceUnavailable):
            adapters.parse_treasury_mts_totals_json(
                source(), body(missing), RETRIEVED_AT
            )
        substituted = valid_rows()
        substituted[2]["classification_desc"] = "Net operating balance"
        with self.assertRaises(SourceUnavailable):
            adapters.parse_treasury_mts_totals_json(
                source(), body(substituted), RETRIEVED_AT
            )

    def test_broken_accounting_or_calendar_identity_fails_closed(self):
        broken = valid_rows()
        broken[2]["current_month_budget_amt"] = "-24"
        with self.assertRaises(SourceUnavailable):
            adapters.parse_treasury_mts_totals_json(
                source(), body(broken), RETRIEVED_AT
            )
        broken = valid_rows()
        broken[0]["record_calendar_month"] = "2"
        with self.assertRaises(SourceUnavailable):
            adapters.parse_treasury_mts_totals_json(
                source(), body(broken), RETRIEVED_AT
            )

    def test_duplicate_or_skipped_month_fails_closed(self):
        duplicated = valid_rows()
        duplicated.append(copy.deepcopy(duplicated[0]))
        with self.assertRaises(SourceUnavailable):
            adapters.parse_treasury_mts_totals_json(
                source(), body(duplicated), RETRIEVED_AT
            )
        skipped = valid_rows()
        skipped[3:] = [
            row("2026-05-31", "20", "110", "1110", "990"),
            row("2026-05-31", "50", "140", "1390", "1210"),
            row("2026-05-31", "80", "-30", "-280", "-220"),
        ]
        with self.assertRaises(SourceUnavailable):
            adapters.parse_treasury_mts_totals_json(
                source(), body(skipped), RETRIEVED_AT
            )


if __name__ == "__main__":
    unittest.main()
