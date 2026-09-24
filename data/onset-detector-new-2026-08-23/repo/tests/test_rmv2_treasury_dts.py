from __future__ import absolute_import

import copy
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.canonical import canonical_json_bytes
from live_data.rmv2_live.treasury_dts import (
    CURRENT_CONCEPT,
    CURRENT_CONCEPT_START,
    ENDPOINT,
    LEGACY_CONCEPT,
    METHOD_VERSION,
    SCHEMA_VERSION,
    SOURCE_ID,
    TreasuryDtsDataError,
    normalize_treasury_dts_bytes,
    parse_treasury_dts_json,
)


RETRIEVED_AT = "2026-07-29T16:00:00Z"


def _row(record_date="2026-07-28", line="44", today="2144"):
    return {
        "record_date": record_date,
        "account_type": "Treasury General Account (TGA)",
        "transaction_type": "Deposits",
        "transaction_catg": CURRENT_CONCEPT,
        "transaction_catg_desc": "null",
        "transaction_today_amt": today,
        "transaction_mtd_amt": "252277",
        "transaction_fytd_amt": "2966377",
        "table_nbr": "II",
        "table_nm": "Deposits and Withdrawals of Operating Cash",
        "src_line_nbr": line,
        "record_fiscal_year": "2026",
        "record_fiscal_quarter": "4",
        "record_calendar_year": record_date[:4],
        "record_calendar_quarter": "3",
        "record_calendar_month": record_date[5:7],
        "record_calendar_day": record_date[8:10],
    }


def _meta(count):
    labels = {
        "record_date": "Record Date",
        "account_type": "Type of Account",
        "transaction_type": "Transaction Type",
        "transaction_catg": "Transaction Category",
        "transaction_catg_desc": "Transaction Category Description",
        "transaction_today_amt": "Transactions Today",
        "transaction_mtd_amt": "Transactions Month to Date",
        "transaction_fytd_amt": "Transactions Fiscal Year to Date",
        "table_nbr": "Table Number",
        "table_nm": "Table Name",
        "src_line_nbr": "Source Line Number",
        "record_fiscal_year": "Fiscal Year",
        "record_fiscal_quarter": "Fiscal Quarter Number",
        "record_calendar_year": "Calendar Year",
        "record_calendar_quarter": "Calendar Quarter Number",
        "record_calendar_month": "Calendar Month Number",
        "record_calendar_day": "Calendar Day Number",
    }
    data_types = dict((key, "STRING") for key in labels)
    data_types["record_date"] = "DATE"
    data_types["transaction_today_amt"] = "CURRENCY0"
    data_types["transaction_mtd_amt"] = "CURRENCY0"
    data_types["transaction_fytd_amt"] = "CURRENCY0"
    data_types["src_line_nbr"] = "INTEGER"
    data_formats = dict((key, "String") for key in labels)
    data_formats["record_date"] = "YYYY-MM-DD"
    return {
        "count": count,
        "labels": labels,
        "dataTypes": data_types,
        "dataFormats": data_formats,
        "total-count": count,
        "total-pages": 1,
    }


def _payload(rows=None):
    rows = list(rows if rows is not None else [_row()])
    return {
        "data": rows,
        "meta": _meta(len(rows)),
        "links": {
            "self": "&page%5Bnumber%5D=1",
            "first": "&page%5Bnumber%5D=1",
            "prev": None,
            "next": None,
            "last": "&page%5Bnumber%5D=1",
        },
    }


def _bytes(payload):
    return canonical_json_bytes(payload)


class TreasuryDtsValidFixtureTests(unittest.TestCase):
    def test_valid_current_concept_preserves_values_and_explicit_clocks(self):
        records = parse_treasury_dts_json(_bytes(_payload()), RETRIEVED_AT)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["schema_version"], SCHEMA_VERSION)
        self.assertEqual(record["source_id"], SOURCE_ID)
        self.assertEqual(record["method_version"], METHOD_VERSION)
        self.assertEqual(record["provenance_url"], ENDPOINT)
        self.assertEqual(record["observation_period"], "2026-07-28")
        self.assertEqual(record["observed_at"], "2026-07-28")
        self.assertEqual(record["reference_start"], "2026-07-28")
        self.assertEqual(record["reference_end"], "2026-07-28")
        self.assertEqual(record["retrieved_at"], RETRIEVED_AT)
        self.assertEqual(record["available_at"], RETRIEVED_AT)
        self.assertIsNone(record["publisher_release_at"])
        self.assertIsNone(record["provider_available_at"])
        self.assertEqual(record["transaction_catg"], CURRENT_CONCEPT)
        self.assertEqual(record["transaction_catg_desc"], "null")
        self.assertEqual(record["source_line_nbr"], "44")
        self.assertEqual(record["today_amt"], "2144")
        self.assertEqual(record["mtd_amt"], "252277")
        self.assertEqual(record["fytd_amt"], "2966377")
        self.assertEqual(record["amount_unit"], "USD millions")
        self.assertEqual(record["value_status"], "actual")
        self.assertEqual(record["vintage_kind"], "self_captured_current_api")

    def test_canonical_output_is_deterministic_across_object_and_row_order(self):
        later = _row()
        earlier = _row("2026-07-27", "43", "3210")
        earlier["record_calendar_day"] = "27"
        left = _payload([later, earlier])
        right = {
            "links": dict(reversed(list(left["links"].items()))),
            "meta": dict(reversed(list(left["meta"].items()))),
            "data": [
                dict(reversed(list(earlier.items()))),
                dict(reversed(list(later.items()))),
            ],
        }
        self.assertEqual(
            normalize_treasury_dts_bytes(_bytes(left), RETRIEVED_AT),
            normalize_treasury_dts_bytes(_bytes(right), RETRIEVED_AT),
        )
        decoded = json.loads(
            normalize_treasury_dts_bytes(_bytes(right), RETRIEVED_AT)
            .decode("utf-8")
        )
        self.assertEqual(
            [item["observation_period"] for item in decoded],
            ["2026-07-27", "2026-07-28"],
        )


class TreasuryDtsBoundaryAndIdentityTests(unittest.TestCase):
    def test_legacy_concept_and_pre_start_current_rows_are_rejected(self):
        legacy = _payload()
        legacy["data"][0]["transaction_catg"] = LEGACY_CONCEPT
        with self.assertRaisesRegex(
            TreasuryDtsDataError, "legacy withheld-tax concept"
        ):
            parse_treasury_dts_json(_bytes(legacy), RETRIEVED_AT)

        pre_start = _payload()
        pre_start["data"][0]["record_date"] = "2023-02-13"
        pre_start["data"][0]["record_calendar_year"] = "2023"
        pre_start["data"][0]["record_calendar_quarter"] = "1"
        pre_start["data"][0]["record_calendar_month"] = "02"
        pre_start["data"][0]["record_calendar_day"] = "13"
        pre_start["data"][0]["record_fiscal_year"] = "2023"
        pre_start["data"][0]["record_fiscal_quarter"] = "2"
        with self.assertRaisesRegex(
            TreasuryDtsDataError, CURRENT_CONCEPT_START
        ):
            parse_treasury_dts_json(_bytes(pre_start), RETRIEVED_AT)

    def test_unknown_semantic_identities_are_rejected(self):
        mutations = (
            ("transaction_catg", "Other Cash Deposits"),
            ("account_type", "Other Account"),
            ("transaction_type", "Withdrawals"),
            ("table_nbr", "III"),
            ("table_nm", "Other Table"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                payload = _payload()
                payload["data"][0][field] = value
                with self.assertRaisesRegex(
                    TreasuryDtsDataError, "unreviewed"
                ):
                    parse_treasury_dts_json(_bytes(payload), RETRIEVED_AT)

    def test_duplicate_row_identity_is_rejected_even_if_amount_changes(self):
        first = _row()
        second = copy.deepcopy(first)
        second["transaction_today_amt"] = "9999"
        payload = _payload([first, second])
        with self.assertRaisesRegex(
            TreasuryDtsDataError, "duplicate row identities"
        ):
            parse_treasury_dts_json(_bytes(payload), RETRIEVED_AT)


class TreasuryDtsMalformedInputTests(unittest.TestCase):
    def test_unknown_response_meta_and_row_fields_are_rejected(self):
        mutations = []
        top = _payload()
        top["unexpected"] = True
        mutations.append(top)
        meta = _payload()
        meta["meta"]["future-schema"] = "drift"
        mutations.append(meta)
        nested_meta = _payload()
        nested_meta["meta"]["labels"]["future_field"] = "Future"
        mutations.append(nested_meta)
        row = _payload()
        row["data"][0]["future_field"] = "Future"
        mutations.append(row)
        for index, payload in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(TreasuryDtsDataError):
                    parse_treasury_dts_json(_bytes(payload), RETRIEVED_AT)

    def test_bad_dates_amounts_line_numbers_and_calendar_fields_are_rejected(self):
        mutations = (
            ("record_date", "2026-02-30"),
            ("transaction_today_amt", "1,234"),
            ("transaction_mtd_amt", "Infinity"),
            ("transaction_fytd_amt", "1e6"),
            ("src_line_nbr", "-1"),
            ("record_calendar_day", "27"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                payload = _payload()
                payload["data"][0][field] = value
                with self.assertRaises(TreasuryDtsDataError):
                    parse_treasury_dts_json(_bytes(payload), RETRIEVED_AT)

        numeric_amount = _payload()
        numeric_amount["data"][0]["transaction_today_amt"] = 2144
        with self.assertRaisesRegex(
            TreasuryDtsDataError, "quoted finite decimal"
        ):
            parse_treasury_dts_json(
                _bytes(numeric_amount), RETRIEVED_AT
            )

    def test_duplicate_json_keys_nonfinite_html_empty_and_bad_utf8_are_rejected(self):
        invalid = (
            b'{"data":[],"data":[],"meta":{},"links":{}}',
            b'{"data":[],"meta":{"count":NaN},"links":{}}',
            b"<!doctype html><html></html>",
            b"",
            b'{"x":"\xff"}',
        )
        for value in invalid:
            with self.subTest(value=value[:30]):
                with self.assertRaises(TreasuryDtsDataError):
                    parse_treasury_dts_json(value, RETRIEVED_AT)

    def test_meta_counts_and_shapes_must_reconcile_exactly(self):
        bad_count = _payload()
        bad_count["meta"]["count"] = 2
        bad_total = _payload()
        bad_total["meta"]["total-count"] = 0
        bad_maps = _payload()
        del bad_maps["meta"]["dataTypes"]["record_date"]
        bad_link = _payload()
        bad_link["links"]["future"] = None
        for payload in (bad_count, bad_total, bad_maps, bad_link):
            with self.assertRaises(TreasuryDtsDataError):
                parse_treasury_dts_json(_bytes(payload), RETRIEVED_AT)

    def test_retrieval_clock_is_strict_and_publisher_release_is_never_inferred(self):
        for value in (
            "2026-07-29",
            "2026-07-29T16:00:00-04:00",
            "2026-07-29T16:00:00.123Z",
            "2026-13-29T16:00:00Z",
        ):
            with self.subTest(value=value):
                with self.assertRaises(TreasuryDtsDataError):
                    parse_treasury_dts_json(_bytes(_payload()), value)


if __name__ == "__main__":
    unittest.main()
