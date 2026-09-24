from __future__ import absolute_import

import io
import sys
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable
from live_data.rmv2_live.config import load_config


CONFIG_PATH = PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"
RETRIEVED_AT = "2026-07-30T14:01:00Z"
INDEX_LABELS = (
    "Current performance",
    "Revenues",
    "Employees",
    "Hours",
    "Delivery time",
    "Demand",
    "Output prices",
    "Input prices",
    "Future performance",
    "Future employees",
    "Future hours",
    "Future delivery time",
    "Future demand",
    "Future output prices",
    "Future input prices",
)


def source_config():
    return {
        "adapter": "census_btos_xlsx",
        "allowed_hosts": ["www.census.gov"],
        "coverage_source_ids": ["census_btos"],
        "enabled": True,
        "endpoint": "https://www.census.gov/hfp/btos/downloads/National.xlsx",
        "expected_content_types": [
            "application/octet-stream",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ],
        "frequency": "biweekly",
        "information_set_mode": "current_revised",
        "label": "Census Business Trends and Outlook Survey national workbook",
        "max_bytes": 5000000,
        "method_version": "census_btos_national_workbook.v2",
        "poll_seconds": 3600,
        "publisher": "U.S. Census Bureau",
        "publisher_release_clock": (
            "every other Thursday 10:00 America/New_York; "
            "publisher calendar controls exceptions"
        ),
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {},
        "source_id": "census_btos_national_current",
        "value_status": "model_estimate",
    }


def _column_name(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _cell(reference, value, numeric=False):
    if value is None:
        return ""
    if numeric:
        return '<c r="%s" t="n"><v>%s</v></c>' % (
            reference,
            escape(str(value)),
        )
    return (
        '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' %
        (reference, escape(str(value)))
    )


def _sheet(rows):
    rendered = []
    for row_number, row in enumerate(rows, 1):
        cells = []
        for column_number, item in enumerate(row, 1):
            value, numeric = item if isinstance(item, tuple) else (item, False)
            cells.append(
                _cell(
                    "%s%d" % (_column_name(column_number), row_number),
                    value,
                    numeric=numeric,
                )
            )
        rendered.append(
            '<row r="%d">%s</row>' % (row_number, "".join(cells))
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><sheetData>%s</sheetData></worksheet>'
    ) % "".join(rendered)


def workbook_bytes(
    current_value="54.6",
    response_value="12.3%",
    gap_value=".",
    index_gap_value=None,
    duplicate_index=False,
    future_response=False,
    future_question=(
        "Six months from now, how do you think you will describe "
        "this business's performance?"
    ),
    response_header="Question ID",
):
    cycles = ("202614", "202521")
    index_gap_value = (
        gap_value if index_gap_value is None else index_gap_value
    )
    response_rows = [
        [response_header, "Question", "Answer ID", "Answer"] + list(cycles),
        [
            ("3", True),
            "Overall, how would you describe this business's current performance?",
            ("1", True),
            "Excellent",
            response_value,
            gap_value,
        ],
    ]
    response_se_rows = [
        ["Question ID", "Question", "Answer ID", "Answer"] + list(cycles),
        [
            ("3", True),
            "Overall, how would you describe this business's current performance?",
            ("1", True),
            "Excellent",
            "0.18%",
            gap_value,
        ],
    ]
    if future_response:
        response_rows.append([
            ("16", True),
            future_question,
            ("1", True),
            "Excellent",
            "19.4%",
            gap_value,
        ])
        response_se_rows.append([
            ("16", True),
            future_question,
            ("1", True),
            "Excellent",
            "0.22%",
            gap_value,
        ])
    index_rows = [["Option Text"] + list(cycles)]
    index_se_rows = [["Option Text"] + list(cycles)]
    for label in INDEX_LABELS:
        value = current_value if label == "Current performance" else "51.2"
        index_rows.append([label, value, index_gap_value])
        index_se_rows.append([label, "0.20", index_gap_value])
    if duplicate_index:
        index_rows.append(["Current performance", "55.0", gap_value])

    dates_rows = [
        [
            "Sample Year",
            "Cycle",
            "Panel",
            "Smpdt",
            "Collection Start",
            "Col End",
            "Reference Period Start",
            "Ref End",
            "Publication Date",
        ],
        [
            ("4", True),
            ("4", True),
            ("5", True),
            ("202614", True),
            ("46202", True),
            ("46215", True),
            ("46188", True),
            ("46201", True),
            ("46219", True),
        ],
        [
            ("3", True),
            ("1", True),
            ("3", True),
            ("202521", True),
            ("45936", True),
            ("45949", True),
            ("45922", True),
            ("45935", True),
            None,
        ],
    ]
    dictionary_rows = [
        ["Item", "Description", "Notes"],
        ["smpdt", "Sample Date", "Publisher cycle identifier"],
    ]
    sheet_names = (
        "Response Estimates",
        "Response Standard Errors",
        "Index Estimates",
        "Index Standard Errors",
        "Collection and Reference Dates",
        "Data Dictionary",
    )
    worksheets = (
        response_rows,
        response_se_rows,
        index_rows,
        index_se_rows,
        dates_rows,
        dictionary_rows,
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships"><sheets>%s</sheets></workbook>'
    ) % "".join(
        '<sheet name="%s" sheetId="%d" r:id="rId%d"/>' %
        (escape(name), index, index)
        for index, name in enumerate(sheet_names, 1)
    )
    relationships_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
        '2006/relationships">%s</Relationships>'
    ) % "".join(
        '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet%d.xml"/>' % (index, index)
        for index in range(1, 7)
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types"><Default Extension="xml" '
        'ContentType="application/xml"/></Types>'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            relationships_xml,
        )
        for index, rows in enumerate(worksheets, 1):
            archive.writestr(
                "xl/worksheets/sheet%d.xml" % index,
                _sheet(rows),
            )
    return output.getvalue()


class CensusBtosTests(unittest.TestCase):
    def test_national_workbook_projects_response_index_and_clock_lineage(self):
        records = adapters.normalize(
            source_config(),
            workbook_bytes(),
            RETRIEVED_AT,
        )

        self.assertEqual(len(records), 64)
        response = next(
            row for row in records
            if row["series_id"] ==
            "CENSUS.BTOS.NATIONAL.RESPONSE.Q003.A001.ESTIMATE" and
            row["publisher_cycle"] == "202614"
        )
        self.assertEqual(response["value"], "12.3")
        self.assertEqual(response["unit"], "percent of businesses")
        self.assertEqual(response["observation_period"], "2026-06-28")
        self.assertEqual(response["reference_period_start"], "2026-06-15")
        self.assertEqual(response["collection_start"], "2026-06-29")
        self.assertEqual(response["collection_end"], "2026-07-12")
        self.assertEqual(response["publisher_publication_date"], "2026-07-16")
        self.assertEqual(response["value_status"], "model_estimate")
        self.assertFalse(response["strict_publisher_first_release_proven"])

        current = next(
            row for row in records
            if row["series_id"] ==
            "CENSUS.BTOS.NATIONAL.INDEX.CURRENT_PERFORMANCE.ESTIMATE" and
            row["publisher_cycle"] == "202614"
        )
        future = next(
            row for row in records
            if row["series_id"] ==
            "CENSUS.BTOS.NATIONAL.INDEX.FUTURE_PERFORMANCE.ESTIMATE" and
            row["publisher_cycle"] == "202614"
        )
        future_uncertainty = next(
            row for row in records
            if row["series_id"] ==
            "CENSUS.BTOS.NATIONAL.INDEX.FUTURE_PERFORMANCE.STANDARD_ERROR" and
            row["publisher_cycle"] == "202614"
        )
        self.assertEqual(current["value"], "54.6")
        self.assertEqual(current["unit"], "BTOS index points")
        self.assertEqual(current["value_status"], "model_estimate")
        self.assertEqual(future["value_status"], "forecast")
        self.assertEqual(
            future["forecast_horizon"],
            "six_month_business_expectation",
        )
        self.assertEqual(
            future_uncertainty["forecast_horizon"],
            "six_month_business_expectation",
        )
        self.assertEqual(
            future_uncertainty["value_status"],
            "model_estimate",
        )
        self.assertIsNone(future["forecast_origin"])

    def test_suppression_and_shutdown_cycles_remain_unavailable(self):
        records = adapters.normalize(
            source_config(),
            workbook_bytes(response_value="S"),
            RETRIEVED_AT,
        )

        suppressed = next(
            row for row in records
            if row["series_id"] ==
            "CENSUS.BTOS.NATIONAL.RESPONSE.Q003.A001.ESTIMATE" and
            row["publisher_cycle"] == "202614"
        )
        gap = next(
            row for row in records
            if row["series_id"] ==
            "CENSUS.BTOS.NATIONAL.INDEX.CURRENT_PERFORMANCE.ESTIMATE" and
            row["publisher_cycle"] == "202521"
        )
        self.assertIsNone(suppressed["value"])
        self.assertEqual(suppressed["value_status"], "unavailable")
        self.assertEqual(suppressed["publisher_missing_reason"], "suppressed")
        self.assertIsNone(gap["value"])
        self.assertEqual(gap["value_status"], "unavailable")
        self.assertTrue(gap["publisher_structural_gap"])
        self.assertEqual(
            gap["publisher_missing_reason"],
            "federal_shutdown_no_collection",
        )

    def test_future_response_has_exact_six_month_forecast_semantics(self):
        records = adapters.normalize(
            source_config(),
            workbook_bytes(future_response=True),
            RETRIEVED_AT,
        )

        estimate = next(
            row for row in records
            if row["series_id"] ==
            "CENSUS.BTOS.NATIONAL.RESPONSE.Q016.A001.ESTIMATE" and
            row["publisher_cycle"] == "202614"
        )
        uncertainty = next(
            row for row in records
            if row["series_id"] ==
            "CENSUS.BTOS.NATIONAL.RESPONSE.Q016.A001.STANDARD_ERROR" and
            row["publisher_cycle"] == "202614"
        )
        self.assertEqual(estimate["value_status"], "forecast")
        self.assertEqual(
            estimate["forecast_horizon"],
            "six_month_business_expectation",
        )
        self.assertEqual(
            uncertainty["forecast_horizon"],
            "six_month_business_expectation",
        )
        self.assertEqual(uncertainty["value_status"], "model_estimate")

        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                source_config(),
                workbook_bytes(
                    future_response=True,
                    future_question="Six months from now, something changed?",
                ),
                RETRIEVED_AT,
            )

    def test_shutdown_cycle_numeric_values_fail_closed(self):
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                source_config(),
                workbook_bytes(index_gap_value="49.0"),
                RETRIEVED_AT,
            )

    def test_archive_schema_identity_and_numeric_drift_fail_closed(self):
        unsafe = io.BytesIO(workbook_bytes())
        rewritten = io.BytesIO()
        with zipfile.ZipFile(unsafe) as source:
            with zipfile.ZipFile(rewritten, "w", zipfile.ZIP_DEFLATED) as target:
                for name in source.namelist():
                    target.writestr(name, source.read(name))
                target.writestr("../escape.xml", b"<escape/>")

        mutations = (
            workbook_bytes(response_header="question_id"),
            workbook_bytes(current_value="NaN"),
            workbook_bytes(current_value="-1"),
            workbook_bytes(current_value="101"),
            workbook_bytes(duplicate_index=True),
            rewritten.getvalue(),
            b"not-an-xlsx",
        )
        for body in mutations:
            with self.subTest(size=len(body)):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(source_config(), body, RETRIEVED_AT)

    def test_series_metadata_is_exact_and_live_config_is_non_admitted(self):
        source = source_config()
        source["series"] = {"implicit_default": "forbidden"}
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(source, workbook_bytes(), RETRIEVED_AT)

        config = load_config(CONFIG_PATH)
        live = next(
            item for item in config["sources"]
            if item["source_id"] == "census_btos_national_current"
        )
        self.assertEqual(live["adapter"], "census_btos_xlsx")
        self.assertEqual(live["coverage_source_ids"], ["census_btos"])
        self.assertEqual(live["information_set_mode"], "current_revised")
        self.assertEqual(live["value_status"], "model_estimate")
        self.assertEqual(live["series"], {})
        self.assertEqual(live["poll_seconds"], 3600)


class CensusBtosSharedStringIndexTests(unittest.TestCase):
    """Regression: shared-string index 0 is valid (0-based); B-FEEDFIX-1."""

    def _archive_with_shared_cell(self, index_text):
        worksheet = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main"><sheetData>'
            '<row r="1"><c r="A1" t="s"><v>%s</v></c></row>'
            '</sheetData></worksheet>'
        ) % index_text
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("s.xml", worksheet)
        return zipfile.ZipFile(io.BytesIO(output.getvalue()))

    def test_shared_string_index_zero_resolves(self):
        from live_data.rmv2_live import census_btos

        archive = self._archive_with_shared_cell("0")
        rows = census_btos._sheet_rows(
            archive, "s.xml", ("Question ID", "second"),
        )
        self.assertEqual(rows[0][1]["value"], "Question ID")

    def test_shared_string_index_non_integer_still_rejected(self):
        from live_data.rmv2_live import census_btos

        archive = self._archive_with_shared_cell("x")
        with self.assertRaises(census_btos.CensusBtosDataError):
            census_btos._sheet_rows(archive, "s.xml", ("Question ID",))


if __name__ == "__main__":
    unittest.main()
