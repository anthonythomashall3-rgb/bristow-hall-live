from __future__ import absolute_import

import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import HttpResponse, SourceUnavailable
from live_data.rmv2_live.canonical import read_json
from live_data.rmv2_live.pipeline import (
    RefreshPipeline,
    _validate_selected_atomic_bundles,
)


RETRIEVED_AT = "2026-07-30T20:00:00Z"
GEOGRAPHIES = [
    ("National", "United States", "-----"),
    ("State", "Alabama", "'01'"),
    ("State", "Alaska", "'02'"),
    ("State", "Arizona", "'04'"),
    ("State", "Arkansas", "'05'"),
    ("State", "California", "'06'"),
    ("State", "Colorado", "'08'"),
    ("State", "Connecticut", "'09'"),
    ("State", "Delaware", "'10'"),
    ("State", "District of Columbia", "'11'"),
    ("State", "Florida", "'12'"),
    ("State", "Georgia", "'13'"),
    ("State", "Hawaii", "'15'"),
    ("State", "Idaho", "'16'"),
    ("State", "Illinois", "'17'"),
    ("State", "Indiana", "'18'"),
    ("State", "Iowa", "'19'"),
    ("State", "Kansas", "'20'"),
    ("State", "Kentucky", "'21'"),
    ("State", "Louisiana", "'22'"),
    ("State", "Maine", "'23'"),
    ("State", "Maryland", "'24'"),
    ("State", "Massachusetts", "'25'"),
    ("State", "Michigan", "'26'"),
    ("State", "Minnesota", "'27'"),
    ("State", "Mississippi", "'28'"),
    ("State", "Missouri", "'29'"),
    ("State", "Montana", "'30'"),
    ("State", "Nebraska", "'31'"),
    ("State", "Nevada", "'32'"),
    ("State", "New Hampshire", "'33'"),
    ("State", "New Jersey", "'34'"),
    ("State", "New Mexico", "'35'"),
    ("State", "New York", "'36'"),
    ("State", "North Carolina", "'37'"),
    ("State", "North Dakota", "'38'"),
    ("State", "Ohio", "'39'"),
    ("State", "Oklahoma", "'40'"),
    ("State", "Oregon", "'41'"),
    ("State", "Pennsylvania", "'42'"),
    ("State", "Rhode Island", "'44'"),
    ("State", "South Carolina", "'45'"),
    ("State", "South Dakota", "'46'"),
    ("State", "Tennessee", "'47'"),
    ("State", "Texas", "'48'"),
    ("State", "Utah", "'49'"),
    ("State", "Vermont", "'50'"),
    ("State", "Virginia", "'51'"),
    ("State", "Washington", "'53'"),
    ("State", "West Virginia", "'54'"),
    ("State", "Wisconsin", "'55'"),
    ("State", "Wyoming", "'56'"),
]


def config():
    return read_json(PROJECT_ROOT / "live_data/config/sources.v1.json")


def source(source_id):
    matches = [
        value for value in config()["sources"]
        if value["source_id"] == source_id
    ]
    if len(matches) != 1:
        raise AssertionError("CFPB mortgage source configuration is not exact")
    return matches[0]


def months():
    result = []
    year = 2008
    month = 1
    while (year, month) <= (2025, 9):
        result.append("%04d-%02d" % (year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def body(metric_code, mutate=None):
    header = ["RegionType", "Name", "FIPSCode"] + months()
    rows = []
    for geography_index, geography in enumerate(GEOGRAPHIES):
        values = ["1.0"] * len(months())
        if geography_index == 0:
            values[-1] = "1.6" if metric_code == "30_89" else "0.8"
        rows.append(list(geography) + values)
    if mutate is not None:
        mutate(header, rows)
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def unrelated_source():
    return {
        "adapter": "raw_capture",
        "allowed_hosts": ["publisher.example"],
        "coverage_source_ids": ["synthetic_publisher"],
        "enabled": True,
        "endpoint": "https://publisher.example/data.bin",
        "expected_content_types": ["application/octet-stream"],
        "frequency": "daily",
        "information_set_mode": "current_revised",
        "label": "Synthetic unrelated source",
        "max_bytes": 100000,
        "method_version": "synthetic-unrelated.v1",
        "poll_seconds": 300,
        "publisher": "Synthetic publisher",
        "publisher_release_clock": "publisher clock",
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {},
        "source_id": "synthetic_unrelated",
        "value_status": "actual",
    }


def bundle_config():
    return {
        "api": {
            "host": "127.0.0.1",
            "port": 8792,
            "website_poll_seconds": 60,
        },
        "catalog_registry": "registry.csv",
        "schema_version": "recession-monitor-v2.live-data-config.v1",
        "service": {"refresh_tick_seconds": 60},
        "sources": [
            source("cfpb_mortgage_performance_state_30_89_current"),
            source("cfpb_mortgage_performance_state_90_plus_current"),
            unrelated_source(),
        ],
        "store": {
            "public": "public",
            "root": "store",
            "runtime": "runtime",
        },
    }


def http_response(source_value, response_body):
    content_type = (
        "text/csv"
        if source_value["adapter"] == "cfpb_mortgage_performance_state_csv"
        else "application/octet-stream"
    )
    return HttpResponse(
        source_value["endpoint"],
        200,
        {"content-type": content_type},
        response_body,
    )


class ScriptedClient(object):
    def __init__(self, scripts):
        self.scripts = {
            source_id: list(values)
            for source_id, values in scripts.items()
        }

    def fetch(self, source_value, now=None, conditional_headers=None):
        source_id = source_value["source_id"]
        if source_id not in self.scripts or not self.scripts[source_id]:
            raise AssertionError("unexpected source fetch: %s" % source_id)
        value = self.scripts[source_id].pop(0)
        if isinstance(value, Exception):
            raise value
        response = http_response(source_value, value)
        response.request_headers = dict(conditional_headers or {})
        return response


class CfpbMortgageTests(unittest.TestCase):
    def test_valid_state_file_unpivots_exact_geographies_and_months(self):
        source_value = source(
            "cfpb_mortgage_performance_state_90_plus_current"
        )
        records = adapters.parse_cfpb_mortgage_performance_state_csv(
            source_value,
            body("90_PLUS"),
            RETRIEVED_AT,
        )
        self.assertEqual(len(records), 52 * 213)
        national = [
            record for record in records
            if record["series_id"] == "CFPB.MPT.90_PLUS.NATIONAL"
            and record["observation_period"] == "2025-09"
        ]
        self.assertEqual(len(national), 1)
        self.assertEqual(national[0]["value"], "0.8")
        self.assertEqual(national[0]["data_through"], "2025-09")
        alabama = [
            record for record in records
            if record["series_id"] == "CFPB.MPT.90_PLUS.STATE.01"
        ][0]
        self.assertEqual(alabama["publisher_fips_token"], "'01'")
        self.assertEqual(alabama["value_status"], "actual")
        self.assertFalse(alabama["strict_publisher_first_release_proven"])

    def test_invalid_geography_or_value_fails_closed(self):
        source_value = source(
            "cfpb_mortgage_performance_state_30_89_current"
        )
        with self.assertRaises(SourceUnavailable):
            adapters.parse_cfpb_mortgage_performance_state_csv(
                source_value,
                body(
                    "30_89",
                    lambda header, rows: rows.__setitem__(
                        1, ["State", "Alabama", "'99'"] + ["1.0"] * 213
                    ),
                ),
                RETRIEVED_AT,
            )
        with self.assertRaises(SourceUnavailable):
            adapters.parse_cfpb_mortgage_performance_state_csv(
                source_value,
                body(
                    "30_89",
                    lambda header, rows: rows[0].__setitem__(-1, "NaN"),
                ),
                RETRIEVED_AT,
            )

    def test_gapped_or_wrong_terminal_month_fails_closed(self):
        source_value = source(
            "cfpb_mortgage_performance_state_30_89_current"
        )
        with self.assertRaises(SourceUnavailable):
            adapters.parse_cfpb_mortgage_performance_state_csv(
                source_value,
                body(
                    "30_89",
                    lambda header, rows: header.__setitem__(-1, "2025-10"),
                ),
                RETRIEVED_AT,
            )

    def test_atomic_bundle_rejects_single_member_selection(self):
        with self.assertRaises(ValueError):
            _validate_selected_atomic_bundles(
                config(),
                {"cfpb_mortgage_performance_state_30_89_current"},
            )
        _validate_selected_atomic_bundles(
            config(),
            {
                "cfpb_mortgage_performance_state_30_89_current",
                "cfpb_mortgage_performance_state_90_plus_current",
            },
        )

    def test_failed_bundle_cannot_publish_mixed_heads_on_unrelated_refresh_and_recovers(self):
        member_30 = "cfpb_mortgage_performance_state_30_89_current"
        member_90 = "cfpb_mortgage_performance_state_90_plus_current"
        bundle_id = "cfpb_mortgage_performance_state_current.v1"
        pair = {member_30, member_90}
        initial_30 = body("30_89")
        changed_30 = body(
            "30_89",
            lambda header, rows: rows[0].__setitem__(-1, "1.7"),
        )
        initial_90 = body("90_PLUS")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "registry.csv").write_text(
                "source_id,access_class,coverage,frequency,primary_url,"
                "publisher,rights_status,typical_release_or_availability\n"
                "cfpb_mortgage_performance,A,2008-present,monthly,"
                "https://files.consumerfinance.gov,CFPB,public,periodic\n"
                "synthetic_publisher,A,current,daily,"
                "https://publisher.example,Synthetic publisher,public,daily\n",
                encoding="utf-8",
            )
            config_value = bundle_config()

            initial = RefreshPipeline(
                root,
                config_value,
                ScriptedClient({
                    member_30: [initial_30],
                    member_90: [initial_90],
                }),
                clock=lambda: "2026-07-30T20:00:00Z",
            ).refresh(source_ids=pair)
            self.assertIsNotNone(initial["pointer"])
            initial_pointer = read_json(root / "public/latest.pointer.json")
            initial_commit = read_json(
                root /
                "runtime" /
                "atomic_bundles" /
                (bundle_id + ".json")
            )

            failed = RefreshPipeline(
                root,
                config_value,
                ScriptedClient({
                    member_30: [changed_30],
                    member_90: [SourceUnavailable("publisher timeout")],
                }),
                clock=lambda: "2026-07-30T20:06:00Z",
            ).refresh(source_ids=pair)
            self.assertIsNone(failed["pointer"])
            self.assertEqual(
                read_json(root / "public/latest.pointer.json"),
                initial_pointer,
            )
            self.assertEqual(
                read_json(
                    root /
                    "runtime" /
                    "atomic_bundles" /
                    (bundle_id + ".json")
                ),
                initial_commit,
            )

            unrelated = RefreshPipeline(
                root,
                config_value,
                ScriptedClient({
                    "synthetic_unrelated": [b"new unrelated payload"],
                }),
                clock=lambda: "2026-07-30T20:12:00Z",
            ).refresh(source_ids={"synthetic_unrelated"})
            self.assertIsNone(unrelated["pointer"])
            self.assertEqual(
                read_json(root / "public/latest.pointer.json"),
                initial_pointer,
            )
            bundle_failures = [
                outcome for outcome in unrelated["outcomes"]
                if outcome["source_id"] == bundle_id
            ]
            self.assertEqual(len(bundle_failures), 1)
            self.assertIn(
                "committed bundle",
                bundle_failures[0]["error"],
            )

            recovered = RefreshPipeline(
                root,
                config_value,
                ScriptedClient({
                    member_30: [changed_30],
                    member_90: [initial_90],
                }),
                clock=lambda: "2026-07-30T20:18:00Z",
            ).refresh(source_ids=pair)
            self.assertIsNotNone(recovered["pointer"])
            self.assertNotEqual(
                recovered["pointer"]["generation_sha256"],
                initial_pointer["generation_sha256"],
            )
            recovered_commit = read_json(
                root /
                "runtime" /
                "atomic_bundles" /
                (bundle_id + ".json")
            )
            self.assertNotEqual(recovered_commit, initial_commit)
            self.assertEqual(
                recovered_commit["atomic_bundle_id"],
                bundle_id,
            )
            self.assertEqual(
                [item["source_id"] for item in recovered_commit["members"]],
                sorted(pair),
            )
            operational = read_json(root / "public/operational_status.json")
            self.assertIn(
                "atomic_bundle_evidence_changed",
                operational["generation_advance_reasons"],
            )


if __name__ == "__main__":
    unittest.main()
