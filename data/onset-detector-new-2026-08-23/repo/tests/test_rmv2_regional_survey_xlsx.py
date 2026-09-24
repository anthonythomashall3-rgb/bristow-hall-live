from __future__ import absolute_import

import copy
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
RETRIEVED_AT = "2026-07-30T18:00:00Z"


def _cell(reference, value, shared_index=None, style=None, formula=None):
    attributes = ['r="%s"' % reference]
    if shared_index is not None:
        attributes.append('t="s"')
    if style is not None:
        attributes.append('s="%s"' % style)
    value_xml = ""
    if value is not None:
        value_xml = "<v>%s</v>" % escape(str(value))
    formula_xml = ""
    if formula is not None:
        formula_xml = "<f>%s</f>" % escape(formula)
    return "<c %s>%s%s</c>" % (
        " ".join(attributes),
        formula_xml,
        value_xml,
    )


def _workbook_bytes(
    sheet_name="Survey",
    headers=("date", "activity", "future_activity"),
    rows=None,
    date1904=False,
    add_external_link=False,
    formula=False,
):
    rows = rows or (
        ("40603", "34.700000000000003", "47.7"),
        ("40634", None, "-8.4"),
    )
    shared = list(headers)
    shared_indexes = {value: index for index, value in enumerate(shared)}
    sheet_rows = []
    header_cells = []
    for index, header in enumerate(headers, 1):
        column = chr(64 + index)
        header_cells.append(_cell(
            "%s1" % column,
            shared_indexes[header],
            shared_index=shared_indexes[header],
        ))
    sheet_rows.append('<row r="1">%s</row>' % "".join(header_cells))
    for row_index, row in enumerate(rows, 2):
        cells = []
        for column_index, value in enumerate(row, 1):
            if value is None:
                continue
            column = chr(64 + column_index)
            cell_formula = "1+1" if formula and row_index == 2 and column_index == 2 else None
            cells.append(_cell(
                "%s%d" % (column, row_index),
                value,
                style="1" if column_index == 1 else "2",
                formula=cell_formula,
            ))
        sheet_rows.append(
            '<row r="%d">%s</row>' % (row_index, "".join(cells))
        )

    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships">'
        '<workbookPr date1904="%s"/>'
        '<sheets><sheet name="%s" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    ) % ("1" if date1904 else "0", escape(sheet_name))
    workbook_relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
        '2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><dimension ref="A1:C%d"/>'
        '<sheetData>%s</sheetData></worksheet>'
    ) % (len(rows) + 1, "".join(sheet_rows))
    shared_strings = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
        '2006/main" count="%d" uniqueCount="%d">%s</sst>'
    ) % (
        len(shared),
        len(shared),
        "".join("<si><t>%s</t></si>" % escape(value) for value in shared),
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main">'
        '<numFmts count="2">'
        '<numFmt numFmtId="164" formatCode="mmm\\-yyyy;@"/>'
        '<numFmt numFmtId="165" formatCode="0.0"/>'
        '</numFmts>'
        '<fonts count="1"><font/></fonts>'
        '<fills count="1"><fill/></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0"/></cellStyleXfs>'
        '<cellXfs count="3"><xf numFmtId="0"/>'
        '<xf numFmtId="164"/><xf numFmtId="165"/></cellXfs>'
        '</styleSheet>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types"><Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            workbook_relationships,
        )
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
        archive.writestr("xl/sharedStrings.xml", shared_strings)
        archive.writestr("xl/styles.xml", styles)
        if add_external_link:
            archive.writestr("xl/externalLinks/externalLink1.xml", "<bad/>")
    return output.getvalue()


def _series(date_kind="excel_serial_1900_first_of_month"):
    return {
        "date_column": "date",
        "date_kind": date_kind,
        "decimal_places": 1,
        "expected_header": ["date", "activity", "future_activity"],
        "items": [
            {
                "column": "activity",
                "forecast_horizon": None,
                "label": "Current activity diffusion index",
                "series_id": "REGIONAL.ACTIVITY",
                "unit": "diffusion index points",
                "value_status": "model_estimate",
            },
            {
                "column": "future_activity",
                "forecast_horizon": "six_months_ahead",
                "label": "Future activity diffusion index",
                "series_id": "REGIONAL.FUTURE_ACTIVITY",
                "unit": "diffusion index points",
                "value_status": "forecast",
            },
        ],
        "numeric_format_code": "0.0",
        "sheet_name": "Survey",
    }


def _source(series=None, endpoint="https://publisher.example/survey.xlsx"):
    return {
        "adapter": "regional_survey_xlsx",
        "allowed_hosts": ["publisher.example"],
        "coverage_source_ids": ["regional_survey"],
        "enabled": True,
        "endpoint": endpoint,
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        "frequency": "monthly",
        "information_set_mode": "current_revised",
        "label": "Regional business survey",
        "max_bytes": 1000000,
        "method_version": "regional_survey.current_revised.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Bank",
        "publisher_release_clock": "publisher schedule",
        "rights_status": "published_output_under_publisher_terms",
        "secret_env": None,
        "secret_required": False,
        "series": series or _series(),
        "source_id": "regional_survey_current",
        "value_status": "model_estimate",
    }


class RegionalSurveyWorkbookTests(unittest.TestCase):
    def test_excel_serial_dates_values_and_forecasts_are_projected_exactly(self):
        rows = adapters.normalize(
            _source(),
            _workbook_bytes(),
            RETRIEVED_AT,
        )
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["observation_period"], "2011-03-01")
        self.assertEqual(rows[0]["value"], "34.7")
        self.assertEqual(rows[0]["value_status"], "model_estimate")
        self.assertEqual(rows[1]["value"], "47.7")
        self.assertEqual(rows[1]["value_status"], "forecast")
        self.assertEqual(rows[1]["forecast_horizon"], "six_months_ahead")
        self.assertIsNone(rows[1]["forecast_origin"])
        self.assertIsNone(rows[1]["release_at"])
        self.assertEqual(rows[1]["available_at"], RETRIEVED_AT)
        self.assertEqual(rows[2]["value"], None)
        self.assertEqual(rows[2]["value_status"], "unavailable")
        self.assertFalse(rows[-1]["strict_publisher_first_release_proven"])

    def test_shared_string_month_dates_and_xls_suffix_ooxml_are_supported(self):
        series = _series("month_abbrev_two_digit_year_pivot_1968")
        rows = adapters.normalize(
            _source(series, "https://publisher.example/survey.xls"),
            _workbook_bytes(rows=(
                ("Jun-04", "11.4", "47.4"),
                ("Jul-26", "-4", "8.1999999999999993"),
            )),
            RETRIEVED_AT,
        )
        self.assertEqual(
            [row["observation_period"] for row in rows[::2]],
            ["2004-06-01", "2026-07-01"],
        )
        self.assertEqual([row["value"] for row in rows], [
            "11.4", "47.4", "-4.0", "8.2",
        ])

    def test_schema_date_formula_and_archive_drift_fail_closed(self):
        cases = []
        cases.append((_source(), _workbook_bytes(headers=(
            "date", "future_activity", "activity",
        ))))
        cases.append((_source(), _workbook_bytes(date1904=True)))
        cases.append((_source(), _workbook_bytes(formula=True)))
        cases.append((_source(), _workbook_bytes(add_external_link=True)))
        cases.append((_source(), b"not an xlsx archive"))
        cases.append((_source(), _workbook_bytes(rows=(
            ("40603", "1.0", "2.0"),
            ("40603", "3.0", "4.0"),
        ))))
        for source, body in cases:
            with self.subTest(body_size=len(body)):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(source, body, RETRIEVED_AT)

    def test_unknown_metadata_and_noncanonical_values_fail_closed(self):
        series = copy.deepcopy(_series())
        series["default"] = "forbidden"
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(_source(series), _workbook_bytes(), RETRIEVED_AT)
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                _source(),
                _workbook_bytes(rows=(("40603", "nan", "1.0"),)),
                RETRIEVED_AT,
            )

    def test_three_live_regional_sources_have_distinct_exact_contracts(self):
        config = load_config(CONFIG_PATH)
        expected = {
            "philly_nmbos_diffusion_current": (
                "philly_nmbos",
                "Diffusion",
                7,
            ),
            "dallas_tmos_diffusion_current": (
                "dallas_tmos",
                "All Data Seasonally Adjusted",
                11,
            ),
            "dallas_tssos_diffusion_current": (
                "dallas_tssos",
                "All Data Seasonally Adjusted",
                9,
            ),
        }
        selected = {
            source["source_id"]: source
            for source in config["sources"]
            if source["source_id"] in expected
        }
        self.assertEqual(set(selected), set(expected))
        for source_id, (family, sheet, item_count) in expected.items():
            source = selected[source_id]
            self.assertEqual(source["adapter"], "regional_survey_xlsx")
            self.assertEqual(source["coverage_source_ids"], [family])
            self.assertEqual(source["information_set_mode"], "current_revised")
            self.assertEqual(source["series"]["sheet_name"], sheet)
            self.assertEqual(len(source["series"]["items"]), item_count)
            self.assertEqual(
                len(source["series"]["expected_header"]),
                len(set(source["series"]["expected_header"])),
            )


if __name__ == "__main__":
    unittest.main()
