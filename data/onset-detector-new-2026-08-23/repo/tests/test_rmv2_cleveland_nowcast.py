from __future__ import absolute_import

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import (
    PublisherHttpClient,
    SourceUnavailable,
)
from live_data.rmv2_live.canonical import canonical_json_bytes
from live_data.rmv2_live.config import load_config


RETRIEVED_AT = "2026-07-30T06:20:00Z"
CONFIG_PATH = PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"
NOWCAST_NAMES = (
    "CPI Inflation",
    "Core CPI Inflation",
    "PCE Inflation",
    "Core PCE Inflation",
)
ACTUAL_NAMES = tuple("Actual " + name for name in NOWCAST_NAMES)


def source_config():
    return {
        "adapter": "cleveland_nowcast_json",
        "allowed_hosts": ["www.clevelandfed.org"],
        "coverage_source_ids": ["cleveland_inflation_nowcast"],
        "enabled": True,
        "endpoint": (
            "https://www.clevelandfed.org/-/media/files/webcharts/"
            "inflationnowcasting/nowcast_quarter.json?sc_lang=en"
        ),
        "expected_content_types": [
            "application/octet-stream",
            "application/json",
        ],
        "frequency": "business_daily",
        "information_set_mode": "current_revised",
        "label": "Cleveland Fed quarterly Inflation Nowcast",
        "max_bytes": 10000000,
        "method_version": (
            "cleveland_inflation_nowcast_quarter_current.v1"
        ),
        "poll_seconds": 3600,
        "publisher": "Federal Reserve Bank of Cleveland",
        "publisher_release_clock": (
            "business days around 10:00 America/New_York; exact release "
            "timestamp remains null unless directly proven"
        ),
        "rights_status": (
            "published_output_with_attribution_Cleveland_Fed_terms"
        ),
        "secret_env": None,
        "secret_required": False,
        "series": {},
        "source_id": "cleveland_inflation_nowcast_quarter_current",
        "value_status": "nowcast",
    }


def data_values(value):
    return [
        {"tooltext": "first", "value": "1.0"},
        {"tooltext": "latest", "value": value},
    ]


def dataset(name, value):
    return {
        "color": "e03430",
        "data": data_values(value),
        "seriesname": name,
    }


def chart(quarter, include_actuals=True):
    rows = [
        dataset(name, str(index + 1))
        for index, name in enumerate(NOWCAST_NAMES)
    ]
    if include_actuals:
        rows.extend(
            dataset(name, str(index + 5))
            for index, name in enumerate(ACTUAL_NAMES)
        )
    return {
        "categories": [{
            "category": [
                {"label": "01/02"},
                {"label": "01/03"},
            ],
        }],
        "chart": {
            "_comment": "2026-07-29 00:00",
            "basefont": "Helvetica",
            "bgalpha": "0",
            "caption": "Inflation Nowcasting",
            "labelpadding": "10",
            "legendnumcolumns": "4",
            "showborder": "0",
            "showexportdatamenuitem": "1",
            "showtooltip": "1",
            "showvalues": "0",
            "subcaption": quarter,
            "yaxisname": "Quarterly Annualized Percent Change",
        },
        "dataset": rows,
    }


def fixture():
    return canonical_json_bytes([
        chart("2026:Q1"),
        chart("2026:Q2", include_actuals=False),
    ])


class FakeResponse(object):
    def __init__(self, body):
        self.status = 200
        self.headers = {"Content-Type": "application/octet-stream"}
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def getcode(self):
        return 200

    def geturl(self):
        return source_config()["endpoint"]

    def read(self, size):
        return self._body


class FakeOpener(object):
    def __init__(self, body):
        self.body = body
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        return FakeResponse(self.body)


class ClevelandNowcastTests(unittest.TestCase):
    def test_valid_panels_project_exact_nowcast_and_actual_series(self):
        records = adapters.normalize(
            source_config(),
            fixture(),
            RETRIEVED_AT,
        )

        self.assertEqual(len(records), 12)
        current = next(
            row for row in records
            if row["series_id"] ==
            "CLEVELAND.INFLATION_NOWCAST.CORE_PCE.NOWCAST" and
            row["publisher_target_quarter"] == "2026:Q2"
        )
        actual = next(
            row for row in records
            if row["series_id"] ==
            "CLEVELAND.INFLATION_NOWCAST.CPI.ACTUAL"
        )
        self.assertEqual(current["value"], "4")
        self.assertEqual(current["value_status"], "nowcast")
        self.assertIsNone(current["forecast_origin"])
        self.assertEqual(current["forecast_target_start"], "2026-04-01")
        self.assertEqual(current["forecast_target_end"], "2026-06-30")
        self.assertEqual(actual["value_status"], "actual")
        self.assertEqual(actual["unit"], "annualized percent")
        self.assertEqual(
            current["publisher_as_of_label"],
            "2026-07-29 00:00",
        )
        self.assertFalse(current["strict_publisher_first_release_proven"])

    def test_duplicate_keys_unknown_series_and_missing_nowcast_fail_closed(self):
        duplicate_key = (
            b'[{"chart":{},"chart":{},"categories":[],"dataset":[]}]'
        )
        unknown = json.loads(fixture().decode("utf-8"))
        unknown[0]["dataset"][0]["seriesname"] = "Unknown Inflation"
        missing = json.loads(fixture().decode("utf-8"))
        del missing[0]["dataset"][0]
        duplicate_series = json.loads(fixture().decode("utf-8"))
        duplicate_series[0]["dataset"][1]["seriesname"] = "CPI Inflation"
        malformed_quarter = json.loads(fixture().decode("utf-8"))
        malformed_quarter[0]["chart"]["subcaption"] = "2026:Q5"
        nonfinite = json.loads(fixture().decode("utf-8"))
        nonfinite[0]["dataset"][0]["data"][-1]["value"] = "NaN"

        cases = (
            duplicate_key,
            canonical_json_bytes(unknown),
            canonical_json_bytes(missing),
            canonical_json_bytes(duplicate_series),
            canonical_json_bytes(malformed_quarter),
            canonical_json_bytes(nonfinite),
            canonical_json_bytes({"not": "a list"}),
        )
        for body in cases:
            with self.subTest(prefix=body[:100]):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(source_config(), body, RETRIEVED_AT)

    def test_complete_actual_panel_cannot_follow_an_incomplete_panel(self):
        body = canonical_json_bytes([
            chart("2026:Q1", include_actuals=False),
            chart("2026:Q2", include_actuals=True),
        ])
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source_config(), body, RETRIEVED_AT)

    def test_browser_request_profile_is_scoped_to_cleveland_only(self):
        cleveland_opener = FakeOpener(fixture())
        with mock.patch.object(
            adapters,
            "build_opener",
            return_value=cleveland_opener,
        ):
            PublisherHttpClient().fetch(source_config())
        cleveland_agent = cleveland_opener.requests[0].get_header("User-agent")
        self.assertIn("Mozilla/5.0", cleveland_agent)
        self.assertIn("Chrome/", cleveland_agent)

        ordinary = copy.deepcopy(source_config())
        ordinary["adapter"] = "raw_capture"
        ordinary_opener = FakeOpener(fixture())
        with mock.patch.object(
            adapters,
            "build_opener",
            return_value=ordinary_opener,
        ):
            PublisherHttpClient().fetch(ordinary)
        ordinary_agent = ordinary_opener.requests[0].get_header("User-agent")
        self.assertEqual(ordinary_agent, PublisherHttpClient.USER_AGENT)

    def test_live_config_is_exact_and_diagnostic_only(self):
        config = load_config(CONFIG_PATH)
        source = next(
            item for item in config["sources"]
            if item["source_id"] ==
            "cleveland_inflation_nowcast_quarter_current"
        )
        self.assertEqual(source["adapter"], "cleveland_nowcast_json")
        self.assertEqual(
            source["coverage_source_ids"],
            ["cleveland_inflation_nowcast"],
        )
        self.assertEqual(source["information_set_mode"], "current_revised")
        self.assertEqual(source["value_status"], "nowcast")
        self.assertEqual(source["series"], {})


if __name__ == "__main__":
    unittest.main()
