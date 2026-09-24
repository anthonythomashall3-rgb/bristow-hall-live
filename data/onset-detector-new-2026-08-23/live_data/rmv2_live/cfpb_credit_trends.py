"""Strict CFPB Consumer Credit Trends national-series parsing.

This module performs no network I/O and does not assign scientific weight.
It validates the publisher's complete row schema and all row identities while
projecting only the national ``all/all`` published estimates.  Demographic and
geographic rows remain preserved in the immutable raw source object for later
separately reviewed parsers.
"""

from __future__ import absolute_import

import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


class CfpbCreditTrendsDataError(ValueError):
    """Raised when CFPB bytes violate the reviewed source contract."""


HEADER = (
    "month",
    "date",
    "series",
    "subgroup",
    "subgroup_level",
    "loan_type",
    "value_type",
    "value",
    "value_yoy",
)
SERIES_LOANS = {
    "Credit Tightness Index": ("AUT", "CRC", "MTG"),
    "Dollar Volume": ("AUT", "CRC", "MTG", "STU"),
    "Inquiry Index": ("AUT", "CRC", "MTG"),
    "Originations": ("AUT", "CRC", "MTG", "STU"),
}
SERIES_TOKENS = {
    "Credit Tightness Index": "CREDIT_TIGHTNESS_INDEX",
    "Dollar Volume": "DOLLAR_VOLUME",
    "Inquiry Index": "INQUIRY_INDEX",
    "Originations": "ORIGINATIONS",
}
VALUE_TYPES = {
    "Seasonally Adjusted": "SA",
    "Unadjusted": "NSA",
}
SUBGROUPS = frozenset(("all", "age", "income", "map", "score"))
SUBGROUP_LEVELS = {
    "all": frozenset(("all",)),
    "age": frozenset((
        "30-44",
        "45-64",
        "65 and older",
        "Younger than 30",
    )),
    "income": frozenset(("High", "Low", "Middle", "Moderate")),
    "map": frozenset((
        "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL",
        "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA",
        "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE",
        "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV",
        "WY",
    )),
    "score": frozenset((
        "Deep Subprime",
        "Near Prime",
        "Prime",
        "Subprime",
        "Superprime",
    )),
}
VALUE_UNITS = {
    "Credit Tightness Index": "index Jan 2010=100",
    "Dollar Volume": "estimated USD",
    "Inquiry Index": "index Jan 2010=100",
    "Originations": "estimated loan count",
}
VALUE_LABELS = {
    "Credit Tightness Index": "CFPB national credit tightness index",
    "Dollar Volume": "CFPB estimated national loan dollar volume",
    "Inquiry Index": "CFPB national credit inquiry index",
    "Originations": "CFPB estimated national loan originations",
}
EXPECTED_NATIONAL_IDENTITIES = frozenset(
    (series, loan_type, value_type)
    for series, loan_types in SERIES_LOANS.items()
    for loan_type in loan_types
    for value_type in VALUE_TYPES
)

_MONTH_INDEX_RE = re.compile(r"^(?:0|[1-9]\d*)$")
_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
_DECIMAL_RE = re.compile(
    r"^-?(?:(?:0|[1-9]\d*)(?:\.\d+)?|\.\d+)$"
)
_SCIENTIFIC_DECIMAL_RE = re.compile(
    r"^-?(?:(?:0|[1-9]\d*)(?:\.\d+)?|\.\d+)[eE][+-]?\d+$"
)


def _canonical_decimal(value, field, missing_allowed, signed):
    if value == "" and missing_allowed:
        return None
    if not isinstance(value, str):
        raise CfpbCreditTrendsDataError(
            "%s was not a canonical finite decimal" % field
        )
    if _SCIENTIFIC_DECIMAL_RE.match(value):
        try:
            value = format(Decimal(value), "f")
        except InvalidOperation:
            raise CfpbCreditTrendsDataError(
                "%s was not a canonical finite decimal" % field
            )
    if not _DECIMAL_RE.match(value):
        raise CfpbCreditTrendsDataError(
            "%s was not a canonical finite decimal" % field
        )
    if not signed and value.startswith("-"):
        raise CfpbCreditTrendsDataError(
            "%s must be nonnegative" % field
        )
    if value.startswith("-."):
        return "-0" + value[1:]
    if value.startswith("."):
        return "0" + value
    return value


def _month_identity(raw_month, raw_date):
    if (
        not isinstance(raw_month, str) or
        not _MONTH_INDEX_RE.match(raw_month)
    ):
        raise CfpbCreditTrendsDataError(
            "CFPB month index was not a canonical nonnegative integer"
        )
    match = _MONTH_RE.match(raw_date or "")
    if not match:
        raise CfpbCreditTrendsDataError("CFPB date was not canonical YYYY-MM")
    try:
        datetime.strptime(raw_date + "-01", "%Y-%m-%d")
    except ValueError:
        raise CfpbCreditTrendsDataError("CFPB date was invalid")
    month_index = int(raw_month)
    expected = (int(match.group(1)) - 2000) * 12 + int(match.group(2)) - 1
    if expected < 0 or month_index != expected:
        raise CfpbCreditTrendsDataError(
            "CFPB month index did not match the publisher date"
        )
    return month_index, raw_date + "-01"


def _exact_text(value, field):
    if (
        not isinstance(value, str) or not value or
        value != value.strip() or
        "\r" in value or "\n" in value
    ):
        raise CfpbCreditTrendsDataError("%s was not exact text" % field)
    return value


def parse_cfpb_credit_trends_csv(series_metadata, body):
    """Return national published estimates after validating all publisher rows."""
    if series_metadata != {}:
        raise CfpbCreditTrendsDataError(
            "CFPB series metadata must be the exact empty object"
        )
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise CfpbCreditTrendsDataError(
                "CFPB CSV was not valid UTF-8: %s" % exc
            )
    elif isinstance(body, str):
        text = body
    else:
        raise TypeError("CFPB CSV must be bytes or str")

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != HEADER:
        raise CfpbCreditTrendsDataError("CFPB CSV header was not exact")

    selected = []
    all_row_identities = set()
    national_identities = set()
    national_identity_max_month = {}
    for row in reader:
        if row.get(None) or set(row) != set(HEADER):
            raise CfpbCreditTrendsDataError("CFPB CSV row width was not exact")
        if any(value is None for value in row.values()):
            raise CfpbCreditTrendsDataError("CFPB CSV row had a missing cell")

        month_index, reference_period = _month_identity(
            row["month"],
            row["date"],
        )
        series = _exact_text(row["series"], "CFPB series")
        subgroup = _exact_text(row["subgroup"], "CFPB subgroup")
        subgroup_level = _exact_text(
            row["subgroup_level"],
            "CFPB subgroup level",
        )
        loan_type = _exact_text(row["loan_type"], "CFPB loan type")
        value_type = _exact_text(row["value_type"], "CFPB value type")

        if series not in SERIES_LOANS:
            raise CfpbCreditTrendsDataError("CFPB series identity changed")
        if subgroup not in SUBGROUPS:
            raise CfpbCreditTrendsDataError("CFPB subgroup identity changed")
        if subgroup_level not in SUBGROUP_LEVELS[subgroup]:
            raise CfpbCreditTrendsDataError(
                "CFPB subgroup and subgroup level were inconsistent"
            )
        if loan_type not in SERIES_LOANS[series]:
            raise CfpbCreditTrendsDataError(
                "CFPB series and loan type were inconsistent"
            )
        if value_type not in VALUE_TYPES:
            raise CfpbCreditTrendsDataError(
                "CFPB adjustment identity changed"
            )

        if (
            series in ("Credit Tightness Index", "Inquiry Index") and
            subgroup != "all"
        ):
            raise CfpbCreditTrendsDataError(
                "CFPB index series cannot use a non-national subgroup"
            )
        if (
            series == "Originations" and
            subgroup not in ("all", "age", "income", "score")
        ):
            raise CfpbCreditTrendsDataError(
                "CFPB Originations subgroup was not permitted"
            )
        if (
            series == "Dollar Volume" and
            (
                subgroup not in ("all", "age", "income", "map", "score") or
                subgroup == "map" and value_type != "Unadjusted"
            )
        ):
            raise CfpbCreditTrendsDataError(
                "CFPB Dollar Volume subgroup/adjustment was not permitted"
            )

        value = _canonical_decimal(
            row["value"],
            "CFPB value",
            False,
            False,
        )
        value_yoy = _canonical_decimal(
            row["value_yoy"],
            "CFPB value_yoy",
            True,
            True,
        )
        row_identity = (
            row["date"],
            series,
            subgroup,
            subgroup_level,
            loan_type,
            value_type,
        )
        if row_identity in all_row_identities:
            raise CfpbCreditTrendsDataError(
                "CFPB CSV contained a duplicate row identity"
            )
        all_row_identities.add(row_identity)

        if subgroup == "all":
            national_identity = (series, loan_type, value_type)
            national_identities.add(national_identity)
            national_identity_max_month[national_identity] = max(
                month_index,
                national_identity_max_month.get(national_identity, month_index),
            )
            selected.append({
                "adjustment_token": VALUE_TYPES[value_type],
                "label": VALUE_LABELS[series],
                "loan_type": loan_type,
                "month_index": month_index,
                "publisher_period": row["date"],
                "reference_period": reference_period,
                "series": series,
                "series_token": SERIES_TOKENS[series],
                "subgroup": subgroup,
                "subgroup_level": subgroup_level,
                "value": value,
                "value_type": value_type,
                "value_unit": VALUE_UNITS[series],
                "value_yoy": value_yoy,
            })

    if not selected:
        raise CfpbCreditTrendsDataError(
            "CFPB CSV contained no national observations"
        )
    if national_identities != EXPECTED_NATIONAL_IDENTITIES:
        missing = sorted(EXPECTED_NATIONAL_IDENTITIES - national_identities)
        extra = sorted(national_identities - EXPECTED_NATIONAL_IDENTITIES)
        raise CfpbCreditTrendsDataError(
            "CFPB national identity set changed; missing=%r extra=%r" %
            (missing, extra)
        )

    observations = []
    for item in selected:
        identity = (
            item["series"],
            item["loan_type"],
            item["value_type"],
        )
        recent = (
            item["month_index"] >=
            national_identity_max_month[identity] - 5
        )
        revision_status = (
            "recent_six_month_values_may_be_nonfinal"
            if recent else
            "historical_current_revised_capture"
        )
        base_id = "CFPB.CCT.%s.%s.%s" % (
            item["series_token"],
            item["loan_type"],
            item["adjustment_token"],
        )
        publisher_identity = {
            "loan_type": item["loan_type"],
            "series": item["series"],
            "subgroup": item["subgroup"],
            "subgroup_level": item["subgroup_level"],
            "value_type": item["value_type"],
        }
        observations.append({
            "label": item["label"],
            "publisher_field": "value",
            "publisher_identity": publisher_identity,
            "publisher_month_index": str(item["month_index"]),
            "publisher_period": item["publisher_period"],
            "publisher_revision_status": revision_status,
            "reference_period": item["reference_period"],
            "series_id": base_id + ".VALUE",
            "unit": item["value_unit"],
            "value": item["value"],
        })
        observations.append({
            "label": item["label"] + ", year-over-year change",
            "publisher_field": "value_yoy",
            "publisher_identity": publisher_identity,
            "publisher_month_index": str(item["month_index"]),
            "publisher_period": item["publisher_period"],
            "publisher_revision_status": revision_status,
            "reference_period": item["reference_period"],
            "series_id": base_id + ".YOY_PCT",
            "unit": "percent change year over year",
            "value": item["value_yoy"],
        })
    return observations
