"""Strict Census BTOS national-workbook parsing.

The workbook is a publisher output, not a recession label or scientific model
binding.  This parser keeps response estimates, their standard errors, the
published national indices, and all distinct collection/reference/publication
clocks.  Missing and suppressed values remain unavailable.
"""

from __future__ import absolute_import

import io
import posixpath
import re
import zipfile
from datetime import date, timedelta
import xml.etree.ElementTree as ET


class CensusBtosDataError(ValueError):
    """Raised when BTOS workbook bytes violate the reviewed contract."""


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
SHEET_NAMES = (
    "Response Estimates",
    "Response Standard Errors",
    "Index Estimates",
    "Index Standard Errors",
    "Collection and Reference Dates",
    "Data Dictionary",
)
RESPONSE_HEADER = (
    "Question ID",
    "Question",
    "Answer ID",
    "Answer",
)
DATES_HEADER = (
    "Sample Year",
    "Cycle",
    "Panel",
    "Smpdt",
    "Collection Start",
    "Col End",
    "Reference Period Start",
    "Ref End",
    "Publication Date",
)
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
INDEX_TOKENS = {
    "Current performance": "CURRENT_PERFORMANCE",
    "Revenues": "REVENUES",
    "Employees": "EMPLOYEES",
    "Hours": "HOURS",
    "Delivery time": "DELIVERY_TIME",
    "Demand": "DEMAND",
    "Output prices": "OUTPUT_PRICES",
    "Input prices": "INPUT_PRICES",
    "Future performance": "FUTURE_PERFORMANCE",
    "Future employees": "FUTURE_EMPLOYEES",
    "Future hours": "FUTURE_HOURS",
    "Future delivery time": "FUTURE_DELIVERY_TIME",
    "Future demand": "FUTURE_DEMAND",
    "Future output prices": "FUTURE_OUTPUT_PRICES",
    "Future input prices": "FUTURE_INPUT_PRICES",
}
FUTURE_RESPONSE_QUESTIONS = {
    "16": (
        "Six months from now, how do you think you will describe "
        "this business's performance?"
    ),
    "17": (
        "Six months from now, how do you think this business's number "
        "of paid employees will have changed?"
    ),
    "18": (
        "Six months from now, how do you think the total number of hours "
        "worked by this business's paid employees will have changed?"
    ),
    "19": (
        "Six months from now, how do you think the time it takes for this "
        "business to receive deliveries from suppliers will have changed?"
    ),
    "20": (
        "Six months from now, how do you think you will describe this "
        "business's inventories?"
    ),
    "21": (
        "Six months from now, how do you think demand for this business's "
        "goods or services will have changed?"
    ),
    "22": (
        "Six months from now, how do you think the prices this business "
        "charges for its own goods or services will have changed?"
    ),
    "23": (
        "Six months from now, how do you think the prices this business "
        "pays for goods or services will have changed?"
    ),
    "24": (
        "During the next six months, do you think this business will be "
        "using Artificial Intelligence (AI) in any of its business "
        "functions? (Examples of AI: machine learning, natural language "
        "processing, virtual agents, voice recognition, etc.)"
    ),
}
STRUCTURAL_GAP_CYCLES = frozenset(("202521", "202522", "202523"))

_CELL_RE = re.compile(r"^([A-Z]+)([1-9]\d*)$")
_CYCLE_RE = re.compile(r"^20\d{2}(?:0[1-9]|1\d|2[0-6])$")
_INTEGER_RE = re.compile(r"^[1-9]\d*$")
# Shared-string references are 0-based; index 0 is valid (line-362 range check
# already admits it). _INTEGER_RE rejects "0", so it must NOT gate this field.
_SHARED_STRING_INDEX_RE = re.compile(r"^(?:0|[1-9]\d*)$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
_XML_DECLARATION_GUARD = re.compile(br"<!\s*(?:DOCTYPE|ENTITY)", re.I)


def _column_number(name):
    value = 0
    for character in name:
        value = value * 26 + ord(character) - 64
    return value


def _exact_text(value, field):
    if (
        not isinstance(value, str) or
        not value or
        value != value.strip() or
        "\x00" in value
    ):
        raise CensusBtosDataError("%s was not exact text" % field)
    return value


def _safe_xml(raw, member):
    if _XML_DECLARATION_GUARD.search(raw[:4096]):
        raise CensusBtosDataError(
            "BTOS workbook XML declarations are prohibited in %s" % member
        )
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise CensusBtosDataError(
            "BTOS workbook XML was invalid in %s: %s" % (member, exc)
        )


def _validate_archive(body):
    if not isinstance(body, bytes):
        raise TypeError("BTOS workbook must be bytes")
    if not zipfile.is_zipfile(io.BytesIO(body)):
        raise CensusBtosDataError("BTOS workbook was not a valid XLSX archive")
    try:
        archive = zipfile.ZipFile(io.BytesIO(body), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise CensusBtosDataError("BTOS workbook could not be opened: %s" % exc)

    infos = archive.infolist()
    if not infos or len(infos) > 64:
        archive.close()
        raise CensusBtosDataError("BTOS workbook member count was unsafe")
    names = [item.filename for item in infos]
    if len(names) != len(set(names)):
        archive.close()
        raise CensusBtosDataError("BTOS workbook had duplicate members")
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
            raise CensusBtosDataError("BTOS workbook member path was unsafe")
        if (
            name.lower().endswith((".bin", ".vba", ".vbaProject")) or
            name.startswith("xl/externalLinks/") or
            name.startswith("xl/embeddings/")
        ):
            archive.close()
            raise CensusBtosDataError("BTOS workbook active content is prohibited")
        if info.file_size > 20000000:
            archive.close()
            raise CensusBtosDataError("BTOS workbook member was too large")
        total_size += info.file_size
        if (
            info.file_size > 1048576 and
            info.compress_size > 0 and
            info.file_size > info.compress_size * 200
        ):
            archive.close()
            raise CensusBtosDataError("BTOS workbook compression ratio was unsafe")
    if total_size > 50000000:
        archive.close()
        raise CensusBtosDataError("BTOS workbook expanded size was too large")
    required = {
        "[Content_Types].xml",
        "xl/workbook.xml",
        "xl/_rels/workbook.xml.rels",
    }
    if not required.issubset(names):
        archive.close()
        raise CensusBtosDataError("BTOS workbook required members were absent")
    return archive


def _shared_strings(archive):
    member = "xl/sharedStrings.xml"
    if member not in archive.namelist():
        return ()
    root = _safe_xml(archive.read(member), member)
    values = []
    for item in root.findall("{%s}si" % MAIN_NS):
        values.append("".join(item.itertext()))
    return tuple(values)


def _sheet_paths(archive):
    workbook_member = "xl/workbook.xml"
    relationships_member = "xl/_rels/workbook.xml.rels"
    workbook = _safe_xml(archive.read(workbook_member), workbook_member)
    workbook_pr = workbook.find("{%s}workbookPr" % MAIN_NS)
    if (
        workbook_pr is not None and
        workbook_pr.get("date1904") not in (None, "0", "false")
    ):
        raise CensusBtosDataError("BTOS workbook used the 1904 date system")
    relationships = _safe_xml(
        archive.read(relationships_member),
        relationships_member,
    )
    targets = {}
    for relationship in relationships.findall(
        "{%s}Relationship" % PACKAGE_REL_NS
    ):
        relationship_id = relationship.get("Id")
        if (
            not relationship_id or
            relationship_id in targets or
            relationship.get("Type") != WORKSHEET_REL_TYPE
        ):
            if relationship.get("Type") == WORKSHEET_REL_TYPE:
                raise CensusBtosDataError(
                    "BTOS worksheet relationship was invalid"
                )
            continue
        target = relationship.get("Target")
        if not target or "\\" in target:
            raise CensusBtosDataError("BTOS worksheet target was invalid")
        if target.startswith("/"):
            if not target.startswith("/xl/"):
                raise CensusBtosDataError(
                    "BTOS worksheet target escaped its root"
                )
            normalized = posixpath.normpath(target.lstrip("/"))
        else:
            normalized = posixpath.normpath(posixpath.join("xl", target))
        if (
            normalized.startswith("../") or
            not normalized.startswith("xl/worksheets/")
        ):
            raise CensusBtosDataError("BTOS worksheet target escaped its root")
        targets[relationship_id] = normalized

    sheets_parent = workbook.find("{%s}sheets" % MAIN_NS)
    if sheets_parent is None:
        raise CensusBtosDataError("BTOS workbook sheets were absent")
    sheets = []
    for sheet in sheets_parent.findall("{%s}sheet" % MAIN_NS):
        name = sheet.get("name")
        relationship_id = sheet.get("{%s}id" % REL_NS)
        if not name or relationship_id not in targets:
            raise CensusBtosDataError("BTOS workbook sheet identity was invalid")
        sheets.append((name, targets[relationship_id]))
    if tuple(name for name, _ in sheets) != SHEET_NAMES:
        raise CensusBtosDataError("BTOS workbook sheet set/order changed")
    if len({path for _, path in sheets}) != len(sheets):
        raise CensusBtosDataError("BTOS workbook reused a worksheet target")
    if any(path not in archive.namelist() for _, path in sheets):
        raise CensusBtosDataError("BTOS workbook worksheet bytes were absent")
    return dict(sheets)


def _sheet_rows(archive, member, shared_strings):
    root = _safe_xml(archive.read(member), member)
    rows = []
    seen_row_numbers = set()
    last_row_number = 0
    for row in root.findall(".//{%s}row" % MAIN_NS):
        raw_row_number = row.get("r")
        if not raw_row_number or not _INTEGER_RE.match(raw_row_number):
            raise CensusBtosDataError("BTOS worksheet row identity was invalid")
        row_number = int(raw_row_number)
        if row_number <= last_row_number or row_number in seen_row_numbers:
            raise CensusBtosDataError("BTOS worksheet row order was invalid")
        seen_row_numbers.add(row_number)
        last_row_number = row_number
        cells = {}
        for cell in row.findall("{%s}c" % MAIN_NS):
            reference = cell.get("r")
            match = _CELL_RE.match(reference or "")
            if not match or int(match.group(2)) != row_number:
                raise CensusBtosDataError(
                    "BTOS worksheet cell reference was invalid"
                )
            column = _column_number(match.group(1))
            if column in cells:
                raise CensusBtosDataError(
                    "BTOS worksheet duplicated a cell"
                )
            if cell.find("{%s}f" % MAIN_NS) is not None:
                raise CensusBtosDataError(
                    "BTOS worksheet formulas are prohibited"
                )
            cell_type = cell.get("t")
            value = ""
            if cell_type == "inlineStr":
                inline = cell.find("{%s}is" % MAIN_NS)
                if inline is None:
                    raise CensusBtosDataError(
                        "BTOS inline string cell was invalid"
                    )
                value = "".join(inline.itertext())
            else:
                value_node = cell.find("{%s}v" % MAIN_NS)
                raw_value = value_node.text if value_node is not None else ""
                if cell_type == "s":
                    if not _SHARED_STRING_INDEX_RE.match(raw_value or ""):
                        raise CensusBtosDataError(
                            "BTOS shared-string index was invalid"
                        )
                    index = int(raw_value)
                    if not (0 <= index < len(shared_strings)):
                        raise CensusBtosDataError(
                            "BTOS shared-string index was out of range"
                        )
                    value = shared_strings[index]
                elif cell_type in (None, "n"):
                    value = raw_value or ""
                else:
                    raise CensusBtosDataError(
                        "BTOS worksheet cell type was unsupported"
                    )
            cells[column] = {
                "type": cell_type or "n",
                "value": value,
            }
        if any(item["value"] != "" for item in cells.values()):
            rows.append(cells)
    if not rows:
        raise CensusBtosDataError("BTOS worksheet contained no rows")
    return rows


def _value(row, column):
    return row.get(column, {"type": "n", "value": ""})["value"]


def _type(row, column):
    return row.get(column, {"type": "n", "value": ""})["type"]


def _cycle_header(row, prefix):
    for index, expected in enumerate(prefix, 1):
        if _value(row, index) != expected:
            raise CensusBtosDataError("BTOS worksheet header changed")
    cycles = []
    column = len(prefix) + 1
    while _value(row, column):
        cycle = _value(row, column)
        if not _CYCLE_RE.match(cycle):
            raise CensusBtosDataError("BTOS cycle header was invalid")
        cycles.append(cycle)
        column += 1
    if not cycles or len(cycles) != len(set(cycles)):
        raise CensusBtosDataError("BTOS cycle header set was invalid")
    if any(
        int(left) <= int(right)
        for left, right in zip(cycles, cycles[1:])
    ):
        raise CensusBtosDataError("BTOS cycle headers were not descending")
    if any(_value(row, index) for index in range(column, max(row.keys()) + 1)):
        raise CensusBtosDataError("BTOS cycle header contained a gap")
    return tuple(cycles)


def _excel_date(cell, field):
    if cell["type"] != "n" or not _INTEGER_RE.match(cell["value"] or ""):
        raise CensusBtosDataError("%s was not an Excel date serial" % field)
    serial = int(cell["value"])
    if not (30000 <= serial <= 60000):
        raise CensusBtosDataError("%s was outside the supported date range" % field)
    return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()


def _date_contract(rows):
    header = rows[0]
    if tuple(_value(header, index) for index in range(1, 10)) != DATES_HEADER:
        raise CensusBtosDataError("BTOS date-sheet header changed")
    result = {}
    for row in rows[1:]:
        cycle = _value(row, 4)
        if not cycle:
            continue
        if _type(row, 4) != "n" or not _CYCLE_RE.match(cycle):
            raise CensusBtosDataError("BTOS date-sheet cycle was invalid")
        if cycle in result:
            raise CensusBtosDataError("BTOS date-sheet cycle was duplicated")
        publication_cell = row.get(9, {"type": "", "value": ""})
        publication_date = None
        if publication_cell["value"]:
            publication_date = _excel_date(
                publication_cell,
                "BTOS publication date",
            )
        elif cycle not in STRUCTURAL_GAP_CYCLES:
            raise CensusBtosDataError(
                "BTOS publication date was absent outside a structural gap"
            )
        clocks = {
            "collection_start": _excel_date(
                row.get(5, {"type": "", "value": ""}),
                "BTOS collection start",
            ),
            "collection_end": _excel_date(
                row.get(6, {"type": "", "value": ""}),
                "BTOS collection end",
            ),
            "reference_period_start": _excel_date(
                row.get(7, {"type": "", "value": ""}),
                "BTOS reference start",
            ),
            "reference_period_end": _excel_date(
                row.get(8, {"type": "", "value": ""}),
                "BTOS reference end",
            ),
            "publisher_publication_date": publication_date,
        }
        if not (
            clocks["reference_period_start"] <=
            clocks["reference_period_end"] <
            clocks["collection_start"] <=
            clocks["collection_end"]
        ):
            raise CensusBtosDataError("BTOS date clocks were inconsistent")
        if (
            publication_date is not None and
            clocks["collection_end"] >= publication_date
        ):
            raise CensusBtosDataError("BTOS date clocks were inconsistent")
        result[cycle] = clocks
    if not result:
        raise CensusBtosDataError("BTOS date sheet contained no cycles")
    return result


def _parse_numeric(raw_value, percent, cycle):
    if cycle in STRUCTURAL_GAP_CYCLES and raw_value != ".":
        raise CensusBtosDataError(
            "BTOS structural-gap cycle contained a value"
        )
    if raw_value in (".", "S"):
        return None
    if not isinstance(raw_value, str):
        raise CensusBtosDataError("BTOS value was not text")
    value = raw_value
    if percent:
        if not value.endswith("%"):
            raise CensusBtosDataError("BTOS response value lacked percent unit")
        value = value[:-1]
    elif value.endswith("%"):
        raise CensusBtosDataError("BTOS index value unexpectedly used percent")
    if not _DECIMAL_RE.match(value):
        raise CensusBtosDataError("BTOS value was not a canonical decimal")
    whole, _, fraction = value.partition(".")
    numeric = int(whole + (fraction or "0"))
    denominator = 10 ** len(fraction) if fraction else 1
    if numeric > 100 * denominator:
        raise CensusBtosDataError("BTOS value exceeded its valid range")
    return value


def _missing_metadata(raw_value, cycle):
    if raw_value == "S":
        return "suppressed", False
    if raw_value == "." and cycle in STRUCTURAL_GAP_CYCLES:
        return "federal_shutdown_no_collection", True
    if raw_value == ".":
        return "publisher_unavailable", False
    return None, cycle in STRUCTURAL_GAP_CYCLES


def _response_rows(rows, cycles):
    if _cycle_header(rows[0], RESPONSE_HEADER) != cycles:
        raise CensusBtosDataError("BTOS response cycles differed")
    result = []
    identities = set()
    for row in rows[1:]:
        if not any(_value(row, 5 + index) for index in range(len(cycles))):
            continue
        question_id = _value(row, 1)
        answer_id = _value(row, 3)
        if (
            _type(row, 1) != "n" or
            _type(row, 3) != "n" or
            not _INTEGER_RE.match(question_id or "") or
            not _INTEGER_RE.match(answer_id or "")
        ):
            raise CensusBtosDataError(
                "BTOS response question/answer identity was invalid"
            )
        question = _exact_text(_value(row, 2), "BTOS question")
        answer = _exact_text(_value(row, 4), "BTOS answer")
        if (
            question_id in FUTURE_RESPONSE_QUESTIONS and
            question != FUTURE_RESPONSE_QUESTIONS[question_id]
        ):
            raise CensusBtosDataError(
                "BTOS future response question identity changed"
            )
        identity = (question_id, question, answer_id, answer)
        if (question_id, answer_id) in identities:
            raise CensusBtosDataError("BTOS response identity was duplicated")
        identities.add((question_id, answer_id))
        values = tuple(
            _value(row, 5 + index)
            for index in range(len(cycles))
        )
        if any(value == "" for value in values):
            raise CensusBtosDataError("BTOS response value cell was absent")
        result.append((identity, values))
    if not result:
        raise CensusBtosDataError("BTOS response sheet contained no series")
    return tuple(result)


def _index_rows(rows, cycles):
    if _cycle_header(rows[0], ("Option Text",)) != cycles:
        raise CensusBtosDataError("BTOS index cycles differed")
    result = []
    for row in rows[1:]:
        if not any(_value(row, 2 + index) for index in range(len(cycles))):
            continue
        label = _exact_text(_value(row, 1), "BTOS index label")
        values = tuple(
            _value(row, 2 + index)
            for index in range(len(cycles))
        )
        if any(value == "" for value in values):
            raise CensusBtosDataError("BTOS index value cell was absent")
        result.append((label, values))
    if tuple(label for label, _ in result) != INDEX_LABELS:
        raise CensusBtosDataError("BTOS national index series set/order changed")
    return tuple(result)


def _observation_base(cycle, clocks, raw_value):
    missing_reason, structural_gap = _missing_metadata(raw_value, cycle)
    return {
        "collection_end": clocks["collection_end"],
        "collection_start": clocks["collection_start"],
        "publisher_cycle": cycle,
        "publisher_missing_reason": missing_reason,
        "publisher_publication_date": clocks["publisher_publication_date"],
        "publisher_structural_gap": structural_gap,
        "reference_period": clocks["reference_period_end"],
        "reference_period_start": clocks["reference_period_start"],
    }


def parse_census_btos_xlsx(series_metadata, body):
    """Return all national BTOS estimates and uncertainty measures."""
    if series_metadata != {}:
        raise CensusBtosDataError(
            "BTOS series metadata must be the exact empty object"
        )
    archive = _validate_archive(body)
    try:
        shared = _shared_strings(archive)
        paths = _sheet_paths(archive)
        sheet_rows = {
            name: _sheet_rows(archive, paths[name], shared)
            for name in SHEET_NAMES
        }
    finally:
        archive.close()

    response_cycles = _cycle_header(
        sheet_rows["Response Estimates"][0],
        RESPONSE_HEADER,
    )
    for sheet_name, prefix in (
        ("Response Standard Errors", RESPONSE_HEADER),
        ("Index Estimates", ("Option Text",)),
        ("Index Standard Errors", ("Option Text",)),
    ):
        if _cycle_header(sheet_rows[sheet_name][0], prefix) != response_cycles:
            raise CensusBtosDataError("BTOS worksheet cycle sets differed")
    clocks = _date_contract(
        sheet_rows["Collection and Reference Dates"]
    )
    if any(cycle not in clocks for cycle in response_cycles):
        raise CensusBtosDataError("BTOS data cycle lacked date lineage")

    response_estimates = _response_rows(
        sheet_rows["Response Estimates"],
        response_cycles,
    )
    response_errors = _response_rows(
        sheet_rows["Response Standard Errors"],
        response_cycles,
    )
    if tuple(item[0] for item in response_estimates) != tuple(
        item[0] for item in response_errors
    ):
        raise CensusBtosDataError(
            "BTOS response estimate/error identities differed"
        )
    index_estimates = _index_rows(
        sheet_rows["Index Estimates"],
        response_cycles,
    )
    index_errors = _index_rows(
        sheet_rows["Index Standard Errors"],
        response_cycles,
    )
    if tuple(item[0] for item in index_estimates) != tuple(
        item[0] for item in index_errors
    ):
        raise CensusBtosDataError(
            "BTOS index estimate/error identities differed"
        )

    observations = []
    for measurement, rows, unit in (
        ("ESTIMATE", response_estimates, "percent of businesses"),
        (
            "STANDARD_ERROR",
            response_errors,
            "percentage points standard error",
        ),
    ):
        for identity, values in rows:
            question_id, question, answer_id, answer = identity
            is_future = question_id in FUTURE_RESPONSE_QUESTIONS
            series_id = (
                "CENSUS.BTOS.NATIONAL.RESPONSE.Q%s.A%s.%s" %
                (
                    question_id.zfill(3),
                    answer_id.zfill(3),
                    measurement,
                )
            )
            for cycle, raw_value in zip(response_cycles, values):
                value = _parse_numeric(raw_value, percent=True, cycle=cycle)
                item = _observation_base(cycle, clocks[cycle], raw_value)
                item.update({
                    "forecast_horizon": (
                        "six_month_business_expectation"
                        if is_future
                        else None
                    ),
                    "label": "%s — %s (%s)" % (
                        question,
                        answer,
                        (
                            "estimate"
                            if measurement == "ESTIMATE"
                            else "standard error"
                        ),
                    ),
                    "publisher_answer": answer,
                    "publisher_answer_id": answer_id,
                    "publisher_measure_kind": measurement.lower(),
                    "publisher_question": question,
                    "publisher_question_id": question_id,
                    "series_id": series_id,
                    "unit": unit,
                    "value": value,
                    "value_status": (
                        "unavailable"
                        if value is None
                        else (
                            "forecast"
                            if is_future and measurement == "ESTIMATE"
                            else "model_estimate"
                        )
                    ),
                })
                observations.append(item)

    for measurement, rows, unit in (
        ("ESTIMATE", index_estimates, "BTOS index points"),
        (
            "STANDARD_ERROR",
            index_errors,
            "BTOS index points standard error",
        ),
    ):
        for label, values in rows:
            token = INDEX_TOKENS[label]
            is_future = label.startswith("Future ")
            series_id = "CENSUS.BTOS.NATIONAL.INDEX.%s.%s" % (
                token,
                measurement,
            )
            for cycle, raw_value in zip(response_cycles, values):
                value = _parse_numeric(raw_value, percent=False, cycle=cycle)
                item = _observation_base(cycle, clocks[cycle], raw_value)
                item.update({
                    "forecast_horizon": (
                        "six_month_business_expectation"
                        if is_future
                        else None
                    ),
                    "label": "BTOS national %s %s" % (
                        label.lower(),
                        (
                            "index"
                            if measurement == "ESTIMATE"
                            else "index standard error"
                        ),
                    ),
                    "publisher_index_horizon": (
                        "future_six_month" if is_future else "current"
                    ),
                    "publisher_index_label": label,
                    "publisher_measure_kind": measurement.lower(),
                    "series_id": series_id,
                    "unit": unit,
                    "value": value,
                    "value_status": (
                        "unavailable"
                        if value is None
                        else (
                            "forecast"
                            if is_future and measurement == "ESTIMATE"
                            else "model_estimate"
                        )
                    ),
                })
                observations.append(item)
    return observations
