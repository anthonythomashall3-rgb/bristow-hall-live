"""Strict parser for the Cleveland Fed quarterly Inflation Nowcast chart feed.

The publisher route is an undocumented FusionCharts JSON payload.  This module
therefore validates the complete currently reviewed envelope before selecting
one final nonempty published value per target-quarter/series path.  It performs
no network I/O and assigns no Recession Monitor scientific weight.
"""

from __future__ import absolute_import

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


class ClevelandNowcastDataError(ValueError):
    """Raised when Cleveland Fed chart bytes violate the source contract."""


TOP_FIELDS = frozenset(("categories", "chart", "dataset"))
CHART_FIELDS = frozenset((
    "_comment",
    "basefont",
    "bgalpha",
    "caption",
    "labelpadding",
    "legendnumcolumns",
    "showborder",
    "showexportdatamenuitem",
    "showtooltip",
    "showvalues",
    "subcaption",
    "yaxisname",
))
CATEGORY_CONTAINER_FIELDS = frozenset(("category",))
CATEGORY_FIELDS = frozenset(("label",))
CATEGORY_LINE_FIELDS = frozenset((
    "color",
    "label",
    "labelposition",
    "lineposition",
    "vline",
))
DATASET_FIELDS = frozenset(("color", "data", "seriesname"))
DATA_FIELDS = frozenset(("tooltext", "value"))
DATA_ANCHOR_FIELDS = frozenset((
    "anchorbgcolor",
    "anchorbordercolor",
    "anchorborderthickness",
    "anchorradius",
    "tooltext",
    "value",
))
NOWCAST_NAMES = (
    "CPI Inflation",
    "Core CPI Inflation",
    "PCE Inflation",
    "Core PCE Inflation",
)
ACTUAL_NAMES = tuple("Actual " + name for name in NOWCAST_NAMES)
ALL_NAMES = frozenset(NOWCAST_NAMES + ACTUAL_NAMES)
NAME_CONTRACT = {
    "CPI Inflation": ("CPI", "NOWCAST", "nowcast"),
    "Core CPI Inflation": ("CORE_CPI", "NOWCAST", "nowcast"),
    "PCE Inflation": ("PCE", "NOWCAST", "nowcast"),
    "Core PCE Inflation": ("CORE_PCE", "NOWCAST", "nowcast"),
    "Actual CPI Inflation": ("CPI", "ACTUAL", "actual"),
    "Actual Core CPI Inflation": ("CORE_CPI", "ACTUAL", "actual"),
    "Actual PCE Inflation": ("PCE", "ACTUAL", "actual"),
    "Actual Core PCE Inflation": ("CORE_PCE", "ACTUAL", "actual"),
}

_QUARTER_RE = re.compile(r"^(\d{4}):Q([1-4])$")
_AS_OF_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
_HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}$")
_DECIMAL_RE = re.compile(
    r"^-?(?:(?:0|[1-9]\d*)(?:\.\d+)?|\.\d+)$"
)
_SCIENTIFIC_RE = re.compile(
    r"^-?(?:(?:0|[1-9]\d*)(?:\.\d+)?|\.\d+)[eE][+-]?\d+$"
)


def _pairs_hook(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ClevelandNowcastDataError(
                "Cleveland JSON contained a duplicate key: %s" % key
            )
        result[key] = value
    return result


def _reject_constant(token):
    raise ClevelandNowcastDataError(
        "Cleveland JSON contained a non-finite number: %s" % token
    )


def _load_json(body):
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ClevelandNowcastDataError(
                "Cleveland JSON was not valid UTF-8: %s" % exc
            )
    elif isinstance(body, str):
        text = body
    else:
        raise TypeError("Cleveland JSON must be bytes or str")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_hook,
            parse_float=str,
            parse_int=str,
            parse_constant=_reject_constant,
        )
    except ClevelandNowcastDataError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClevelandNowcastDataError(
            "Cleveland response was malformed JSON: %s" % exc
        )


def _exact_text(value, field):
    if (
        not isinstance(value, str) or not value or
        value != value.strip() or
        "\r" in value or "\n" in value
    ):
        raise ClevelandNowcastDataError("%s was not exact text" % field)
    return value


def _decimal(value, field):
    if not isinstance(value, str) or not value:
        raise ClevelandNowcastDataError("%s was empty or not text" % field)
    if _SCIENTIFIC_RE.match(value):
        try:
            value = format(Decimal(value), "f")
        except InvalidOperation:
            raise ClevelandNowcastDataError(
                "%s was not a finite decimal" % field
            )
    if not _DECIMAL_RE.match(value):
        raise ClevelandNowcastDataError(
            "%s was not a canonical finite decimal" % field
        )
    if value.startswith("-."):
        return "-0" + value[1:]
    if value.startswith("."):
        return "0" + value
    return value


def _quarter(raw_value):
    match = _QUARTER_RE.match(raw_value or "")
    if not match:
        raise ClevelandNowcastDataError(
            "Cleveland target quarter was not canonical"
        )
    year = int(match.group(1))
    quarter = int(match.group(2))
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    end_day = 31 if end_month in (3, 12) else 30
    return {
        "end": "%04d-%02d-%02d" % (year, end_month, end_day),
        "ordinal": year * 4 + quarter - 1,
        "start": "%04d-%02d-01" % (year, start_month),
    }


def _validate_categories(categories):
    if (
        not isinstance(categories, list) or
        len(categories) != 1 or
        not isinstance(categories[0], dict) or
        frozenset(categories[0]) != CATEGORY_CONTAINER_FIELDS
    ):
        raise ClevelandNowcastDataError(
            "Cleveland category container changed"
        )
    rows = categories[0]["category"]
    if not isinstance(rows, list) or not rows:
        raise ClevelandNowcastDataError(
            "Cleveland category list was empty"
        )
    for row in rows:
        if (
            not isinstance(row, dict) or
            frozenset(row) not in (CATEGORY_FIELDS, CATEGORY_LINE_FIELDS)
        ):
            raise ClevelandNowcastDataError(
                "Cleveland category row schema changed"
            )
        _exact_text(row.get("label"), "Cleveland category label")
        if frozenset(row) == CATEGORY_LINE_FIELDS:
            if (
                row["vline"] != "true" or
                not _HEX_COLOR_RE.match(row["color"]) or
                row["labelposition"] != "0" or
                row["lineposition"] != "0"
            ):
                raise ClevelandNowcastDataError(
                    "Cleveland category marker contract changed"
                )


def _latest_value(dataset, expected_length):
    if (
        not isinstance(dataset, dict) or
        frozenset(dataset) != DATASET_FIELDS
    ):
        raise ClevelandNowcastDataError(
            "Cleveland dataset schema changed"
        )
    name = _exact_text(
        dataset.get("seriesname"),
        "Cleveland dataset seriesname",
    )
    if name not in ALL_NAMES:
        raise ClevelandNowcastDataError(
            "Cleveland dataset series identity changed"
        )
    color = _exact_text(dataset.get("color"), "Cleveland dataset color")
    if not _HEX_COLOR_RE.match(color):
        raise ClevelandNowcastDataError(
            "Cleveland dataset color changed type"
        )
    rows = dataset.get("data")
    if (
        not isinstance(rows, list) or not rows or
        len(rows) != expected_length
    ):
        raise ClevelandNowcastDataError(
            "Cleveland dataset path length changed within a quarter"
        )
    nonempty = []
    for index, row in enumerate(rows):
        if (
            not isinstance(row, dict) or
            frozenset(row) not in (DATA_FIELDS, DATA_ANCHOR_FIELDS)
        ):
            raise ClevelandNowcastDataError(
                "Cleveland data-point schema changed"
            )
        value = row.get("value")
        tooltext = row.get("tooltext")
        if not isinstance(value, str) or not isinstance(tooltext, str):
            raise ClevelandNowcastDataError(
                "Cleveland data-point fields were not text"
            )
        if value:
            nonempty.append((
                index,
                _decimal(value, "Cleveland dataset value"),
                tooltext,
            ))
    if not nonempty:
        raise ClevelandNowcastDataError(
            "Cleveland dataset contained no published value"
        )
    index, value, tooltext = nonempty[-1]
    return {
        "latest_path_index": index,
        "latest_tooltext": tooltext,
        "name": name,
        "nonempty_count": len(nonempty),
        "value": value,
    }


def parse_cleveland_nowcast_json(series_metadata, body):
    """Project latest values per quarter/series from reviewed chart JSON."""
    if series_metadata != {}:
        raise ClevelandNowcastDataError(
            "Cleveland series metadata must be the exact empty object"
        )
    panels = _load_json(body)
    if not isinstance(panels, list) or not panels:
        raise ClevelandNowcastDataError(
            "Cleveland response was not a nonempty panel list"
        )

    observations = []
    seen_quarters = set()
    previous_quarter_ordinal = None
    incomplete_actuals_seen = False
    common_as_of = None
    for panel in panels:
        if not isinstance(panel, dict) or frozenset(panel) != TOP_FIELDS:
            raise ClevelandNowcastDataError(
                "Cleveland panel schema changed"
            )
        chart = panel["chart"]
        if not isinstance(chart, dict) or frozenset(chart) != CHART_FIELDS:
            raise ClevelandNowcastDataError(
                "Cleveland chart metadata schema changed"
            )
        if (
            chart["caption"] != "Inflation Nowcasting" or
            chart["yaxisname"] !=
            "Quarterly Annualized Percent Change"
        ):
            raise ClevelandNowcastDataError(
                "Cleveland chart identity changed"
            )
        quarter = _exact_text(
            chart["subcaption"],
            "Cleveland chart subcaption",
        )
        quarter_value = _quarter(quarter)
        if quarter in seen_quarters:
            raise ClevelandNowcastDataError(
                "Cleveland target quarter was duplicated"
            )
        seen_quarters.add(quarter)
        if (
            previous_quarter_ordinal is not None and
            quarter_value["ordinal"] != previous_quarter_ordinal + 1
        ):
            raise ClevelandNowcastDataError(
                "Cleveland target-quarter sequence was not contiguous"
            )
        previous_quarter_ordinal = quarter_value["ordinal"]

        as_of = _exact_text(
            chart["_comment"],
            "Cleveland chart _comment",
        )
        if not _AS_OF_RE.match(as_of):
            raise ClevelandNowcastDataError(
                "Cleveland chart _comment was not a reviewed timestamp label"
            )
        try:
            datetime.strptime(as_of, "%Y-%m-%d %H:%M")
        except ValueError:
            raise ClevelandNowcastDataError(
                "Cleveland chart _comment was invalid"
            )
        if common_as_of is None:
            common_as_of = as_of
        elif as_of != common_as_of:
            raise ClevelandNowcastDataError(
                "Cleveland panels mixed publisher as-of labels"
            )
        _validate_categories(panel["categories"])

        datasets = panel["dataset"]
        if not isinstance(datasets, list) or not datasets:
            raise ClevelandNowcastDataError(
                "Cleveland panel contained no datasets"
            )
        first_data = datasets[0].get("data") if isinstance(datasets[0], dict) else None
        if not isinstance(first_data, list) or not first_data:
            raise ClevelandNowcastDataError(
                "Cleveland first dataset path was invalid"
            )
        projected = [
            _latest_value(dataset, len(first_data))
            for dataset in datasets
        ]
        names = [item["name"] for item in projected]
        if len(names) != len(set(names)):
            raise ClevelandNowcastDataError(
                "Cleveland panel duplicated a series"
            )
        if not set(NOWCAST_NAMES).issubset(names):
            raise ClevelandNowcastDataError(
                "Cleveland panel omitted a required nowcast series"
            )
        actual_names = set(names).intersection(ACTUAL_NAMES)
        if actual_names != set(ACTUAL_NAMES):
            incomplete_actuals_seen = True
        elif incomplete_actuals_seen:
            raise ClevelandNowcastDataError(
                "Cleveland complete actual panel followed an incomplete one"
            )

        for item in projected:
            token, kind, status = NAME_CONTRACT[item["name"]]
            observations.append({
                "forecast_target_end": quarter_value["end"],
                "forecast_target_start": quarter_value["start"],
                "label": item["name"],
                "publisher_as_of_label": as_of,
                "publisher_last_path_index": item["latest_path_index"],
                "publisher_last_tooltext": item["latest_tooltext"],
                "publisher_nonempty_observation_count": (
                    item["nonempty_count"]
                ),
                "publisher_target_quarter": quarter,
                "reference_period": quarter_value["start"],
                "series_id": (
                    "CLEVELAND.INFLATION_NOWCAST.%s.%s" %
                    (token, kind)
                ),
                "unit": "annualized percent",
                "value": item["value"],
                "value_status": status,
            })
    return observations
