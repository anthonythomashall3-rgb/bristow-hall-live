from __future__ import absolute_import

import csv
import io
import sys
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable
from live_data.rmv2_live.canonical import read_json


RETRIEVED_AT = "2026-07-30T20:00:00Z"


def source():
    config = read_json(PROJECT_ROOT / "live_data/config/sources.v1.json")
    matches = [
        value for value in config["sources"]
        if value["source_id"] == "census_qss_current_revised"
    ]
    if len(matches) != 1:
        raise AssertionError("Census QSS source configuration is not exact")
    return matches[0]


def csv_bytes(data_rows=None):
    if data_rows is None:
        data_rows = [
            ["1", "1", "1", "0", "1", "1", "100.5"],
            ["1", "1", "0", "1", "1", "1", "0.4"],
            ["1", "1", "2", "0", "1", "1", "Z"],
            ["2", "1", "1", "0", "1", "1", "110.5"],
            ["2", "1", "0", "1", "1", "1", "0.3"],
            ["2", "1", "2", "0", "1", "1", "S"],
        ]
    rows = [
        ["CATEGORIES"],
        ["cat_idx", "cat_code", "cat_desc", "cat_indent"],
        ["1", "000000A", "Selected Services Total", "0"],
        [],
        [],
        ["DATA TYPES"],
        ["dt_idx", "dt_code", "dt_desc", "dt_unit"],
        ["1", "QREV", "Total Revenue", "MLN$"],
        ["2", "PQREV", "Total Revenue Percent Change", "PCT"],
        [],
        [],
        ["ERROR TYPES"],
        ["et_idx", "err_code", "err_desc", "err_unit"],
        ["1", "E_QREV", "Coefficient Of Variation For Total Revenue", "PCT"],
        [],
        [],
        ["GEO LEVELS"],
        ["geo_idx", "geo_code", "geo_desc"],
        ["1", "US", "U.S. Total"],
        [],
        [],
        ["TIME PERIODS"],
        ["per_idx", "per_name"],
        ["1", "Q4-2025"],
        ["2", "Q1-2026"],
        ["3", "Q2-2026"],
        [],
        [],
        ["NOTES"],
        ["N = Not available."],
        ["Z = Absolute value is less than 0.05."],
        [
            "S = Estimate does not meet publication standards because of "
            "high sampling variability."
        ],
        [],
        [],
        ["DATA UPDATED ON"],
        ["Thursday", " 11-Jun-26 09:01:38 EDT"],
        [],
        [],
        ["DATA"],
        ["per_idx", "cat_idx", "dt_idx", "et_idx", "geo_idx", "is_adj", "val"],
    ] + data_rows
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def zip_bytes(data=None, extra_members=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("QSS-mf.csv", csv_bytes() if data is None else data)
        archive.writestr("/README", b"Quarterly Services Survey\n")
        for name, value in extra_members or []:
            archive.writestr(name, value)
    return output.getvalue()


class CensusQssTests(unittest.TestCase):
    def test_valid_zip_preserves_actual_error_and_censored_statuses(self):
        records = adapters.parse_census_qss_zip(
            source(), zip_bytes(), RETRIEVED_AT
        )
        self.assertEqual(len(records), 6)
        by_key = {
            (record["observation_period"], record["publisher_measure_code"]):
            record
            for record in records
        }
        self.assertEqual(
            by_key[("2026-03-31", "QREV")]["value"],
            "110.5",
        )
        self.assertEqual(
            by_key[("2026-03-31", "E_QREV")]["publisher_measure_kind"],
            "sampling_error",
        )
        self.assertEqual(
            by_key[("2025-12-31", "PQREV")]["publisher_token"],
            "Z",
        )
        self.assertIsNone(
            by_key[("2025-12-31", "PQREV")]["value"],
        )
        self.assertEqual(
            by_key[("2026-03-31", "PQREV")]["publisher_missing_reason"],
            "suppressed_publication_standard",
        )
        self.assertTrue(
            all(
                record["provider_vintage_kind"] == "current_revised"
                and record["strict_publisher_first_release_proven"] is False
                for record in records
            )
        )

    def test_dictionary_only_future_quarter_emits_no_record(self):
        records = adapters.parse_census_qss_zip(
            source(), zip_bytes(), RETRIEVED_AT
        )
        self.assertNotIn(
            "2026-06-30",
            {record["observation_period"] for record in records},
        )

    def test_unsafe_or_extra_zip_member_fails_closed(self):
        with self.assertRaises(SourceUnavailable):
            adapters.parse_census_qss_zip(
                source(),
                zip_bytes(extra_members=[("../escape", b"x")]),
                RETRIEVED_AT,
            )

    def test_duplicate_identity_or_unknown_token_fails_closed(self):
        duplicate = [
            ["1", "1", "1", "0", "1", "1", "100.5"],
            ["1", "1", "1", "0", "1", "1", "100.5"],
        ]
        with self.assertRaises(SourceUnavailable):
            adapters.parse_census_qss_zip(
                source(), zip_bytes(csv_bytes(duplicate)), RETRIEVED_AT
            )
        invalid = [["1", "1", "1", "0", "1", "1", "missing"]]
        with self.assertRaises(SourceUnavailable):
            adapters.parse_census_qss_zip(
                source(), zip_bytes(csv_bytes(invalid)), RETRIEVED_AT
            )


if __name__ == "__main__":
    unittest.main()
