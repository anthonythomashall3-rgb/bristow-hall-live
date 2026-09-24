"""Strict parsing for Federal Reserve Data Download Program CSV packages.

This module performs no network I/O.  It validates the six-row DDP metadata
envelope before projecting observations, so an HTML page, a reordered series
set, or a changed unit cannot silently enter the live-data store.
"""

from __future__ import absolute_import

import csv
import io
import re
from datetime import datetime


class FedDdpDataError(ValueError):
    """Raised when Federal Reserve DDP bytes violate the configured contract."""


_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
_QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")
_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
_SERIES_FIELDS = frozenset((
    "date_frequency",
    "expected_columns",
    "expected_currency",
    "expected_multiplier",
    "expected_unit",
    "identifier_prefix",
    "missing_tokens",
    "series_id_prefix",
))
_OPTIONAL_SERIES_FIELDS = frozenset((
    "expected_unique_identifier_label",
))
_DEFAULT_METADATA_LABELS = (
    "Series Description",
    "Unit:",
    "Multiplier:",
    "Currency:",
    "Unique Identifier:",
    "Time Period",
)


def _validate_series(series):
    if (
        not isinstance(series, dict) or
        frozenset(series) not in (
            _SERIES_FIELDS,
            _SERIES_FIELDS | _OPTIONAL_SERIES_FIELDS,
        )
    ):
        raise FedDdpDataError("DDP series metadata key set was not exact")
    columns = series["expected_columns"]
    if (
        not isinstance(columns, list) or not columns or
        any(not isinstance(item, str) or not _TOKEN_RE.match(item) for item in columns) or
        len(columns) != len(set(columns))
    ):
        raise FedDdpDataError("DDP expected column set was invalid")
    if series["date_frequency"] not in ("daily", "monthly", "quarterly"):
        raise FedDdpDataError("DDP date frequency was invalid")
    for field in (
        "expected_currency",
        "expected_multiplier",
        "expected_unit",
        "identifier_prefix",
        "series_id_prefix",
    ):
        if not isinstance(series[field], str) or not series[field]:
            raise FedDdpDataError("DDP %s was invalid" % field)
    missing = series["missing_tokens"]
    if (
        not isinstance(missing, list) or not missing or
        any(not isinstance(item, str) for item in missing) or
        len(missing) != len(set(missing))
    ):
        raise FedDdpDataError("DDP missing-token set was invalid")
    for column in columns:
        if not _TOKEN_RE.match(series["series_id_prefix"] + column):
            raise FedDdpDataError("DDP projected series identity was invalid")
    unique_identifier_label = series.get(
        "expected_unique_identifier_label",
        "Unique Identifier:",
    )
    if unique_identifier_label not in (
        "Unique Identifier:",
        "Unique Identifier: ",
    ):
        raise FedDdpDataError(
            "DDP unique-identifier metadata label was invalid"
        )
    return columns


def _reference_period(raw_value, frequency):
    if frequency == "quarterly":
        match = _QUARTER_RE.match(raw_value)
        if not match:
            raise FedDdpDataError("DDP quarterly period was invalid")
        month = (int(match.group(2)) - 1) * 3 + 1
        return "%s-%02d-01" % (match.group(1), month)
    if frequency == "monthly":
        if not _MONTH_RE.match(raw_value):
            raise FedDdpDataError("DDP monthly period was invalid")
        return raw_value + "-01"
    try:
        parsed = datetime.strptime(raw_value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise FedDdpDataError("DDP daily period was invalid")
    if parsed.isoformat() != raw_value:
        raise FedDdpDataError("DDP daily period was not canonical")
    return raw_value


def parse_fed_ddp_csv(series, body):
    """Return validated DDP observations without assigning scientific meaning."""
    _validate_series(series)
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise FedDdpDataError("DDP CSV was not valid UTF-8: %s" % exc)
    elif isinstance(body, str):
        text = body
    else:
        raise TypeError("DDP CSV must be bytes or str")

    rows = list(csv.reader(io.StringIO(text, newline="")))
    if len(rows) < 7:
        raise FedDdpDataError("DDP CSV did not contain metadata and data rows")
    width = len(series["expected_columns"]) + 1
    if any(len(row) != width for row in rows):
        raise FedDdpDataError("DDP CSV row width was not exact")
    metadata_labels = list(_DEFAULT_METADATA_LABELS)
    metadata_labels[4] = series.get(
        "expected_unique_identifier_label",
        "Unique Identifier:",
    )
    if tuple(row[0] for row in rows[:6]) != tuple(metadata_labels):
        raise FedDdpDataError("DDP metadata label order was not exact")

    columns = rows[5][1:]
    if columns != series["expected_columns"]:
        raise FedDdpDataError("DDP series column set or order changed")
    descriptions = rows[0][1:]
    if any(not item or "\r" in item or "\n" in item for item in descriptions):
        raise FedDdpDataError("DDP series description was invalid")
    if rows[1][1:] != [series["expected_unit"]] * len(columns):
        raise FedDdpDataError("DDP unit metadata changed")
    if rows[2][1:] != [series["expected_multiplier"]] * len(columns):
        raise FedDdpDataError("DDP multiplier metadata changed")
    if rows[3][1:] != [series["expected_currency"]] * len(columns):
        raise FedDdpDataError("DDP currency metadata changed")
    identifiers = rows[4][1:]
    expected_identifiers = [
        series["identifier_prefix"] + column
        for column in columns
    ]
    if identifiers != expected_identifiers:
        raise FedDdpDataError("DDP unique-identifier mapping changed")

    missing_tokens = frozenset(series["missing_tokens"])
    seen_periods = set()
    observations = []
    available_count = 0
    for row in rows[6:]:
        publisher_period = row[0]
        reference_period = _reference_period(
            publisher_period,
            series["date_frequency"],
        )
        if publisher_period in seen_periods:
            raise FedDdpDataError("DDP CSV contained a duplicate period")
        seen_periods.add(publisher_period)
        for index, column in enumerate(columns):
            raw_value = row[index + 1]
            if raw_value in missing_tokens:
                value = None
            else:
                if not _DECIMAL_RE.match(raw_value):
                    raise FedDdpDataError(
                        "DDP value for %s was not a canonical decimal" % column
                    )
                value = raw_value
                available_count += 1
            observations.append({
                "label": descriptions[index],
                "publisher_field": column,
                "publisher_identifier": identifiers[index],
                "publisher_period": publisher_period,
                "reference_period": reference_period,
                "series_id": series["series_id_prefix"] + column,
                "value": value,
            })
    if not observations or not available_count:
        raise FedDdpDataError("DDP CSV contained no available observations")
    return observations
