"""Strict CFPB state and national mortgage-performance normalization."""

from __future__ import absolute_import

import csv
import io
import re
from decimal import Decimal


class CfpbMortgageDataError(RuntimeError):
    pass


DECIMAL_RE = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
EXPECTED_GEOGRAPHIES = [
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


def _month_range(first, last):
    if not re.match(r"^\d{4}-\d{2}$", first) or not re.match(
        r"^\d{4}-\d{2}$", last
    ):
        raise CfpbMortgageDataError("CFPB month contract was invalid")
    year, month = [int(value) for value in first.split("-")]
    last_year, last_month = [int(value) for value in last.split("-")]
    result = []
    while (year, month) <= (last_year, last_month):
        if month < 1 or month > 12:
            raise CfpbMortgageDataError("CFPB month contract was invalid")
        result.append("%04d-%02d" % (year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    if not result or result[-1] != last:
        raise CfpbMortgageDataError("CFPB month range was invalid")
    return result


def parse_cfpb_mortgage_performance_state_csv(series, body):
    expected_series = {
        "atomic_bundle_id",
        "atomic_bundle_members",
        "data_through",
        "expected_geography_contract",
        "first_reference_period",
        "metric_code",
        "metric_label",
    }
    if not isinstance(series, dict) or set(series) != expected_series:
        raise CfpbMortgageDataError("CFPB mortgage series metadata was not exact")
    expected_members = [
        "cfpb_mortgage_performance_state_30_89_current",
        "cfpb_mortgage_performance_state_90_plus_current",
    ]
    if (
        series["atomic_bundle_id"] !=
        "cfpb_mortgage_performance_state_current.v1" or
        series["atomic_bundle_members"] != expected_members or
        series["expected_geography_contract"] !=
        "national_plus_50_states_and_DC.v1" or
        series["first_reference_period"] != "2008-01" or
        series["metric_code"] not in ("30_89", "90_PLUS") or
        not isinstance(series["metric_label"], str) or
        not series["metric_label"]
    ):
        raise CfpbMortgageDataError("CFPB mortgage source identity differed")
    try:
        text = body.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise CfpbMortgageDataError("CFPB mortgage CSV was not UTF-8") from exc
    if "\x00" in text or text.lstrip().lower().startswith(("<html", "<!doctype")):
        raise CfpbMortgageDataError("CFPB mortgage response was not CSV")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows or any(not row for row in rows):
        raise CfpbMortgageDataError("CFPB mortgage CSV contained blank rows")
    expected_months = _month_range(
        series["first_reference_period"],
        series["data_through"],
    )
    expected_header = ["RegionType", "Name", "FIPSCode"] + expected_months
    if rows[0] != expected_header:
        raise CfpbMortgageDataError("CFPB mortgage header differed")
    if len(rows[1:]) != len(EXPECTED_GEOGRAPHIES):
        raise CfpbMortgageDataError("CFPB mortgage geography count differed")

    records = []
    for row_index, row in enumerate(rows[1:]):
        if len(row) != len(expected_header):
            raise CfpbMortgageDataError("CFPB mortgage row width differed")
        identity = tuple(row[:3])
        if identity != EXPECTED_GEOGRAPHIES[row_index]:
            raise CfpbMortgageDataError("CFPB mortgage geography identity differed")
        region_type, name, raw_fips = identity
        if region_type == "National":
            geography = "NATIONAL"
            normalized_fips = None
        else:
            match = re.match(r"^'(\d{2})'$", raw_fips)
            if not match:
                raise CfpbMortgageDataError("CFPB mortgage state FIPS differed")
            normalized_fips = match.group(1)
            geography = "STATE.%s" % normalized_fips
        series_id = "CFPB.MPT.%s.%s" % (
            series["metric_code"],
            geography,
        )
        for period, value in zip(expected_months, row[3:]):
            if not DECIMAL_RE.match(value):
                raise CfpbMortgageDataError(
                    "CFPB mortgage value was not a canonical decimal"
                )
            if Decimal(value) < 0 or Decimal(value) > 100:
                raise CfpbMortgageDataError("CFPB mortgage value was out of range")
            records.append({
                "atomic_bundle_id": series["atomic_bundle_id"],
                "bundle_member_metric": series["metric_code"],
                "data_through": series["data_through"],
                "label": "%s — %s" % (series["metric_label"], name),
                "measurement_basis": (
                    "publisher nationally representative five-percent "
                    "sample estimate"
                ),
                "provider_vintage_kind": "current_revised",
                "publisher_fips": normalized_fips,
                "publisher_fips_token": raw_fips,
                "publisher_geography_name": name,
                "publisher_geography_type": region_type,
                "publisher_imputation_present": True,
                "reference_period": period,
                "series_id": series_id,
                "unit": "percent of outstanding mortgages",
                "value": value,
                "value_status": "actual",
            })
    return records
