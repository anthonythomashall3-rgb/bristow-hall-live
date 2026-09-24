"""Strict normalization for the current Daily Treasury Statement tax lane.

This module performs no network I/O.  It is intentionally separate from the
live collector registry so the parser can be reviewed before the source is
enabled.  The current FiscalData concept must never be silently joined to the
legacy ``Withheld Income and Employment Taxes`` series.
"""

from __future__ import absolute_import

import json
import re
from datetime import datetime

from .canonical import canonical_json_bytes


SCHEMA_VERSION = "recession-monitor-v2.treasury-dts-current-record.v1"
SOURCE_ID = "treasury_dts_withheld_individual_fica_current"
METHOD_VERSION = "treasury_dts_withheld_individual_fica_current.v1"
ENDPOINT = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
    "v1/accounting/dts/deposits_withdrawals_operating_cash"
)

CURRENT_CONCEPT = "Taxes - Withheld Individual/FICA"
LEGACY_CONCEPT = "Withheld Income and Employment Taxes"
CURRENT_CONCEPT_START = "2023-02-14"

_ACCOUNT_TYPE = "Treasury General Account (TGA)"
_TRANSACTION_TYPE = "Deposits"
_TABLE_NUMBER = "II"
_TABLE_NAME = "Deposits and Withdrawals of Operating Cash"

_TOP_LEVEL_FIELDS = frozenset(("data", "links", "meta"))
_META_FIELDS = frozenset((
    "count",
    "dataFormats",
    "dataTypes",
    "labels",
    "total-count",
    "total-pages",
))
_LINK_FIELDS = frozenset(("first", "last", "next", "prev", "self"))
_ROW_FIELDS = frozenset((
    "account_type",
    "record_calendar_day",
    "record_calendar_month",
    "record_calendar_quarter",
    "record_calendar_year",
    "record_date",
    "record_fiscal_quarter",
    "record_fiscal_year",
    "src_line_nbr",
    "table_nm",
    "table_nbr",
    "transaction_catg",
    "transaction_catg_desc",
    "transaction_fytd_amt",
    "transaction_mtd_amt",
    "transaction_today_amt",
    "transaction_type",
))
_REQUIRED_ROW_FIELDS = frozenset((
    "account_type",
    "record_date",
    "src_line_nbr",
    "table_nm",
    "table_nbr",
    "transaction_catg",
    "transaction_fytd_amt",
    "transaction_mtd_amt",
    "transaction_today_amt",
    "transaction_type",
))
_AMOUNT_FIELDS = (
    ("transaction_today_amt", "today_amt"),
    ("transaction_mtd_amt", "mtd_amt"),
    ("transaction_fytd_amt", "fytd_amt"),
)
_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_NONNEGATIVE_INTEGER_RE = re.compile(r"^(?:0|[1-9]\d*)$")
_UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
)


class TreasuryDtsDataError(ValueError):
    """Raised when DTS bytes do not satisfy the reviewed source contract."""


class _PublisherNumber(str):
    """Marks an unquoted JSON number without converting it to float or int."""


def _reject_constant(token):
    raise TreasuryDtsDataError(
        "DTS JSON contained a non-finite number: %s" % token
    )


def _pairs_hook(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise TreasuryDtsDataError(
                "DTS JSON contained a duplicate key: %s" % key
            )
        value[key] = item
    return value


def _load_json(data):
    if isinstance(data, bytes):
        if not data:
            raise TreasuryDtsDataError("DTS response was empty")
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise TreasuryDtsDataError(
                "DTS response was not valid UTF-8: %s" % exc
            )
    elif isinstance(data, str):
        if not data:
            raise TreasuryDtsDataError("DTS response was empty")
        text = data
    else:
        raise TypeError("DTS response must be bytes or str")

    prefix = text.lstrip()[:64].lower()
    if prefix.startswith("<!doctype html") or prefix.startswith("<html"):
        raise TreasuryDtsDataError("DTS response was HTML, not JSON")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_hook,
            parse_float=_PublisherNumber,
            parse_int=_PublisherNumber,
            parse_constant=_reject_constant,
        )
    except TreasuryDtsDataError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TreasuryDtsDataError("DTS response was malformed JSON: %s" % exc)


def _exact_string(value, label):
    if type(value) is not str or not value:
        raise TreasuryDtsDataError("%s must be a nonempty JSON string" % label)
    return value


def _date(value, label):
    value = _exact_string(value, label)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise TreasuryDtsDataError("%s was not a valid ISO date" % label)
    return parsed


def _retrieval_timestamp(value):
    value = _exact_string(value, "retrieved_at")
    if not _UTC_TIMESTAMP_RE.match(value):
        raise TreasuryDtsDataError(
            "retrieved_at must be whole-second RFC 3339 UTC"
        )
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise TreasuryDtsDataError("retrieved_at was not a valid UTC timestamp")
    return value


def _decimal_string(value, label):
    if type(value) is not str or not _DECIMAL_RE.match(value):
        raise TreasuryDtsDataError(
            "%s must be a quoted finite decimal string" % label
        )
    return value


def _metadata_integer(value, label):
    if (
        not isinstance(value, _PublisherNumber) or
        not _NONNEGATIVE_INTEGER_RE.match(value)
    ):
        raise TreasuryDtsDataError(
            "%s must be an unquoted nonnegative integer" % label
        )
    return int(value)


def _validate_metadata(payload, row_count):
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise TreasuryDtsDataError("DTS response lacked a meta object")
    unknown = set(meta) - _META_FIELDS
    if unknown:
        raise TreasuryDtsDataError(
            "DTS meta contained unknown fields: %s" %
            ", ".join(sorted(unknown))
        )
    missing = _META_FIELDS - set(meta)
    if missing:
        raise TreasuryDtsDataError(
            "DTS meta lacked required fields: %s" %
            ", ".join(sorted(missing))
        )

    count = _metadata_integer(meta["count"], "meta.count")
    total_count = _metadata_integer(
        meta["total-count"], "meta.total-count"
    )
    total_pages = _metadata_integer(
        meta["total-pages"], "meta.total-pages"
    )
    if count != row_count:
        raise TreasuryDtsDataError("meta.count did not equal the data row count")
    if total_count < count:
        raise TreasuryDtsDataError("meta.total-count was smaller than meta.count")
    if total_pages < 1:
        raise TreasuryDtsDataError("meta.total-pages must be positive")

    metadata_key_sets = []
    for field in ("labels", "dataTypes", "dataFormats"):
        mapping = meta[field]
        if not isinstance(mapping, dict):
            raise TreasuryDtsDataError("meta.%s must be an object" % field)
        unknown_nested = set(mapping) - _ROW_FIELDS
        if unknown_nested:
            raise TreasuryDtsDataError(
                "meta.%s described unknown fields: %s" % (
                    field,
                    ", ".join(sorted(unknown_nested)),
                )
            )
        if not _REQUIRED_ROW_FIELDS.issubset(set(mapping)):
            raise TreasuryDtsDataError(
                "meta.%s did not describe every required DTS field" % field
            )
        for key, value in mapping.items():
            _exact_string(value, "meta.%s.%s" % (field, key))
        metadata_key_sets.append(set(mapping))
    if not (
        metadata_key_sets[0] ==
        metadata_key_sets[1] ==
        metadata_key_sets[2]
    ):
        raise TreasuryDtsDataError(
            "DTS metadata field maps described different schemas"
        )


def _validate_links(payload):
    links = payload.get("links")
    if not isinstance(links, dict):
        raise TreasuryDtsDataError("DTS response lacked a links object")
    if set(links) != _LINK_FIELDS:
        raise TreasuryDtsDataError(
            "DTS links did not have the exact pagination fields"
        )
    for key, value in links.items():
        if value is not None and type(value) is not str:
            raise TreasuryDtsDataError(
                "DTS links.%s must be a string or null" % key
            )


def _validate_calendar_fields(row, parsed_date):
    expected = {
        "record_calendar_day": "%02d" % parsed_date.day,
        "record_calendar_month": "%02d" % parsed_date.month,
        "record_calendar_quarter": str(((parsed_date.month - 1) // 3) + 1),
        "record_calendar_year": "%04d" % parsed_date.year,
        "record_fiscal_quarter": str(((parsed_date.month - 10) % 12) // 3 + 1),
        "record_fiscal_year": str(
            parsed_date.year + (1 if parsed_date.month >= 10 else 0)
        ),
    }
    for field, expected_value in expected.items():
        if field in row:
            actual = _exact_string(row[field], field)
            if actual != expected_value:
                raise TreasuryDtsDataError(
                    "%s was inconsistent with record_date" % field
                )


def _normalize_row(row, retrieved_at):
    if not isinstance(row, dict):
        raise TreasuryDtsDataError("DTS data rows must be objects")
    unknown = set(row) - _ROW_FIELDS
    if unknown:
        raise TreasuryDtsDataError(
            "DTS row contained unknown fields: %s" %
            ", ".join(sorted(unknown))
        )
    missing = _REQUIRED_ROW_FIELDS - set(row)
    if missing:
        raise TreasuryDtsDataError(
            "DTS row lacked required fields: %s" %
            ", ".join(sorted(missing))
        )

    record_date = _date(row["record_date"], "record_date")
    record_date_text = record_date.isoformat()
    if record_date_text < CURRENT_CONCEPT_START:
        raise TreasuryDtsDataError(
            "current DTS concept cannot precede %s" % CURRENT_CONCEPT_START
        )

    category = _exact_string(row["transaction_catg"], "transaction_catg")
    if category == LEGACY_CONCEPT:
        raise TreasuryDtsDataError(
            "legacy withheld-tax concept cannot enter the current DTS lane"
        )
    if category != CURRENT_CONCEPT:
        raise TreasuryDtsDataError(
            "DTS row had an unreviewed transaction category"
        )
    expected_semantics = (
        ("account_type", _ACCOUNT_TYPE),
        ("transaction_type", _TRANSACTION_TYPE),
        ("table_nbr", _TABLE_NUMBER),
        ("table_nm", _TABLE_NAME),
    )
    for field, expected in expected_semantics:
        if _exact_string(row[field], field) != expected:
            raise TreasuryDtsDataError(
                "DTS row had an unreviewed %s identity" % field
            )

    source_line = _exact_string(row["src_line_nbr"], "src_line_nbr")
    if not _NONNEGATIVE_INTEGER_RE.match(source_line):
        raise TreasuryDtsDataError(
            "src_line_nbr must be a quoted nonnegative integer"
        )
    _validate_calendar_fields(row, record_date)

    normalized = {
        "account_type": row["account_type"],
        "amount_unit": "USD millions",
        "available_at": retrieved_at,
        "information_set_mode": "current_revised",
        "method_version": METHOD_VERSION,
        "observation_period": record_date_text,
        "observed_at": record_date_text,
        "provenance_url": ENDPOINT,
        "provider_available_at": None,
        "publisher_release_at": None,
        "reference_end": record_date_text,
        "reference_start": record_date_text,
        "retrieved_at": retrieved_at,
        "rights_status": "public_government_source_with_attribution",
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_line_nbr": source_line,
        "table_nm": row["table_nm"],
        "table_nbr": row["table_nbr"],
        "transaction_catg": category,
        "transaction_catg_desc": (
            _exact_string(
                row["transaction_catg_desc"],
                "transaction_catg_desc",
            )
            if "transaction_catg_desc" in row else None
        ),
        "transaction_type": row["transaction_type"],
        "value_status": "actual",
        "vintage_kind": "self_captured_current_api",
    }
    for publisher_field, normalized_field in _AMOUNT_FIELDS:
        normalized[normalized_field] = _decimal_string(
            row[publisher_field], publisher_field
        )
    return normalized


def parse_treasury_dts_json(data, retrieved_at):
    """Return deterministic normalized rows from official FiscalData JSON."""
    retrieved_at = _retrieval_timestamp(retrieved_at)
    payload = _load_json(data)
    if not isinstance(payload, dict):
        raise TreasuryDtsDataError("DTS response root must be an object")
    if set(payload) != _TOP_LEVEL_FIELDS:
        unknown = set(payload) - _TOP_LEVEL_FIELDS
        missing = _TOP_LEVEL_FIELDS - set(payload)
        details = []
        if unknown:
            details.append("unknown=" + ",".join(sorted(unknown)))
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        raise TreasuryDtsDataError(
            "DTS response fields were not exact (%s)" % "; ".join(details)
        )
    rows = payload["data"]
    if not isinstance(rows, list) or not rows:
        raise TreasuryDtsDataError("DTS response contained no data rows")
    _validate_metadata(payload, len(rows))
    _validate_links(payload)

    normalized = [_normalize_row(row, retrieved_at) for row in rows]
    identity_fields = (
        "observation_period",
        "account_type",
        "transaction_type",
        "transaction_catg",
        "table_nbr",
        "source_line_nbr",
    )
    identities = [
        tuple(row[field] for field in identity_fields)
        for row in normalized
    ]
    if len(identities) != len(set(identities)):
        raise TreasuryDtsDataError(
            "DTS response contained duplicate row identities"
        )
    return sorted(
        normalized,
        key=lambda row: tuple(row[field] for field in identity_fields),
    )


def normalize_treasury_dts_bytes(data, retrieved_at):
    """Return canonical UTF-8 JSON bytes for the normalized DTS record list."""
    return canonical_json_bytes(parse_treasury_dts_json(data, retrieved_at))

