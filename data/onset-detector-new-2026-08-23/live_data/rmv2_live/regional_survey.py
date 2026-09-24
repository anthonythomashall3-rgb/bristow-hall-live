"""Strict parsing for reviewed Federal Reserve regional-survey workbooks."""

from __future__ import absolute_import

import io
import posixpath
import re
import zipfile
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import xml.etree.ElementTree as ET


class RegionalSurveyDataError(ValueError):
    """Raised when a regional-survey workbook violates its exact contract."""


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_REL_NS = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
WORKSHEET_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/"
    "relationships/worksheet"
)
SERIES_FIELDS = frozenset((
    "date_column",
    "date_kind",
    "decimal_places",
    "expected_header",
    "items",
    "numeric_format_code",
    "sheet_name",
))
ITEM_FIELDS = frozenset((
    "column",
    "forecast_horizon",
    "label",
    "series_id",
    "unit",
    "value_status",
))
DATE_KINDS = frozenset((
    "excel_serial_1900_first_of_month",
    "month_abbrev_two_digit_year_pivot_1968",
))
VALUE_STATUSES = frozenset(("actual", "forecast", "model_estimate"))
MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

_CELL_RE = re.compile(r"^([A-Z]+)([1-9]\d*)$")
_INTEGER_RE = re.compile(r"^(?:0|[1-9]\d*)$")
_MONTH_RE = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2})$"
)
_NUMBER_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_XML_DECLARATION_GUARD = re.compile(br"<!\s*(?:DOCTYPE|ENTITY)", re.I)


def _exact_text(value, field):
    if (
        not isinstance(value, str) or
        not value or
        value != value.strip() or
        "\x00" in value
    ):
        raise RegionalSurveyDataError("%s was not exact text" % field)
    return value


def _column_number(name):
    value = 0
    for character in name:
        value = value * 26 + ord(character) - 64
    return value


def _safe_xml(raw, member):
    if _XML_DECLARATION_GUARD.search(raw[:4096]):
        raise RegionalSurveyDataError(
            "workbook XML declarations are prohibited in %s" % member
        )
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RegionalSurveyDataError(
            "workbook XML was invalid in %s: %s" % (member, exc)
        )


def _validate_archive(body):
    if not isinstance(body, bytes):
        raise TypeError("regional survey workbook must be bytes")
    if not zipfile.is_zipfile(io.BytesIO(body)):
        raise RegionalSurveyDataError(
            "regional survey workbook was not a valid OOXML archive"
        )
    try:
        archive = zipfile.ZipFile(io.BytesIO(body), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise RegionalSurveyDataError(
            "regional survey workbook could not be opened: %s" % exc
        )

    infos = archive.infolist()
    if not infos or len(infos) > 256:
        archive.close()
        raise RegionalSurveyDataError("workbook member count was unsafe")
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        archive.close()
        raise RegionalSurveyDataError("workbook contained duplicate members")

    total_size = 0
    for info in infos:
        name = info.filename
        parts = name.split("/")
        if (
            not name or
            name.startswith("/") or
            "\\" in name or
            any(part in ("", ".", "..") for part in parts) or
            info.flag_bits & 0x1
        ):
            archive.close()
            raise RegionalSurveyDataError("workbook member path was unsafe")
        lowered = name.lower()
        if (
            lowered.endswith((".vba", "vbaproject.bin")) or
            name.startswith("xl/externalLinks/") or
            name.startswith("xl/embeddings/")
        ):
            archive.close()
            raise RegionalSurveyDataError(
                "workbook active or external content was prohibited"
            )
        if info.file_size > 30000000:
            archive.close()
            raise RegionalSurveyDataError("workbook member was too large")
        total_size += info.file_size
        if (
            info.file_size > 1048576 and
            info.compress_size > 0 and
            info.file_size > info.compress_size * 300
        ):
            archive.close()
            raise RegionalSurveyDataError(
                "workbook compression ratio was unsafe"
            )
    if total_size > 80000000:
        archive.close()
        raise RegionalSurveyDataError("expanded workbook was too large")
    required = {
        "[Content_Types].xml",
        "xl/workbook.xml",
        "xl/_rels/workbook.xml.rels",
        "xl/styles.xml",
    }
    if not required.issubset(names):
        archive.close()
        raise RegionalSurveyDataError(
            "workbook required members were absent"
        )
    return archive


def _shared_strings(archive):
    member = "xl/sharedStrings.xml"
    if member not in archive.namelist():
        return ()
    root = _safe_xml(archive.read(member), member)
    strings = []
    for item in root.findall("{%s}si" % MAIN_NS):
        strings.append("".join(item.itertext()))
    if len(strings) > 20000:
        raise RegionalSurveyDataError("workbook shared strings were unsafe")
    return tuple(strings)


def _style_formats(archive):
    member = "xl/styles.xml"
    root = _safe_xml(archive.read(member), member)
    custom = {}
    num_fmts = root.find("{%s}numFmts" % MAIN_NS)
    if num_fmts is not None:
        for item in num_fmts.findall("{%s}numFmt" % MAIN_NS):
            identifier = item.get("numFmtId")
            code = item.get("formatCode")
            if (
                identifier is None or
                not identifier.isdigit() or
                code is None or
                int(identifier) in custom
            ):
                raise RegionalSurveyDataError(
                    "workbook numeric format was invalid"
                )
            custom[int(identifier)] = code
    cell_xfs = root.find("{%s}cellXfs" % MAIN_NS)
    if cell_xfs is None:
        raise RegionalSurveyDataError("workbook cell styles were absent")
    formats = []
    for item in cell_xfs.findall("{%s}xf" % MAIN_NS):
        identifier = item.get("numFmtId", "0")
        if not identifier.isdigit():
            raise RegionalSurveyDataError(
                "workbook cell format identifier was invalid"
            )
        formats.append(custom.get(int(identifier)))
    if not formats:
        raise RegionalSurveyDataError("workbook cell styles were empty")
    return tuple(formats)


def _sheet_paths(archive):
    workbook_member = "xl/workbook.xml"
    rels_member = "xl/_rels/workbook.xml.rels"
    workbook = _safe_xml(archive.read(workbook_member), workbook_member)
    workbook_pr = workbook.find("{%s}workbookPr" % MAIN_NS)
    if (
        workbook_pr is not None and
        workbook_pr.get("date1904") not in (None, "0", "false")
    ):
        raise RegionalSurveyDataError(
            "regional survey workbook used the 1904 date system"
        )
    relationships = _safe_xml(archive.read(rels_member), rels_member)
    targets = {}
    for relationship in relationships.findall(
        "{%s}Relationship" % PACKAGE_REL_NS
    ):
        if relationship.get("Type") != WORKSHEET_REL_TYPE:
            continue
        identifier = relationship.get("Id")
        target = relationship.get("Target")
        if (
            not identifier or
            identifier in targets or
            not target or
            "\\" in target
        ):
            raise RegionalSurveyDataError(
                "workbook worksheet relationship was invalid"
            )
        if target.startswith("/"):
            member = target[1:]
        elif target.startswith("xl/"):
            member = target
        else:
            member = posixpath.normpath(posixpath.join("xl", target))
        if (
            not member.startswith("xl/worksheets/") or
            member not in archive.namelist()
        ):
            raise RegionalSurveyDataError(
                "workbook worksheet target was unsafe"
            )
        targets[identifier] = member

    sheets = workbook.find("{%s}sheets" % MAIN_NS)
    if sheets is None:
        raise RegionalSurveyDataError("workbook sheets were absent")
    result = {}
    for sheet in list(sheets):
        name = sheet.get("name")
        identifier = sheet.get("{%s}id" % REL_NS)
        if (
            not name or
            name in result or
            identifier not in targets
        ):
            raise RegionalSurveyDataError("workbook sheet was invalid")
        result[name] = targets[identifier]
    return result


def _cell_value(cell, shared_strings):
    if cell.find("{%s}f" % MAIN_NS) is not None:
        raise RegionalSurveyDataError(
            "workbook formulas were prohibited in the data sheet"
        )
    value_node = cell.find("{%s}v" % MAIN_NS)
    raw = None if value_node is None else value_node.text
    cell_type = cell.get("t")
    if cell_type == "s":
        if raw is None or not _INTEGER_RE.match(raw):
            raise RegionalSurveyDataError(
                "workbook shared-string reference was invalid"
            )
        index = int(raw)
        if index >= len(shared_strings):
            raise RegionalSurveyDataError(
                "workbook shared-string reference was out of range"
            )
        return shared_strings[index]
    if cell_type == "inlineStr":
        inline = cell.find("{%s}is" % MAIN_NS)
        return None if inline is None else "".join(inline.itertext())
    if cell_type not in (None, "n"):
        raise RegionalSurveyDataError(
            "workbook cell type was unsupported"
        )
    return raw


def _rows(archive, member, shared_strings):
    root = _safe_xml(archive.read(member), member)
    sheet_data = root.find("{%s}sheetData" % MAIN_NS)
    if sheet_data is None:
        raise RegionalSurveyDataError("workbook sheet data was absent")
    rows = []
    previous_row = 0
    for row in sheet_data.findall("{%s}row" % MAIN_NS):
        raw_row = row.get("r")
        if (
            raw_row is None or
            not _INTEGER_RE.match(raw_row) or
            int(raw_row) <= previous_row
        ):
            raise RegionalSurveyDataError(
                "workbook row identity was invalid"
            )
        previous_row = int(raw_row)
        if previous_row > 5000:
            raise RegionalSurveyDataError("workbook row count was unsafe")
        values = {}
        styles = {}
        for cell in row.findall("{%s}c" % MAIN_NS):
            reference = cell.get("r")
            match = _CELL_RE.match(reference or "")
            if not match or int(match.group(2)) != previous_row:
                raise RegionalSurveyDataError(
                    "workbook cell reference was invalid"
                )
            column = match.group(1)
            number = _column_number(column)
            if number > 500 or column in values:
                raise RegionalSurveyDataError(
                    "workbook cell column was invalid"
                )
            values[column] = _cell_value(cell, shared_strings)
            raw_style = cell.get("s", "0")
            if not raw_style.isdigit():
                raise RegionalSurveyDataError(
                    "workbook cell style was invalid"
                )
            styles[column] = int(raw_style)
        rows.append((previous_row, values, styles))
    if not rows:
        raise RegionalSurveyDataError("workbook sheet had no rows")
    return rows


def _validate_series(series):
    if not isinstance(series, dict) or frozenset(series) != SERIES_FIELDS:
        raise RegionalSurveyDataError(
            "regional survey series metadata was not exact"
        )
    sheet_name = _exact_text(series["sheet_name"], "sheet_name")
    date_column = _exact_text(series["date_column"], "date_column")
    date_kind = series["date_kind"]
    if date_kind not in DATE_KINDS:
        raise RegionalSurveyDataError("regional survey date kind was invalid")
    decimal_places = series["decimal_places"]
    if (
        not isinstance(decimal_places, int) or
        isinstance(decimal_places, bool) or
        not 0 <= decimal_places <= 6
    ):
        raise RegionalSurveyDataError(
            "regional survey decimal places were invalid"
        )
    numeric_format_code = _exact_text(
        series["numeric_format_code"],
        "numeric_format_code",
    )
    expected_header = series["expected_header"]
    if (
        not isinstance(expected_header, list) or
        not expected_header or
        any(not isinstance(value, str) or not value for value in expected_header) or
        len(expected_header) != len(set(expected_header)) or
        expected_header[0] != date_column
    ):
        raise RegionalSurveyDataError(
            "regional survey expected header was invalid"
        )
    items = series["items"]
    if not isinstance(items, list) or not items:
        raise RegionalSurveyDataError(
            "regional survey projected items were absent"
        )
    seen_columns = set()
    seen_series = set()
    for item in items:
        if not isinstance(item, dict) or frozenset(item) != ITEM_FIELDS:
            raise RegionalSurveyDataError(
                "regional survey projected item was not exact"
            )
        column = _exact_text(item["column"], "item column")
        series_id = _exact_text(item["series_id"], "item series_id")
        _exact_text(item["label"], "item label")
        _exact_text(item["unit"], "item unit")
        if (
            column == date_column or
            column not in expected_header or
            column in seen_columns or
            not _TOKEN_RE.match(series_id) or
            series_id in seen_series or
            item["value_status"] not in VALUE_STATUSES
        ):
            raise RegionalSurveyDataError(
                "regional survey projected item identity was invalid"
            )
        horizon = item["forecast_horizon"]
        if item["value_status"] == "forecast":
            _exact_text(horizon, "forecast_horizon")
        elif horizon is not None:
            raise RegionalSurveyDataError(
                "nonforecast regional series had a forecast horizon"
            )
        seen_columns.add(column)
        seen_series.add(series_id)
    return (
        sheet_name,
        date_column,
        date_kind,
        decimal_places,
        numeric_format_code,
        expected_header,
        items,
    )


def _reference_period(raw, date_kind):
    if date_kind == "excel_serial_1900_first_of_month":
        if not isinstance(raw, str) or not _INTEGER_RE.match(raw):
            raise RegionalSurveyDataError(
                "regional survey Excel date was invalid"
            )
        serial = int(raw)
        if not 1 <= serial <= 2958465:
            raise RegionalSurveyDataError(
                "regional survey Excel date was out of range"
            )
        result = date(1899, 12, 30) + timedelta(days=serial)
        if result.day != 1:
            raise RegionalSurveyDataError(
                "regional survey reference date was not month-start"
            )
        return result.isoformat()
    match = _MONTH_RE.match(raw or "")
    if not match:
        raise RegionalSurveyDataError(
            "regional survey month label was invalid"
        )
    year_suffix = int(match.group(2))
    year = 1900 + year_suffix if year_suffix >= 68 else 2000 + year_suffix
    return date(year, MONTHS[match.group(1)], 1).isoformat()


def _canonical_value(raw, decimal_places):
    if not isinstance(raw, str) or not _NUMBER_RE.match(raw):
        raise RegionalSurveyDataError(
            "regional survey value was not a canonical workbook number"
        )
    try:
        value = Decimal(raw)
        quantum = Decimal(1).scaleb(-decimal_places)
        rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise RegionalSurveyDataError(
            "regional survey value was invalid: %s" % exc
        )
    if not rounded.is_finite():
        raise RegionalSurveyDataError(
            "regional survey value was non-finite"
        )
    return format(rounded, ".%df" % decimal_places)


def parse_regional_survey_xlsx(series, body):
    """Return exact projected diffusion indexes from one reviewed workbook."""
    (
        sheet_name,
        date_column,
        date_kind,
        decimal_places,
        numeric_format_code,
        expected_header,
        items,
    ) = _validate_series(series)
    archive = _validate_archive(body)
    try:
        shared_strings = _shared_strings(archive)
        style_formats = _style_formats(archive)
        sheet_paths = _sheet_paths(archive)
        if sheet_name not in sheet_paths:
            raise RegionalSurveyDataError(
                "reviewed regional survey sheet was absent"
            )
        rows = _rows(
            archive,
            sheet_paths[sheet_name],
            shared_strings,
        )
    finally:
        archive.close()

    header_row, header_values, unused_header_styles = rows[0]
    if header_row != 1:
        raise RegionalSurveyDataError(
            "regional survey header was not row 1"
        )
    actual_header = []
    for index in range(1, len(expected_header) + 1):
        column = ""
        value = index
        while value:
            value, remainder = divmod(value - 1, 26)
            column = chr(65 + remainder) + column
        actual_header.append(header_values.get(column))
    if actual_header != expected_header or len(header_values) != len(expected_header):
        raise RegionalSurveyDataError(
            "regional survey header was not exact"
        )
    column_by_name = {}
    for index, name in enumerate(expected_header, 1):
        column = ""
        value = index
        while value:
            value, remainder = divmod(value - 1, 26)
            column = chr(65 + remainder) + column
        column_by_name[name] = column

    results = []
    previous_period = None
    available_count = 0
    date_letter = column_by_name[date_column]
    for unused_row_number, values, styles in rows[1:]:
        if all(value in (None, "") for value in values.values()):
            continue
        raw_date = values.get(date_letter)
        if raw_date in (None, ""):
            raise RegionalSurveyDataError(
                "regional survey populated row had no date"
            )
        period = _reference_period(raw_date, date_kind)
        if previous_period is not None and period <= previous_period:
            raise RegionalSurveyDataError(
                "regional survey dates were duplicated or out of order"
            )
        previous_period = period
        for item in items:
            column = column_by_name[item["column"]]
            raw = values.get(column)
            if raw in (None, ""):
                value = None
            else:
                style_index = styles.get(column)
                if (
                    style_index is None or
                    style_index >= len(style_formats) or
                    style_formats[style_index] != numeric_format_code
                ):
                    raise RegionalSurveyDataError(
                        "regional survey numeric format drifted"
                    )
                value = _canonical_value(raw, decimal_places)
                available_count += 1
            results.append({
                "forecast_horizon": item["forecast_horizon"],
                "label": item["label"],
                "publisher_field": item["column"],
                "reference_period": period,
                "series_id": item["series_id"],
                "unit": item["unit"],
                "value": value,
                "value_status": item["value_status"],
            })
    if not results or not available_count:
        raise RegionalSurveyDataError(
            "regional survey workbook had no available observations"
        )
    return results
