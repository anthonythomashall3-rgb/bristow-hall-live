"""Strict normalization of the Census Quarterly Services Survey bulk ZIP."""

from __future__ import absolute_import

import csv
import io
import re
import stat
import zipfile
from datetime import datetime
from decimal import Decimal


class CensusQssDataError(RuntimeError):
    pass


SECTION_ORDER = (
    "CATEGORIES",
    "DATA TYPES",
    "ERROR TYPES",
    "GEO LEVELS",
    "TIME PERIODS",
    "NOTES",
    "DATA UPDATED ON",
    "DATA",
)
HEADERS = {
    "CATEGORIES": ["cat_idx", "cat_code", "cat_desc", "cat_indent"],
    "DATA TYPES": ["dt_idx", "dt_code", "dt_desc", "dt_unit"],
    "ERROR TYPES": ["et_idx", "err_code", "err_desc", "err_unit"],
    "GEO LEVELS": ["geo_idx", "geo_code", "geo_desc"],
    "TIME PERIODS": ["per_idx", "per_name"],
    "DATA": [
        "per_idx",
        "cat_idx",
        "dt_idx",
        "et_idx",
        "geo_idx",
        "is_adj",
        "val",
    ],
}
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_]+$")
PERIOD_RE = re.compile(r"^Q([1-4])-(\d{4})$")
UPDATED_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"\d{2}-[A-Z][a-z]{2}-\d{2} \d{2}:\d{2}:\d{2} (?:EST|EDT)$"
)
MISSING_REASONS = {
    "N": "not_available",
    "S": "suppressed_publication_standard",
    "Z": "absolute_value_below_0.05",
}
UNIT_MAP = {
    "K": "thousands",
    "MLN$": "USD millions",
    "PCT": "percent",
}


def _integer(value, label, allow_zero=False):
    pattern = r"^(?:0|[1-9]\d*)$" if allow_zero else r"^[1-9]\d*$"
    if not isinstance(value, str) or not re.match(pattern, value):
        raise CensusQssDataError("%s was not a canonical integer" % label)
    number = int(value)
    if not allow_zero and number < 1:
        raise CensusQssDataError("%s was not positive" % label)
    return number


def _blank(row):
    return not row or all(value == "" for value in row)


def _skip_blank(rows, cursor):
    while cursor < len(rows) and _blank(rows[cursor]):
        cursor += 1
    return cursor


def _require_marker(rows, cursor, marker):
    cursor = _skip_blank(rows, cursor)
    if cursor >= len(rows) or rows[cursor] != [marker]:
        raise CensusQssDataError("QSS section order differed at %s" % marker)
    return cursor + 1


def _read_table(rows, cursor, marker):
    cursor = _require_marker(rows, cursor, marker)
    if cursor >= len(rows) or rows[cursor] != HEADERS[marker]:
        raise CensusQssDataError("QSS %s header differed" % marker)
    cursor += 1
    values = []
    while cursor < len(rows) and not _blank(rows[cursor]):
        if len(rows[cursor]) != len(HEADERS[marker]):
            raise CensusQssDataError("QSS %s row width differed" % marker)
        values.append(rows[cursor])
        cursor += 1
    if not values:
        raise CensusQssDataError("QSS %s was empty" % marker)
    return values, cursor


def _read_zip(body, data_member, readme_member):
    if not isinstance(body, bytes) or not body.startswith(b"PK"):
        raise CensusQssDataError("QSS payload was not a ZIP archive")
    try:
        archive = zipfile.ZipFile(io.BytesIO(body), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise CensusQssDataError("QSS ZIP was invalid") from exc
    with archive:
        infos = archive.infolist()
        if [info.filename for info in infos] != [data_member, readme_member]:
            raise CensusQssDataError("QSS ZIP member set/order differed")
        if len({info.filename for info in infos}) != len(infos):
            raise CensusQssDataError("QSS ZIP contained duplicate members")
        if sum(info.file_size for info in infos) > 20000000:
            raise CensusQssDataError("QSS ZIP expanded size exceeded the limit")
        payloads = {}
        for info in infos:
            mode = info.external_attr >> 16
            if (
                info.is_dir() or
                info.flag_bits & 1 or
                stat.S_ISLNK(mode) or
                info.file_size > 10000000 or
                (
                    info.compress_size and
                    info.file_size > info.compress_size * 200
                )
            ):
                raise CensusQssDataError("QSS ZIP member was unsafe")
            try:
                payloads[info.filename] = archive.read(info)
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                raise CensusQssDataError("QSS ZIP member failed validation") from exc
        if archive.testzip() is not None:
            raise CensusQssDataError("QSS ZIP CRC validation failed")
    if not payloads[readme_member]:
        raise CensusQssDataError("QSS README was empty")
    return payloads[data_member]


def _metadata_map(rows, index_column, code_column, label):
    result = {}
    expected_index = 1
    for row in rows:
        index = _integer(row[0], "%s index" % label)
        if index != expected_index or index in result:
            raise CensusQssDataError("%s indexes were not contiguous" % label)
        if not TOKEN_RE.match(row[1]):
            raise CensusQssDataError("%s code was invalid" % label)
        if not row[2] or "\r" in row[2] or "\n" in row[2]:
            raise CensusQssDataError("%s description was invalid" % label)
        result[index] = row
        expected_index += 1
    return result


def _quarter_end(name):
    match = PERIOD_RE.match(name)
    if not match:
        raise CensusQssDataError("QSS period name was invalid")
    quarter = int(match.group(1))
    year = int(match.group(2))
    month_day = {
        1: (3, 31),
        2: (6, 30),
        3: (9, 30),
        4: (12, 31),
    }[quarter]
    return "%04d-%02d-%02d" % (year, month_day[0], month_day[1])


def parse_census_qss_zip(series, body):
    """Return deterministic QSS records without assigning scientific meaning."""
    expected_series = {
        "data_member",
        "geography_code",
        "missing_tokens",
        "readme_member",
    }
    if not isinstance(series, dict) or set(series) != expected_series:
        raise CensusQssDataError("QSS series metadata was not exact")
    if (
        series["data_member"] != "QSS-mf.csv" or
        series["readme_member"] != "/README" or
        series["geography_code"] != "US" or
        series["missing_tokens"] != ["N", "S", "Z"]
    ):
        raise CensusQssDataError("QSS series contract identity differed")
    csv_payload = _read_zip(
        body,
        series["data_member"],
        series["readme_member"],
    )
    try:
        text = csv_payload.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise CensusQssDataError("QSS CSV was not strict UTF-8") from exc
    if "\x00" in text:
        raise CensusQssDataError("QSS CSV contained NUL")
    rows = list(csv.reader(io.StringIO(text, newline="")))

    cursor = 0
    categories_rows, cursor = _read_table(rows, cursor, "CATEGORIES")
    data_type_rows, cursor = _read_table(rows, cursor, "DATA TYPES")
    error_type_rows, cursor = _read_table(rows, cursor, "ERROR TYPES")
    geography_rows, cursor = _read_table(rows, cursor, "GEO LEVELS")
    period_rows, cursor = _read_table(rows, cursor, "TIME PERIODS")

    cursor = _require_marker(rows, cursor, "NOTES")
    notes = []
    while cursor < len(rows) and not _blank(rows[cursor]):
        if len(rows[cursor]) != 1 or not rows[cursor][0]:
            raise CensusQssDataError("QSS note row differed")
        notes.append(rows[cursor][0])
        cursor += 1
    if not all(
        any(note.startswith("%s = " % token) for note in notes)
        for token in series["missing_tokens"]
    ):
        raise CensusQssDataError("QSS missing-token notes were incomplete")

    cursor = _require_marker(rows, cursor, "DATA UPDATED ON")
    if (
        cursor >= len(rows) or
        len(rows[cursor]) != 2 or
        not rows[cursor][1].startswith(" ")
    ):
        raise CensusQssDataError("QSS dataset update timestamp was missing")
    data_updated_on = rows[cursor][0] + "," + rows[cursor][1]
    if not UPDATED_RE.match(data_updated_on):
        raise CensusQssDataError("QSS dataset update timestamp differed")
    try:
        datetime.strptime(
            data_updated_on.rsplit(" ", 1)[0],
            "%A, %d-%b-%y %H:%M:%S",
        )
    except ValueError as exc:
        raise CensusQssDataError("QSS dataset update timestamp was invalid") from exc
    cursor += 1

    cursor = _require_marker(rows, cursor, "DATA")
    if cursor >= len(rows) or rows[cursor] != HEADERS["DATA"]:
        raise CensusQssDataError("QSS DATA header differed")
    cursor += 1
    data_rows = []
    while cursor < len(rows):
        if _blank(rows[cursor]):
            if any(not _blank(row) for row in rows[cursor + 1:]):
                raise CensusQssDataError("QSS DATA contained an interior blank row")
            break
        if len(rows[cursor]) != len(HEADERS["DATA"]):
            raise CensusQssDataError("QSS DATA row width differed")
        data_rows.append(rows[cursor])
        cursor += 1
    if not data_rows:
        raise CensusQssDataError("QSS DATA was empty")

    categories = _metadata_map(
        categories_rows, "cat_idx", "cat_code", "category"
    )
    for row in categories_rows:
        _integer(row[3], "category indent", allow_zero=True)
    data_types = _metadata_map(
        data_type_rows, "dt_idx", "dt_code", "data type"
    )
    error_types = _metadata_map(
        error_type_rows, "et_idx", "err_code", "error type"
    )
    for row in data_type_rows + error_type_rows:
        if row[3] not in UNIT_MAP:
            raise CensusQssDataError("QSS unit was not admitted")

    if geography_rows != [["1", "US", "U.S. Total"]]:
        raise CensusQssDataError("QSS geography contract differed")
    periods = {}
    prior_quarter = None
    for expected_index, row in enumerate(period_rows, 1):
        index = _integer(row[0], "period index")
        if index != expected_index:
            raise CensusQssDataError("QSS period indexes were not contiguous")
        match = PERIOD_RE.match(row[1])
        if not match:
            raise CensusQssDataError("QSS period name was invalid")
        current_quarter = int(match.group(2)) * 4 + int(match.group(1)) - 1
        if prior_quarter is not None and current_quarter != prior_quarter + 1:
            raise CensusQssDataError("QSS period dictionary had a gap")
        periods[index] = row[1]
        prior_quarter = current_quarter

    staged = []
    identities = set()
    for row in data_rows:
        per_idx = _integer(row[0], "data period index")
        cat_idx = _integer(row[1], "data category index")
        dt_idx = _integer(row[2], "data type index", allow_zero=True)
        et_idx = _integer(row[3], "error type index", allow_zero=True)
        geo_idx = _integer(row[4], "geography index")
        is_adj = _integer(row[5], "adjustment flag", allow_zero=True)
        if (
            per_idx not in periods or
            cat_idx not in categories or
            geo_idx != 1 or
            is_adj not in (0, 1) or
            (dt_idx > 0) == (et_idx > 0) or
            (dt_idx and dt_idx not in data_types) or
            (et_idx and et_idx not in error_types)
        ):
            raise CensusQssDataError("QSS DATA reference was invalid")
        identity = (per_idx, cat_idx, dt_idx, et_idx, geo_idx, is_adj)
        if identity in identities:
            raise CensusQssDataError("QSS DATA identity was duplicated")
        identities.add(identity)
        token = row[6]
        missing_reason = None
        value = token
        if token in MISSING_REASONS:
            value = None
            missing_reason = MISSING_REASONS[token]
        elif not DECIMAL_RE.match(token):
            raise CensusQssDataError("QSS value was not canonical")
        measure = data_types[dt_idx] if dt_idx else error_types[et_idx]
        if value is not None and (
            et_idx or measure[3] in ("K", "MLN$")
        ) and Decimal(value) < 0:
            raise CensusQssDataError("QSS nonnegative measure was negative")
        staged.append({
            "adjustment": "SA" if is_adj else "NSA",
            "category_code": categories[cat_idx][1],
            "category_description": categories[cat_idx][2],
            "category_indent": int(categories[cat_idx][3]),
            "measure_code": measure[1],
            "measure_description": measure[2],
            "measure_kind": "estimate" if dt_idx else "sampling_error",
            "missing_reason": missing_reason,
            "period_index": per_idx,
            "publisher_token": token if value is None else None,
            "reference_period": _quarter_end(periods[per_idx]),
            "reference_quarter": periods[per_idx],
            "unit": UNIT_MAP[measure[3]],
            "value": value,
        })
    latest_period_index = max(item["period_index"] for item in staged)

    output = []
    for item in staged:
        series_id = "CENSUS.QSS.%s.%s.US.%s" % (
            item["category_code"],
            item["measure_code"],
            item["adjustment"],
        )
        output.append({
            "data_updated_on": data_updated_on,
            "label": "%s — %s (%s)" % (
                item["category_description"],
                item["measure_description"],
                item["adjustment"],
            ),
            "publisher_adjustment": item["adjustment"],
            "publisher_category_code": item["category_code"],
            "publisher_category_description": item["category_description"],
            "publisher_category_indent": item["category_indent"],
            "publisher_estimate_status": (
                "preliminary_current_quarter"
                if item["period_index"] == latest_period_index
                else "current_revised_history"
            ),
            "publisher_measure_code": item["measure_code"],
            "publisher_measure_kind": item["measure_kind"],
            "publisher_missing_reason": item["missing_reason"],
            "publisher_token": item["publisher_token"],
            "reference_period": item["reference_period"],
            "reference_quarter": item["reference_quarter"],
            "series_id": series_id,
            "unit": item["unit"],
            "value": item["value"],
            "value_status": "actual" if item["value"] is not None else "unavailable",
        })
    return sorted(
        output,
        key=lambda item: (item["series_id"], item["reference_period"]),
    )
