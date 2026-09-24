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


RETRIEVED_AT = "2026-07-29T20:00:00Z"


def source_config(adapter, series):
    return {
        "adapter": adapter,
        "allowed_hosts": ["publisher.example"],
        "coverage_source_ids": ["test_family"],
        "enabled": True,
        "endpoint": "https://publisher.example/data",
        "expected_content_types": ["text/csv", "application/json"],
        "frequency": "monthly",
        "information_set_mode": "current_revised",
        "label": "Official test source",
        "max_bytes": 1000000,
        "method_version": "official_tabular_test.v1",
        "poll_seconds": 3600,
        "publisher": "Official test publisher",
        "publisher_release_clock": "publisher clock",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": series,
        "source_id": "official_tabular_test",
        "value_status": "model_estimate",
    }


def csv_source():
    return source_config("tabular_csv", {
        "date_column": "Date",
        "date_format": "%m/%d/%Y",
        "items": [
            {
                "column": "Weekly Index",
                "forecast_horizon": None,
                "label": "Published weekly activity index",
                "series_id": "CARTS.WEEKLY",
                "unit": "index",
                "value_status": "model_estimate",
            },
            {
                "column": "Published Actual",
                "forecast_horizon": None,
                "label": "Published monthly actual",
                "series_id": "CARTS.ACTUAL",
                "unit": "USD millions",
                "value_status": "actual",
            },
            {
                "column": "Projection",
                "forecast_horizon": "publisher_current_month_projection",
                "label": "Published current-month projection",
                "series_id": "CARTS.PROJECTION",
                "unit": "USD millions",
                "value_status": "forecast",
            },
        ],
        "missing_tokens": [""],
    })


def socrata_source():
    return source_config("socrata_json", {
        "date_field": "obs_date",
        "date_format": "%Y-%m-%dT00:00:00.000",
        "identity_field": "id",
        "items": [
            {
                "field": "tsi_freight",
                "forecast_horizon": None,
                "label": "Freight Transportation Services Index",
                "series_id": "BTS.TSI.FREIGHT",
                "unit": "index",
                "value_status": "model_estimate",
            },
            {
                "field": "tsi_passenger",
                "forecast_horizon": None,
                "label": "Passenger Transportation Services Index",
                "series_id": "BTS.TSI.PASSENGER",
                "unit": "index",
                "value_status": "model_estimate",
            },
            {
                "field": "tsi_total",
                "forecast_horizon": None,
                "label": "Total Transportation Services Index",
                "series_id": "BTS.TSI.TOTAL",
                "unit": "index",
                "value_status": "model_estimate",
            },
        ],
    })


def fiscaldata_source(
    date_fields=None,
    dimension_fields=None,
    identity_fields=None,
    item_date_fields=None,
    context_fields=None,
):
    date_fields = list(date_fields or ["record_date"])
    dimension_fields = list(dimension_fields or [])
    identity_fields = list(identity_fields or ["record_date"])
    item_date_fields = list(item_date_fields or [date_fields[0], date_fields[0]])
    context_fields = list(context_fields or [])
    expected_data_types = {}
    for field in date_fields:
        expected_data_types[field] = "DATE"
    for field in dimension_fields:
        expected_data_types[field] = (
            "INTEGER" if field == "src_line_nbr" else "STRING"
        )
    for field in identity_fields:
        expected_data_types.setdefault(
            field,
            "INTEGER" if field == "src_line_nbr" else "STRING",
        )
    for field in context_fields:
        expected_data_types[field] = "YEAR"
    expected_data_types["total_amount"] = "CURRENCY"
    expected_data_types["rate_pct"] = "PERCENTAGE"
    return source_config("fiscaldata_json", {
        "date_fields": date_fields,
        "dimension_fields": dimension_fields,
        "expected_data_types": expected_data_types,
        "identity_fields": identity_fields,
        "items": [
            {
                "event_date_field": item_date_fields[0],
                "field": "total_amount",
                "forecast_horizon": None,
                "label": "Official total amount",
                "series_id": "TREASURY.TEST.TOTAL",
                "unit": "USD",
                "value_status": "actual",
            },
            {
                "event_date_field": item_date_fields[1],
                "field": "rate_pct",
                "forecast_horizon": None,
                "label": "Official rate",
                "series_id": "TREASURY.TEST.RATE",
                "unit": "percent",
                "value_status": "actual",
            },
        ],
        "missing_tokens": ["null"],
    })


def fiscaldata_payload(rows, expected_data_types):
    fields = list(expected_data_types)
    return {
        "data": rows,
        "links": {
            "first": "",
            "last": "",
            "next": None,
            "prev": None,
            "self": "",
        },
        "meta": {
            "count": len(rows),
            "dataFormats": {field: "String" for field in fields},
            "dataTypes": dict(expected_data_types),
            "labels": {field: field for field in fields},
            "total-count": len(rows),
            "total-pages": 1,
        },
    }


def tsa_source():
    source = source_config("tsa_passenger_html", {})
    source["value_status"] = "actual"
    return source


def fhfa_source():
    source = source_config("fhfa_hpi_csv", {})
    source["source_id"] = "fhfa_hpi_monthly_us"
    source["value_status"] = "actual"
    return source


def ofr_source():
    source = source_config("ofr_fsi_csv", {})
    source["source_id"] = "ofr_fsi_daily"
    source["value_status"] = "model_estimate"
    return source


def fdic_source():
    source = source_config("fdic_aggregate_json", {})
    source["source_id"] = "fdic_banking_aggregate_quarterly"
    source["value_status"] = "actual"
    return source


class OfficialTabularAdapterTests(unittest.TestCase):
    def test_tabular_csv_preserves_exact_item_statuses_and_missingness(self):
        body = (
            "Date,Weekly Index,Published Actual,Projection\r\n"
            "01/07/2026,610.25,,\r\n"
            "01/14/2026,612.50,611.75,613.25\r\n"
        ).encode("utf-8")
        rows = adapters.normalize(csv_source(), body, RETRIEVED_AT)

        self.assertEqual(len(rows), 6)
        self.assertEqual(
            [(row["observation_period"], row["series_id"]) for row in rows],
            [
                ("2026-01-07", "CARTS.WEEKLY"),
                ("2026-01-07", "CARTS.ACTUAL"),
                ("2026-01-07", "CARTS.PROJECTION"),
                ("2026-01-14", "CARTS.WEEKLY"),
                ("2026-01-14", "CARTS.ACTUAL"),
                ("2026-01-14", "CARTS.PROJECTION"),
            ],
        )
        self.assertEqual(rows[0]["value_status"], "model_estimate")
        self.assertEqual(rows[1]["value_status"], "unavailable")
        self.assertIsNone(rows[1]["value"])
        self.assertEqual(rows[2]["value_status"], "unavailable")
        self.assertEqual(rows[5]["value_status"], "forecast")
        self.assertEqual(
            rows[5]["forecast_horizon"],
            "publisher_current_month_projection",
        )
        self.assertIsNone(rows[5]["forecast_origin"])
        self.assertIsNone(rows[5]["release_at"])
        self.assertEqual(rows[5]["available_at"], RETRIEVED_AT)
        self.assertFalse(rows[0]["strict_publisher_first_release_proven"])
        self.assertEqual(rows[0]["provider_vintage_kind"], "current_revised")

    def test_tabular_csv_rejects_header_date_identity_and_numeric_drift(self):
        valid = (
            "Date,Weekly Index,Published Actual,Projection\r\n"
            "01/07/2026,610.25,,\r\n"
        ).encode("utf-8")
        mutations = (
            valid.replace(b"Projection", b"Projection Renamed"),
            valid + b"01/07/2026,611.00,,\r\n",
            valid.replace(b"01/07/2026", b"2026-01-07"),
            valid.replace(b"610.25", b"610.25*"),
            valid.replace(b"610.25", b"NaN"),
        )
        for body in mutations:
            with self.subTest(body=body):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(csv_source(), body, RETRIEVED_AT)

    def test_tabular_csv_supports_explicit_1968_two_digit_month_pivot(self):
        source = source_config("tabular_csv", {
            "date_column": "DATE",
            "date_format": "month_abbrev_two_digit_year_pivot_1968",
            "items": [{
                "column": "GAC",
                "forecast_horizon": None,
                "label": "General activity current diffusion index",
                "series_id": "PHILLY.MBOS.GAC",
                "unit": "diffusion index points",
                "value_status": "model_estimate",
            }],
            "missing_tokens": [""],
        })
        rows = adapters.normalize(
            source,
            b"DATE,GAC\r\nMay-68,32.2\r\nJan-00,-6.5\r\nJul-26,15.2\r\n",
            RETRIEVED_AT,
        )
        self.assertEqual(
            [row["observation_period"] for row in rows],
            ["1968-05-01", "2000-01-01", "2026-07-01"],
        )
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                source,
                b"DATE,GAC\r\nMAY-68,32.2\r\n",
                RETRIEVED_AT,
            )

    def test_socrata_json_projects_only_configured_fields_and_exact_clocks(self):
        body = json.dumps([
            {
                "id": "SATD202605",
                "obs_date": "2026-05-01T00:00:00.000",
                "tsi_freight": "142.1",
                "tsi_passenger": "131.0",
                "tsi_total": "139.4",
                "publisher_extra_field": "retained outside the projection",
            }
        ], sort_keys=True, separators=(",", ":")).encode("utf-8")
        rows = adapters.normalize(socrata_source(), body, RETRIEVED_AT)

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [row["series_id"] for row in rows],
            ["BTS.TSI.FREIGHT", "BTS.TSI.PASSENGER", "BTS.TSI.TOTAL"],
        )
        self.assertEqual(
            {row["observation_period"] for row in rows},
            {"2026-05-01"},
        )
        self.assertEqual(
            {row["publisher_row_identity"] for row in rows},
            {"SATD202605"},
        )
        self.assertTrue(all(
            row["value_status"] == "model_estimate"
            for row in rows
        ))

    def test_socrata_archive_lane_is_not_relabelled_current_revised(self):
        source = socrata_source()
        source["information_set_mode"] = "archive_snapshot_asof"
        body = json.dumps([{
            "id": "SATD202605",
            "obs_date": "2026-05-01T00:00:00.000",
            "tsi_freight": "142.1",
            "tsi_passenger": "131.0",
            "tsi_total": "139.4",
        }]).encode("utf-8")
        rows = adapters.normalize(source, body, RETRIEVED_AT)
        self.assertEqual(
            {row["provider_vintage_kind"] for row in rows},
            {"archive_snapshot_asof"},
        )
        self.assertEqual(
            {row["information_set_mode"] for row in rows},
            {"archive_snapshot_asof"},
        )

    def test_socrata_json_rejects_duplicate_ids_bad_rows_dates_and_numbers(self):
        valid = [{
            "id": "SATD202605",
            "obs_date": "2026-05-01T00:00:00.000",
            "tsi_freight": "142.1",
            "tsi_passenger": "131.0",
            "tsi_total": "139.4",
        }]
        mutations = (
            valid + [copy.deepcopy(valid[0])],
            ["not-an-object"],
            [dict(valid[0], obs_date="2026-05-01")],
            [dict(valid[0], tsi_total="Infinity")],
            [dict(valid[0], id="")],
        )
        for payload in mutations:
            with self.subTest(payload=payload):
                body = json.dumps(payload).encode("utf-8")
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(socrata_source(), body, RETRIEVED_AT)

    def test_fiscaldata_json_projects_national_rows_and_nulls(self):
        source = fiscaldata_source(context_fields=["record_fiscal_year"])
        payload = fiscaldata_payload(
            [
                {
                    "record_date": "2026-07-28",
                    "record_fiscal_year": "2026",
                    "total_amount": "39797152899275.21",
                    "rate_pct": "null",
                },
                {
                    "record_date": "2026-07-27",
                    "record_fiscal_year": "2026",
                    "total_amount": "39713964053447.11",
                    "rate_pct": "3.18880060",
                },
            ],
            source["series"]["expected_data_types"],
        )
        rows = adapters.normalize(
            source,
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            RETRIEVED_AT,
        )

        self.assertEqual(len(rows), 4)
        self.assertEqual(
            [(row["observation_period"], row["series_id"]) for row in rows],
            [
                ("2026-07-28", "TREASURY.TEST.TOTAL"),
                ("2026-07-28", "TREASURY.TEST.RATE"),
                ("2026-07-27", "TREASURY.TEST.TOTAL"),
                ("2026-07-27", "TREASURY.TEST.RATE"),
            ],
        )
        self.assertEqual(rows[0]["value"], "39797152899275.21")
        self.assertEqual(rows[1]["value_status"], "unavailable")
        self.assertIsNone(rows[1]["value"])
        self.assertEqual(rows[3]["value"], "3.18880060")
        self.assertFalse(rows[0]["strict_publisher_first_release_proven"])
        self.assertEqual(rows[0]["provider_vintage_kind"], "current_revised")
        self.assertEqual(
            rows[0]["publisher_context"],
            {"record_fiscal_year": "2026"},
        )

    def test_fiscaldata_json_preserves_dimensions_context_and_unique_series(self):
        source = fiscaldata_source(
            dimension_fields=["state_nm", "src_line_nbr"],
            identity_fields=["record_date", "state_nm", "src_line_nbr"],
        )
        payload = fiscaldata_payload(
            [
                {
                    "record_date": "2026-07-28",
                    "state_nm": "California",
                    "src_line_nbr": "1",
                    "total_amount": "18979949857.45",
                    "rate_pct": "3.18880060",
                },
                {
                    "record_date": "2026-07-28",
                    "state_nm": "Virgin Islands",
                    "src_line_nbr": "4",
                    "total_amount": "0.00",
                    "rate_pct": "3.18880060",
                },
            ],
            source["series"]["expected_data_types"],
        )
        rows = adapters.normalize(
            source,
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            RETRIEVED_AT,
        )

        self.assertEqual(len(rows), 4)
        self.assertEqual(
            {tuple(sorted(row["publisher_dimensions"].items())) for row in rows},
            {
                (("src_line_nbr", "1"), ("state_nm", "California")),
                (("src_line_nbr", "4"), ("state_nm", "Virgin Islands")),
            },
        )
        total_ids = {
            row["series_id"]
            for row in rows
            if row["publisher_field"] == "total_amount"
        }
        self.assertEqual(len(total_ids), 2)
        self.assertTrue(all(
            series_id.startswith("TREASURY.TEST.TOTAL.")
            for series_id in total_ids
        ))
        self.assertEqual(
            len({row["publisher_row_identity"] for row in rows}),
            2,
        )

    def test_fiscaldata_json_uses_item_event_clocks_without_future_leakage(self):
        source = fiscaldata_source(
            date_fields=[
                "announcemt_date",
                "auction_date",
                "issue_date",
                "maturity_date",
            ],
            dimension_fields=["cusip"],
            identity_fields=["cusip", "auction_date"],
            item_date_fields=["announcemt_date", "auction_date"],
        )
        payload = fiscaldata_payload(
            [{
                "announcemt_date": "2026-07-28",
                "auction_date": "2026-07-30",
                "issue_date": "2026-08-04",
                "maturity_date": "2026-09-29",
                "cusip": "912797VE4",
                "total_amount": "100000000000",
                "rate_pct": "null",
            }],
            source["series"]["expected_data_types"],
        )
        rows = adapters.normalize(
            source,
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            RETRIEVED_AT,
        )
        self.assertEqual(rows[0]["observation_period"], "2026-07-28")
        self.assertEqual(rows[1]["observation_period"], "2026-07-30")
        self.assertEqual(
            rows[0]["publisher_clocks"],
            {
                "announcemt_date": "2026-07-28",
                "auction_date": "2026-07-30",
                "issue_date": "2026-08-04",
                "maturity_date": "2026-09-29",
            },
        )
        self.assertEqual(rows[1]["value_status"], "unavailable")
        self.assertEqual(rows[0]["available_at"], RETRIEVED_AT)

    def test_fiscaldata_json_rejects_schema_identity_date_and_number_drift(self):
        source = fiscaldata_source(
            dimension_fields=["state_nm", "src_line_nbr"],
            identity_fields=["record_date", "state_nm", "src_line_nbr"],
        )
        valid_row = {
            "record_date": "2026-07-28",
            "state_nm": "California",
            "src_line_nbr": "1",
            "total_amount": "18979949857.45",
            "rate_pct": "3.18880060",
        }
        valid_payload = fiscaldata_payload(
            [valid_row],
            source["series"]["expected_data_types"],
        )
        mutations = (
            [],
            {"data": "not-a-list"},
            {"data": ["not-an-object"]},
            fiscaldata_payload(
                [dict(valid_row, record_date="07/28/2026")],
                source["series"]["expected_data_types"],
            ),
            fiscaldata_payload(
                [dict(valid_row, state_nm="")],
                source["series"]["expected_data_types"],
            ),
            fiscaldata_payload(
                [dict(valid_row, src_line_nbr={"bad": "shape"})],
                source["series"]["expected_data_types"],
            ),
            fiscaldata_payload(
                [dict(valid_row, total_amount="NaN")],
                source["series"]["expected_data_types"],
            ),
            fiscaldata_payload(
                [dict(valid_row), dict(valid_row)],
                source["series"]["expected_data_types"],
            ),
            dict(valid_payload, unexpected={}),
            dict(
                valid_payload,
                meta=dict(valid_payload["meta"], **{"total-pages": 2}),
            ),
            dict(
                valid_payload,
                links=dict(valid_payload["links"], next="page-2"),
            ),
        )
        for payload in mutations:
            with self.subTest(payload=payload):
                body = json.dumps(payload).encode("utf-8")
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(source, body, RETRIEVED_AT)

    def test_tsa_html_scraper_extracts_only_exact_observed_daily_table(self):
        body = (
            "<!DOCTYPE html><html><body>"
            "<table><tr><th>Ignore</th></tr><tr><td>42</td></tr></table>"
            "<table class=\"table\"><thead><tr><th>Date</th><th>Numbers</th>"
            "</tr></thead><tbody>"
            "<tr><td class=\"text-align-center\">7/28/2026</td>"
            "<td class=\"text-align-center\">2,332,028</td></tr>"
            "<tr><td>1/1/2026</td><td>2,334,465</td></tr>"
            "</tbody></table></body></html>"
        ).encode("utf-8")
        rows = adapters.normalize(tsa_source(), body, RETRIEVED_AT)
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            [(row["observation_period"], row["value"]) for row in rows],
            [
                ("2026-07-28", "2332028"),
                ("2026-01-01", "2334465"),
            ],
        )
        self.assertEqual({row["series_id"] for row in rows}, {
            "TSA.CHECKPOINT_THROUGHPUT",
        })
        self.assertEqual({row["value_status"] for row in rows}, {"actual"})
        self.assertEqual({row["unit"] for row in rows}, {"persons"})
        self.assertFalse(rows[0]["strict_publisher_first_release_proven"])
        self.assertEqual(rows[0]["provider_vintage_kind"], "current_revised")

    def test_tsa_html_scraper_rejects_header_date_count_and_duplicate_drift(self):
        templates = (
            "<table class=\"table\"><tr><th>Day</th><th>Numbers</th></tr>"
            "<tr><td>7/28/2026</td><td>2,332,028</td></tr></table>",
            "<table class=\"table\"><tr><th>Date</th><th>Numbers</th></tr>"
            "<tr><td>2026-07-28</td><td>2,332,028</td></tr></table>",
            "<table class=\"table\"><tr><th>Date</th><th>Numbers</th></tr>"
            "<tr><td>7/28/2026</td><td>2.332.028</td></tr></table>",
            "<table class=\"table\"><tr><th>Date</th><th>Numbers</th></tr>"
            "<tr><td>7/28/2026</td><td>2,332,028</td></tr>"
            "<tr><td>7/28/2026</td><td>2,332,028</td></tr></table>",
            "<html><body>No passenger table</body></html>",
        )
        for html in templates:
            with self.subTest(html=html):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(
                        tsa_source(),
                        html.encode("utf-8"),
                        RETRIEVED_AT,
                    )

    def test_fhfa_hpi_extracts_only_exact_national_monthly_purchase_only_rows(self):
        body = (
            b"hpi_type,hpi_flavor,frequency,level,place_name,place_id,yr,period,"
            b"index_nsa,index_sa,rstderr,note\r\n"
            b"traditional,purchase-only,monthly,USA or Census Division,"
            b"United States,USA,2024,1,200.10,201.20,,\r\n"
            b"traditional,purchase-only,monthly,USA or Census Division,"
            b"East North Central Division,DV_ENC,2024,1,190.0,191.0,,\r\n"
            b"traditional,purchase-only,monthly,USA or Census Division,"
            b"United States,USA,2024,2,201.10,202.20,,revised\r\n"
        )
        rows = adapters.normalize(fhfa_source(), body, RETRIEVED_AT)
        self.assertEqual(len(rows), 6)
        self.assertEqual(
            [(row["observation_period"], row["series_id"]) for row in rows],
            [
                ("2024-01-01", "FHFA.HPI.PO.USA.NSA"),
                ("2024-01-01", "FHFA.HPI.PO.USA.SA"),
                ("2024-01-01", "FHFA.HPI.PO.USA.RSTDERR"),
                ("2024-02-01", "FHFA.HPI.PO.USA.NSA"),
                ("2024-02-01", "FHFA.HPI.PO.USA.SA"),
                ("2024-02-01", "FHFA.HPI.PO.USA.RSTDERR"),
            ],
        )
        self.assertEqual(rows[0]["value"], "200.10")
        self.assertIsNone(rows[2]["value"])
        self.assertEqual(rows[2]["value_status"], "unavailable")
        self.assertEqual(rows[3]["publisher_context"]["note"], "revised")

    def test_ofr_fsi_preserves_exact_scientific_decimal_and_contributions(self):
        body = (
            b"Date,OFR FSI,Credit,Equity valuation,Safe assets,Funding,"
            b"Volatility,United States,Other advanced economies,"
            b"Emerging markets\n"
            b"2024-01-02,-0.1,0.1,-0.2,0.0,-9.076749291912794e-05,-0.01,"
            b"-0.08,-0.01,-0.01\n"
        )
        rows = adapters.normalize(ofr_source(), body, RETRIEVED_AT)
        self.assertEqual(len(rows), 9)
        by_series = {row["series_id"]: row for row in rows}
        self.assertEqual(by_series["OFR.FSI.TOTAL"]["value"], "-0.1")
        self.assertEqual(
            by_series["OFR.FSI.FUNDING"]["value"],
            "-0.00009076749291912794",
        )
        self.assertEqual(
            {row["value_status"] for row in rows},
            {"model_estimate"},
        )

    def test_fdic_quarterly_aggregate_preserves_integer_units_and_ytd_semantics(self):
        body = json.dumps(
            {
                "meta": {},
                "data": [
                    {
                        "data": {
                            "REPDTE": "20240630",
                            "count": 4610,
                            "sum_ASSET": 24102985567,
                            "sum_DEP": 18920503721,
                            "sum_LNLSNET": 12419352275,
                            "sum_NETINC": 137251415,
                        }
                    }
                ],
                "totals": {},
            },
            separators=(",", ":"),
        ).encode("utf-8")
        rows = adapters.normalize(fdic_source(), body, RETRIEVED_AT)
        self.assertEqual(len(rows), 5)
        by_series = {row["series_id"]: row for row in rows}
        self.assertEqual(
            by_series["FDIC.BANKS.ASSETS"]["value"],
            "24102985567",
        )
        self.assertEqual(
            by_series["FDIC.BANKS.NET_INCOME_YTD"]["unit"],
            "USD thousands year-to-date",
        )
        self.assertEqual(
            by_series["FDIC.BANKS.NET_INCOME_YTD"]["publisher_context"][
                "flow_semantics"
            ],
            "year_to_date_not_single_quarter",
        )

    def test_free_official_adapters_fail_closed_on_duplicates_and_schema_drift(self):
        bad_fhfa = (
            b"hpi_type,hpi_flavor,frequency,level,place_name,place_id,yr,period,"
            b"index_nsa,index_sa,rstderr,note\r\n"
            b"traditional,purchase-only,monthly,USA or Census Division,"
            b"United States,USA,2024,1,200.10,201.20,,\r\n"
        )
        duplicate_fhfa = bad_fhfa + bad_fhfa.split(b"\r\n", 1)[1]
        bad_ofr = (
            b"Date,OFR FSI,Credit,Equity valuation,Safe assets,Funding,"
            b"Volatility,United States,Other advanced economies,Renamed\n"
        )
        duplicate_fdic_key = (
            b'{"meta":{},"data":[],"data":[],"totals":{}}'
        )
        for source, body in (
            (fhfa_source(), duplicate_fhfa),
            (ofr_source(), bad_ofr),
            (fdic_source(), duplicate_fdic_key),
        ):
            with self.subTest(source=source["source_id"]):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(source, body, RETRIEVED_AT)


def fhfa_at_state_source():
    src = source_config("fhfa_hpi_at_geo_csv", {
        "layout": "state",
        "geography_type": "state_or_dc",
        "index_semantics": "all_transactions_purchase_and_refinance",
        "series_id_prefix": "FHFA.HPI.AT.STATE",
        "index_unit": "index",
    })
    src["value_status"] = "actual"
    return src


def fhfa_at_metro_source():
    src = source_config("fhfa_hpi_at_geo_csv", {
        "layout": "metro",
        "geography_type": "cbsa_metro",
        "index_semantics": "all_transactions_purchase_and_refinance",
        "series_id_prefix": "FHFA.HPI.AT.METRO",
        "index_unit": "index",
        "stderr_unit": "index standard error",
    })
    src["value_status"] = "actual"
    return src


class FhfaHpiAtGeoCsvTest(unittest.TestCase):
    def test_state_projects_one_series_per_place(self):
        body = b"AK,1975,1,62.03\nAK,1975,2,63.69\nDC,2026,1,519.43\n"
        rows = adapters.normalize(
            fhfa_at_state_source(), body, RETRIEVED_AT)
        self.assertEqual(len(rows), 3)
        first = rows[0]
        self.assertEqual(first["series_id"], "FHFA.HPI.AT.STATE.AK")
        self.assertEqual(first["observation_period"], "1975-01-01")
        self.assertEqual(first["value"], "62.03")
        self.assertEqual(first["unit"], "index")
        self.assertEqual(first["value_status"], "actual")
        # Q2 maps to April.
        self.assertEqual(rows[1]["observation_period"], "1975-04-01")
        self.assertEqual(rows[2]["series_id"], "FHFA.HPI.AT.STATE.DC")
        self.assertEqual(
            first["publisher_context"]["place_id"], "AK")

    def test_metro_projects_index_and_stderr(self):
        body = (
            b'"Abilene, TX",10180,1986,2,108.10,( 2.56)\n'
            b'"Abilene, TX",10180,1975,1,-,-\n'
        )
        rows = adapters.normalize(
            fhfa_at_metro_source(), body, RETRIEVED_AT)
        by = {(r["series_id"], r["observation_period"]): r for r in rows}
        idx = by[("FHFA.HPI.AT.METRO.10180", "1986-04-01")]
        self.assertEqual(idx["value"], "108.10")
        err = by[("FHFA.HPI.AT.METRO.10180.RSTDERR", "1986-04-01")]
        self.assertEqual(err["value"], "2.56")
        self.assertEqual(err["unit"], "index standard error")
        # dash rows land as unavailable, not dropped.
        miss = by[("FHFA.HPI.AT.METRO.10180", "1975-01-01")]
        self.assertIsNone(miss["value"])
        self.assertEqual(miss["value_status"], "unavailable")
        self.assertEqual(
            idx["publisher_context"]["place_name"], "Abilene, TX")

    def test_rejects_wrong_width(self):
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                fhfa_at_state_source(), b"AK,1975,1\n", RETRIEVED_AT)

    def test_rejects_bad_quarter(self):
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                fhfa_at_state_source(), b"AK,1975,5,62.03\n", RETRIEVED_AT)

    def test_rejects_all_missing(self):
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                fhfa_at_state_source(), b"AK,1975,1,-\n", RETRIEVED_AT)


import io as _io
import zipfile as _zipfile

_CAINC1_HEADER = (
    "GeoFIPS,GeoName,Region,TableName,LineCode,IndustryClassification,"
    "Description,Unit,1969,1970"
)
# Rows exercise every geography_type + the (NA) missing token. Values verbatim
# from the CAINC1__ALL_AREAS shape (state FIPS end in 000, counties do not,
# 9x000 are BEA regions, 00000 is the U.S. aggregate).
_CAINC1_ROWS = [
    ' "00000","United States", ,CAINC1,1,"...",'
    '"Personal income (thousands of dollars) ","Thousands of dollars",'
    '791229000,855525000',
    ' "01000","Alabama",5,CAINC1,1,"...",'
    '"Personal income (thousands of dollars) ","Thousands of dollars",'
    '9737715,10628318',
    ' "01000","Alabama",5,CAINC1,3,"...",'
    '"Per capita personal income (dollars) 2/","Dollars",2831,3081',
    ' "01001","Autauga, AL",5,CAINC1,1,"...",'
    '"Personal income (thousands of dollars) ","Thousands of dollars",'
    '69973,(NA)',
    ' "98000","Far West",8,CAINC1,1,"...",'
    '"Personal income (thousands of dollars) ","Thousands of dollars",'
    '100000,110000',
]


def _cainc1_zip(rows=None, header=_CAINC1_HEADER, member="CAINC1__ALL_AREAS_1969_2024.csv"):
    if rows is None:
        rows = _CAINC1_ROWS
    text = header + "\n" + "\n".join(rows) + "\n"
    buf = _io.BytesIO()
    with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("CAINC1__definition.xml", "<x/>")
        zf.writestr(member, text.encode("latin-1"))
    return buf.getvalue()


def bea_cainc1_source(geography_type):
    src = source_config("bea_regional_cainc_zip", {
        "geography_type": geography_type,
        "series_id_prefix": "BEA.CAINC1",
        "table": "CAINC1",
    })
    src["value_status"] = "actual"
    src["expected_content_types"] = ["application/x-zip-compressed"]
    return src


class BeaRegionalCainc1ZipTest(unittest.TestCase):
    def test_state_projects_series_per_geo_and_linecode(self):
        rows = adapters.normalize(
            bea_cainc1_source("state_or_dc"), _cainc1_zip(), RETRIEVED_AT)
        by = {(r["series_id"], r["observation_period"]): r for r in rows}
        # only Alabama (01000) state rows survive the geography filter; each
        # LineCode is a distinct series; each year a distinct observation.
        self.assertIn(("BEA.CAINC1.01000.L1", "1969-01-01"), by)
        self.assertIn(("BEA.CAINC1.01000.L1", "1970-01-01"), by)
        self.assertIn(("BEA.CAINC1.01000.L3", "1969-01-01"), by)
        self.assertNotIn(("BEA.CAINC1.00000.L1", "1969-01-01"), by)
        self.assertNotIn(("BEA.CAINC1.01001.L1", "1969-01-01"), by)
        self.assertNotIn(("BEA.CAINC1.98000.L1", "1969-01-01"), by)
        inc = by[("BEA.CAINC1.01000.L1", "1969-01-01")]
        self.assertEqual(inc["value"], "9737715")
        self.assertEqual(inc["unit"], "Thousands of dollars")
        self.assertEqual(inc["value_status"], "actual")
        self.assertEqual(inc["publisher_context"]["geo_fips"], "01000")
        self.assertEqual(inc["publisher_context"]["geo_name"], "Alabama")
        self.assertEqual(inc["publisher_context"]["line_code"], "1")
        percap = by[("BEA.CAINC1.01000.L3", "1970-01-01")]
        self.assertEqual(percap["value"], "3081")
        self.assertEqual(percap["unit"], "Dollars")

    def test_county_na_lands_unavailable_not_dropped(self):
        rows = adapters.normalize(
            bea_cainc1_source("county"), _cainc1_zip(), RETRIEVED_AT)
        by = {(r["series_id"], r["observation_period"]): r for r in rows}
        self.assertIn(("BEA.CAINC1.01001.L1", "1969-01-01"), by)
        got = by[("BEA.CAINC1.01001.L1", "1969-01-01")]
        self.assertEqual(got["value"], "69973")
        # (NA) preserved as unavailable, never dropped (§19.4).
        miss = by[("BEA.CAINC1.01001.L1", "1970-01-01")]
        self.assertIsNone(miss["value"])
        self.assertEqual(miss["value_status"], "unavailable")

    def test_national_and_region_filtered_by_geography_type(self):
        nat = adapters.normalize(
            bea_cainc1_source("national_us"), _cainc1_zip(), RETRIEVED_AT)
        self.assertEqual(
            {r["series_id"] for r in nat}, {"BEA.CAINC1.00000.L1"})
        reg = adapters.normalize(
            bea_cainc1_source("bea_region"), _cainc1_zip(), RETRIEVED_AT)
        self.assertEqual(
            {r["series_id"] for r in reg}, {"BEA.CAINC1.98000.L1"})

    def test_rejects_table_mismatch_schema_drift(self):
        rows = [
            ' "01000","Alabama",5,CAINC4,1,"...",'
            '"Personal income (thousands of dollars) ","Thousands of dollars",'
            '9737715,10628318',
        ]
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                bea_cainc1_source("state_or_dc"),
                _cainc1_zip(rows=rows), RETRIEVED_AT)

    def test_rejects_duplicate_series_period(self):
        dup = _CAINC1_ROWS[1]
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                bea_cainc1_source("state_or_dc"),
                _cainc1_zip(rows=[dup, dup]), RETRIEVED_AT)

    def test_rejects_missing_all_areas_member(self):
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                bea_cainc1_source("state_or_dc"),
                _cainc1_zip(member="CAINC1_AL_1969_2024.csv"), RETRIEVED_AT)

    def test_rejects_all_missing(self):
        rows = [
            ' "01000","Alabama",5,CAINC1,1,"...",'
            '"Personal income (thousands of dollars) ","Thousands of dollars",'
            '(NA),(NA)',
        ]
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                bea_cainc1_source("state_or_dc"),
                _cainc1_zip(rows=rows), RETRIEVED_AT)


# --- BEA Regional SAGDP (B-GEO-LAND-4) ---------------------------------------
# SAGDP.zip carries TWO ALL_AREAS tables (SAGDP1 summary + SAGDP2 by-industry).
# The shared bea_regional_cainc_zip adapter must select the ALL_AREAS member
# matching the requested `table`, not merely the first ALL_AREAS member.
_SAGDP_HEADER = (
    "GeoFIPS,GeoName,Region,TableName,LineCode,IndustryClassification,"
    "Description,Unit,1997,1998"
)
_SAGDP1_ROWS = [
    ' "00000","United States", ,SAGDP1,1,"...",'
    '"Real GDP (millions of chained 2017 dollars) 1/",'
    '"Millions of chained 2017 dollars",12370299.0,12924876.0',
    ' "01000","Alabama",5,SAGDP1,3,"...",'
    '"Current-dollar GDP (millions of current dollars) ",'
    '"Millions of current dollars",104120.0,109325.0',
    ' "91000","New England",1,SAGDP1,1,"...",'
    '"Real GDP (millions of chained 2017 dollars) 1/",'
    '"Millions of chained 2017 dollars",700000.0,720000.0',
]
_SAGDP2_ROWS = [
    ' "00000","United States", ,SAGDP2,1,"...",'
    '"All industry total","Millions of current dollars",8577552.0,9062817.0',
    ' "01000","Alabama",5,SAGDP2,11,"...",'
    '"Construction","Millions of current dollars",5000.0,(NA)',
    ' "91000","New England",1,SAGDP2,1,"...",'
    '"All industry total","Millions of current dollars",500000.0,520000.0',
]


def _sagdp_zip():
    """Two-table BEA Regional zip: SAGDP1 first, then SAGDP2 (namelist order)."""
    buf = _io.BytesIO()
    with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("SAGDP1__definition.xml", "<x/>")
        zf.writestr(
            "SAGDP1__ALL_AREAS_1997_2025.csv",
            (_SAGDP_HEADER + "\n" + "\n".join(_SAGDP1_ROWS) + "\n").encode(
                "latin-1"))
        zf.writestr("SAGDP2__definition.xml", "<x/>")
        zf.writestr(
            "SAGDP2__ALL_AREAS_1997_2025.csv",
            (_SAGDP_HEADER + "\n" + "\n".join(_SAGDP2_ROWS) + "\n").encode(
                "latin-1"))
    return buf.getvalue()


def bea_sagdp_source(geography_type, table):
    src = source_config("bea_regional_cainc_zip", {
        "geography_type": geography_type,
        "series_id_prefix": "BEA.%s" % table,
        "table": table,
    })
    src["value_status"] = "actual"
    src["expected_content_types"] = ["application/x-zip-compressed"]
    return src


class BeaRegionalSagdpZipTest(unittest.TestCase):
    def test_selects_all_areas_member_by_table_not_first(self):
        # SAGDP2 is the SECOND ALL_AREAS member; a first-member-wins reader
        # would parse SAGDP1 and never emit any BEA.SAGDP2 series.
        rows = adapters.normalize(
            bea_sagdp_source("state_or_dc", "SAGDP2"), _sagdp_zip(),
            RETRIEVED_AT)
        ids = {r["series_id"] for r in rows}
        self.assertEqual(ids, {"BEA.SAGDP2.01000.L11"})
        by = {(r["series_id"], r["observation_period"]): r for r in rows}
        con = by[("BEA.SAGDP2.01000.L11", "1997-01-01")]
        self.assertEqual(con["value"], "5000.0")
        self.assertEqual(con["unit"], "Millions of current dollars")
        self.assertEqual(con["publisher_context"]["table"], "SAGDP2")
        # (NA) preserved unavailable, never dropped (§19.4).
        miss = by[("BEA.SAGDP2.01000.L11", "1998-01-01")]
        self.assertIsNone(miss["value"])
        self.assertEqual(miss["value_status"], "unavailable")

    def test_sagdp1_member_still_selectable_from_same_zip(self):
        rows = adapters.normalize(
            bea_sagdp_source("state_or_dc", "SAGDP1"), _sagdp_zip(),
            RETRIEVED_AT)
        self.assertEqual(
            {r["series_id"] for r in rows}, {"BEA.SAGDP1.01000.L3"})

    def test_geography_filter_national_and_region(self):
        nat = adapters.normalize(
            bea_sagdp_source("national_us", "SAGDP1"), _sagdp_zip(),
            RETRIEVED_AT)
        self.assertEqual(
            {r["series_id"] for r in nat}, {"BEA.SAGDP1.00000.L1"})
        reg = adapters.normalize(
            bea_sagdp_source("bea_region", "SAGDP2"), _sagdp_zip(),
            RETRIEVED_AT)
        self.assertEqual(
            {r["series_id"] for r in reg}, {"BEA.SAGDP2.91000.L1"})


# --- BEA Regional SQINC quarterly (B-GEO-LAND-6) -----------------------------
# SQINC.zip carries QUARTERLY ALL_AREAS tables whose value columns are
# "YYYY:Qn" (e.g. 1948:Q1), not the annual "YYYY" of CAINC/SAGDP/SAINC. The
# shared bea_regional_cainc_zip adapter must canonicalize a quarterly period to
# the project convention "YYYY-Qn" (parse_bea_api, §24.7 one value one home)
# while leaving annual columns landing "YYYY-01-01" unchanged, and must reject a
# header that mixes annual and quarterly columns.
_SQINC1_HEADER = (
    "GeoFIPS,GeoName,Region,TableName,LineCode,IndustryClassification,"
    "Description,Unit,1948:Q1,1948:Q2"
)
_SQINC1_ROWS = [
    ' "00000","United States", ,SQINC1,1,"...",'
    '"Personal income (thousands of dollars) ","Thousands of dollars",'
    '19700000,19900000',
    ' "01000","Alabama",5,SQINC1,1,"...",'
    '"Personal income (thousands of dollars) ","Thousands of dollars",'
    '250000,(NA)',
    ' "01000","Alabama",5,SQINC1,3,"...",'
    '"Per capita personal income (dollars) 2/","Dollars",850,860',
    ' "91000","New England",1,SQINC1,1,"...",'
    '"Personal income (thousands of dollars) ","Thousands of dollars",'
    '1000000,1010000',
]


def _sqinc1_zip(header=_SQINC1_HEADER, rows=None,
                member="SQINC1__ALL_AREAS_1948_2026.csv"):
    if rows is None:
        rows = _SQINC1_ROWS
    text = header + "\n" + "\n".join(rows) + "\n"
    buf = _io.BytesIO()
    with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("SQINC1__definition.xml", "<x/>")
        zf.writestr(member, text.encode("latin-1"))
    return buf.getvalue()


def bea_sqinc_source(geography_type, table):
    src = source_config("bea_regional_cainc_zip", {
        "geography_type": geography_type,
        "series_id_prefix": "BEA.%s" % table,
        "table": table,
    })
    src["value_status"] = "actual"
    src["expected_content_types"] = ["application/x-zip-compressed"]
    return src


class BeaRegionalSqincQuarterlyZipTest(unittest.TestCase):
    def test_quarterly_columns_canonicalize_to_year_quarter(self):
        rows = adapters.normalize(
            bea_sqinc_source("state_or_dc", "SQINC1"), _sqinc1_zip(),
            RETRIEVED_AT)
        by = {(r["series_id"], r["observation_period"]): r for r in rows}
        # quarterly period canonicalized to YYYY-Qn, never a fabricated day.
        self.assertIn(("BEA.SQINC1.01000.L1", "1948-Q1"), by)
        self.assertIn(("BEA.SQINC1.01000.L3", "1948-Q2"), by)
        self.assertNotIn(("BEA.SQINC1.00000.L1", "1948-Q1"), by)
        self.assertNotIn(("BEA.SQINC1.91000.L1", "1948-Q1"), by)
        inc = by[("BEA.SQINC1.01000.L1", "1948-Q1")]
        self.assertEqual(inc["value"], "250000")
        self.assertEqual(inc["unit"], "Thousands of dollars")
        self.assertEqual(inc["observed_at"], "1948-Q1")
        # (NA) preserved unavailable, never dropped (§19.4).
        miss = by[("BEA.SQINC1.01000.L1", "1948-Q2")]
        self.assertIsNone(miss["value"])
        self.assertEqual(miss["value_status"], "unavailable")

    def test_national_and_region_filtered_by_geography_type(self):
        nat = adapters.normalize(
            bea_sqinc_source("national_us", "SQINC1"), _sqinc1_zip(),
            RETRIEVED_AT)
        self.assertEqual(
            {r["series_id"] for r in nat}, {"BEA.SQINC1.00000.L1"})
        reg = adapters.normalize(
            bea_sqinc_source("bea_region", "SQINC1"), _sqinc1_zip(),
            RETRIEVED_AT)
        self.assertEqual(
            {r["series_id"] for r in reg}, {"BEA.SQINC1.91000.L1"})

    def test_rejects_header_mixing_annual_and_quarterly_columns(self):
        mixed = (
            "GeoFIPS,GeoName,Region,TableName,LineCode,IndustryClassification,"
            "Description,Unit,1948,1948:Q2"
        )
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                bea_sqinc_source("state_or_dc", "SQINC1"),
                _sqinc1_zip(header=mixed), RETRIEVED_AT)

    def test_annual_period_columns_still_land_iso_day(self):
        # regression guard: the quarterly branch must not change annual landing.
        rows = adapters.normalize(
            bea_cainc1_source("state_or_dc"), _cainc1_zip(), RETRIEVED_AT)
        periods = {r["observation_period"] for r in rows}
        self.assertIn("1969-01-01", periods)
        self.assertNotIn("1969-Q1", periods)


if __name__ == "__main__":
    unittest.main()
