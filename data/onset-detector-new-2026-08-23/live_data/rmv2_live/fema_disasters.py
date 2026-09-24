"""Strict OpenFEMA v2 disaster-declaration parsing and aggregation.

FEMA declaration rows are administrative events and designated-area records.
They are useful for disturbance attribution, but they are not measurements of
disaster severity, recession stress, or chronology.
"""

from __future__ import absolute_import

import json
import re
from datetime import datetime


class FemaDisasterDataError(ValueError):
    """Raised when OpenFEMA bytes violate the reviewed source contract."""


ROW_FIELDS = frozenset((
    "femaDeclarationString",
    "disasterNumber",
    "state",
    "declarationType",
    "declarationDate",
    "fyDeclared",
    "incidentType",
    "declarationTitle",
    "ihProgramDeclared",
    "iaProgramDeclared",
    "paProgramDeclared",
    "hmProgramDeclared",
    "incidentBeginDate",
    "incidentEndDate",
    "disasterCloseoutDate",
    "tribalRequest",
    "fipsStateCode",
    "fipsCountyCode",
    "placeCode",
    "designatedArea",
    "declarationRequestNumber",
    "lastIAFilingDate",
    "incidentId",
    "region",
    "designatedIncidentTypes",
    "lastRefresh",
    "hash",
    "id",
))
SERIES_FIELDS = frozenset((
    "declaration_year",
    "entity_key",
    "page_limit",
    "projection",
))
BOOLEAN_FIELDS = (
    "ihProgramDeclared",
    "iaProgramDeclared",
    "paProgramDeclared",
    "hmProgramDeclared",
    "tribalRequest",
)
NULLABLE_DATE_FIELDS = (
    "incidentEndDate",
    "disasterCloseoutDate",
    "lastIAFilingDate",
)
DECLARATION_TYPES = frozenset(("DR", "EM", "FM"))
SEMANTIC_GUARD = (
    "administrative declaration and designated-area counts; "
    "not disaster severity, recession stress, or chronology"
)

_INTEGER_RE = re.compile(r"^(?:0|[1-9]\d*)$")
_STATE_RE = re.compile(r"^[A-Z]{2}$")
_FIPS_STATE_RE = re.compile(r"^\d{2}$")
_FIPS_COUNTY_RE = re.compile(r"^\d{3}$")
_PLACE_CODE_RE = re.compile(r"^(?:0|[1-9]\d{0,4})$")
_HASH_RE = re.compile(r"^[0-9a-f]{40}$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}$"
)
_UTC_MILLISECOND_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
)
_DECLARATION_RE = re.compile(r"^(DR|EM|FM)-([1-9]\d{3})-([A-Z]{2})$")


def _strict_json_loads(body):
    if not isinstance(body, bytes):
        raise TypeError("OpenFEMA response must be bytes")

    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise FemaDisasterDataError(
                    "OpenFEMA JSON key was duplicated"
                )
            result[key] = value
        return result

    def reject_constant(token):
        raise FemaDisasterDataError(
            "OpenFEMA JSON number was non-finite: %s" % token
        )

    try:
        return json.loads(
            body.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs_hook,
            parse_float=str,
            parse_int=str,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FemaDisasterDataError(
            "OpenFEMA response was not strict JSON: %s" % exc
        )


def _exact_text(value, label, nullable=False, trim=False):
    if nullable and value is None:
        return None
    # trim=True: descriptive free-text field (e.g. declarationTitle) where the
    # publisher emits surrounding whitespace as formatting noise. Measured
    # 20260815: 86 current-year rows carried a trailing space. Strip it, keep
    # the internal-control-char guard. Identity/structural fields stay strict.
    if trim and isinstance(value, str):
        value = value.strip()
    if (
        not isinstance(value, str) or
        not value or
        value != value.strip() or
        "\x00" in value or
        "\r" in value or
        "\n" in value
    ):
        raise FemaDisasterDataError(
            "OpenFEMA %s was not exact text" % label
        )
    return value


def _canonical_integer(value, label, minimum=None, maximum=None):
    if not isinstance(value, str) or not _INTEGER_RE.match(value):
        raise FemaDisasterDataError(
            "OpenFEMA %s was not a canonical integer" % label
        )
    parsed = int(value)
    if minimum is not None and parsed < minimum:
        raise FemaDisasterDataError(
            "OpenFEMA %s was outside its domain" % label
        )
    if maximum is not None and parsed > maximum:
        raise FemaDisasterDataError(
            "OpenFEMA %s was outside its domain" % label
        )
    return parsed


def _utc_millisecond(value, label, nullable=False):
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not _UTC_MILLISECOND_RE.match(value):
        raise FemaDisasterDataError(
            "OpenFEMA %s was not an exact UTC timestamp" % label
        )
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise FemaDisasterDataError(
            "OpenFEMA %s was not a valid UTC timestamp" % label
        ) from exc
    return value


def _validate_series_metadata(series_metadata):
    if (
        not isinstance(series_metadata, dict) or
        frozenset(series_metadata) != SERIES_FIELDS or
        not isinstance(series_metadata["declaration_year"], int) or
        series_metadata["declaration_year"] < 1953 or
        series_metadata["entity_key"] != "DisasterDeclarationsSummaries" or
        not isinstance(series_metadata["page_limit"], int) or
        series_metadata["page_limit"] < 1 or
        series_metadata["projection"] !=
        "state_and_national_declaration_aggregates_v1"
    ):
        raise FemaDisasterDataError(
            "OpenFEMA series metadata was not exact"
        )
    return series_metadata


def _validate_row(row, declaration_year):
    if not isinstance(row, dict) or frozenset(row) != ROW_FIELDS:
        raise FemaDisasterDataError("OpenFEMA row field set changed")

    for field in BOOLEAN_FIELDS:
        if not isinstance(row[field], bool):
            raise FemaDisasterDataError(
                "OpenFEMA %s was not boolean" % field
            )

    disaster_number = _canonical_integer(
        row["disasterNumber"],
        "disasterNumber",
        minimum=1,
    )
    fiscal_year = _canonical_integer(
        row["fyDeclared"],
        "fyDeclared",
        minimum=1953,
        maximum=9999,
    )
    region = None
    if row["region"] is not None:
        region = _canonical_integer(
            row["region"],
            "region",
            minimum=1,
            maximum=10,
        )

    state = row["state"]
    declaration_type = row["declarationType"]
    if not isinstance(state, str) or not _STATE_RE.match(state):
        raise FemaDisasterDataError("OpenFEMA state was invalid")
    if declaration_type not in DECLARATION_TYPES:
        raise FemaDisasterDataError(
            "OpenFEMA declarationType was invalid"
        )

    declaration_date = _utc_millisecond(
        row["declarationDate"],
        "declarationDate",
    )
    incident_begin = _utc_millisecond(
        row["incidentBeginDate"],
        "incidentBeginDate",
    )
    last_refresh = _utc_millisecond(
        row["lastRefresh"],
        "lastRefresh",
    )
    nullable_dates = {
        field: _utc_millisecond(
            row[field],
            field,
            nullable=True,
        )
        for field in NULLABLE_DATE_FIELDS
    }
    if int(declaration_date[:4]) != declaration_year:
        raise FemaDisasterDataError(
            "OpenFEMA declaration escaped the configured year"
        )
    if nullable_dates["incidentEndDate"] is not None:
        if nullable_dates["incidentEndDate"] < incident_begin:
            raise FemaDisasterDataError(
                "OpenFEMA incident dates were inconsistent"
            )

    declaration_string = row["femaDeclarationString"]
    match = (
        _DECLARATION_RE.match(declaration_string)
        if isinstance(declaration_string, str)
        else None
    )
    if (
        match is None or
        match.group(1) != declaration_type or
        int(match.group(2)) != disaster_number or
        match.group(3) != state
    ):
        raise FemaDisasterDataError(
            "OpenFEMA declaration identity was inconsistent"
        )

    if (
        not isinstance(row["fipsStateCode"], str) or
        not _FIPS_STATE_RE.match(row["fipsStateCode"]) or
        not isinstance(row["fipsCountyCode"], str) or
        not _FIPS_COUNTY_RE.match(row["fipsCountyCode"]) or
        not isinstance(row["placeCode"], str) or
        not _PLACE_CODE_RE.match(row["placeCode"])
    ):
        raise FemaDisasterDataError("OpenFEMA geographic code was invalid")
    if (
        not isinstance(row["hash"], str) or
        not _HASH_RE.match(row["hash"]) or
        not isinstance(row["id"], str) or
        not _UUID_RE.match(row["id"])
    ):
        raise FemaDisasterDataError(
            "OpenFEMA record identity was invalid"
        )

    _exact_text(row["incidentType"], "incidentType")
    row["declarationTitle"] = _exact_text(
        row["declarationTitle"], "declarationTitle", trim=True,
    )
    _exact_text(row["designatedArea"], "designatedArea")
    _exact_text(
        row["designatedIncidentTypes"],
        "designatedIncidentTypes",
        nullable=True,
    )
    _canonical_integer(
        row["declarationRequestNumber"],
        "declarationRequestNumber",
        minimum=1,
    )
    _canonical_integer(row["incidentId"], "incidentId", minimum=1)

    result = dict(row)
    result.update({
        "declaration_date": declaration_date,
        "declaration_day": declaration_date[:10],
        "disaster_number": disaster_number,
        "fiscal_year": fiscal_year,
        "incident_begin": incident_begin,
        "last_refresh": last_refresh,
        "nullable_dates": nullable_dates,
        "region_number": region,
    })
    return result


def _group_context(rows):
    return {
        "publisher_declaration_ids": sorted(set(
            row["femaDeclarationString"] for row in rows
        )),
        "publisher_declaration_titles": sorted(set(
            row["declarationTitle"] for row in rows
        )),
        "publisher_disaster_numbers": sorted(set(
            str(row["disaster_number"]) for row in rows
        )),
        "publisher_incident_begin_dates": sorted(set(
            row["incident_begin"] for row in rows
        )),
        "publisher_incident_end_dates": sorted(set(
            row["nullable_dates"]["incidentEndDate"]
            for row in rows
            if row["nullable_dates"]["incidentEndDate"] is not None
        )),
        "publisher_incident_types": sorted(set(
            row["incidentType"] for row in rows
        )),
        "publisher_last_refresh_max": max(
            row["last_refresh"] for row in rows
        ),
        "publisher_open_incident_count": sum(
            1 for row in rows
            if row["nullable_dates"]["incidentEndDate"] is None
        ),
        "publisher_record_hashes": sorted(
            row["hash"] for row in rows
        ),
        "publisher_record_ids": sorted(
            row["id"] for row in rows
        ),
    }


def parse_fema_disaster_declarations_json(series_metadata, body):
    """Return deterministic state and national declaration-count records."""
    series = _validate_series_metadata(series_metadata)
    payload = _strict_json_loads(body)
    entity_key = series["entity_key"]
    if not isinstance(payload, dict) or frozenset(payload) != {entity_key}:
        raise FemaDisasterDataError(
            "OpenFEMA response envelope changed"
        )
    rows = payload[entity_key]
    if not isinstance(rows, list) or not rows:
        raise FemaDisasterDataError(
            "OpenFEMA response contained no rows"
        )
    if len(rows) >= series["page_limit"]:
        raise FemaDisasterDataError(
            "OpenFEMA response may be truncated at its page limit"
        )

    validated = [
        _validate_row(row, series["declaration_year"])
        for row in rows
    ]
    record_ids = [row["id"] for row in validated]
    if len(record_ids) != len(set(record_ids)):
        raise FemaDisasterDataError(
            "OpenFEMA record UUID was duplicated"
        )
    composites = [
        (row["disaster_number"], row["placeCode"])
        for row in validated
    ]
    if len(composites) != len(set(composites)):
        raise FemaDisasterDataError(
            "OpenFEMA disaster/place identity was duplicated"
        )
    order = [
        (
            row["declaration_date"],
            row["disaster_number"],
            row["placeCode"],
            row["id"],
        )
        for row in validated
    ]
    if order != sorted(order):
        raise FemaDisasterDataError(
            "OpenFEMA rows were not in configured stable order"
        )

    grouped = {}
    for row in validated:
        for geography in (row["state"], "US"):
            key = (
                row["declaration_day"],
                geography,
                row["declarationType"],
            )
            grouped.setdefault(key, []).append(row)

    result = []
    for key in sorted(grouped):
        declaration_day, geography, declaration_type = key
        group_rows = grouped[key]
        context = _group_context(group_rows)
        event_count = len(set(
            row["femaDeclarationString"] for row in group_rows
        ))
        measures = (
            ("EVENT_COUNT", event_count, "declarations"),
            (
                "DESIGNATED_AREA_COUNT",
                len(group_rows),
                "designated areas",
            ),
        )
        for measure, value, unit in measures:
            item = dict(context)
            item.update({
                "label": (
                    "FEMA %s %s %s" %
                    (
                        geography,
                        declaration_type,
                        measure.lower().replace("_", " "),
                    )
                ),
                "publisher_declaration_type": declaration_type,
                "publisher_geography": geography,
                "publisher_semantic_guard": SEMANTIC_GUARD,
                "reference_period": declaration_day,
                "series_id": "FEMA.DECLARATIONS.%s.%s.%s" % (
                    geography,
                    declaration_type,
                    measure,
                ),
                "unit": unit,
                "value": str(value),
            })
            result.append(item)
    return result
