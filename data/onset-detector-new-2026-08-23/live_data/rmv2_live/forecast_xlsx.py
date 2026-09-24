"""Strict normalization for Philadelphia Fed SPF / Anxious Index xlsx (B-LAND-8).

FORECAST class. The Survey of Professional Forecasters workbooks are written by SAS
9.04.01M7, which emits a malformed ``docProps/core.xml`` modified-date (a
non-zero-padded W3CDTF hour, ``...T 2:31:35-04:00``); openpyxl's date parser raises
``TypeError`` at ``load_workbook`` BEFORE the grid is reachable (CH-R49
``openpyxl_core_defect``). This module repairs ``docProps/core.xml`` **in memory**
(rewriting the zip into a ``BytesIO`` handed to openpyxl) and NEVER writes a fixed
copy to disk — the offline-current binder stores the **ORIGINAL** cache bytes, so the
bound bytes still match the cache-manifest sha.

Shapes (dispatched on ``source["series"]["forecast_shape"]``):

* ``anxious_index`` — the published Anxious Index: the mean probability of a negative
  quarter-over-quarter real GDP growth, one quarter ahead. The ``Data`` sheet is keyed
  by the TARGET quarter (Obs Year / Obs Quarter). The ``RECESS`` column is a ``99999``
  chart-shading flag, NOT data, and is dropped. One series (own id).
* ``spf_aggregate`` — an SPF mean/median level/growth workbook. Header is
  ``YEAR, QUARTER, <VARCODE><horizon>, ...``; each value column becomes its OWN series
  ``SPF_<VARCODE>_<MEAN|MEDIAN>`` keyed by the SURVEY quarter. ``#N/A`` cells emit
  ``value=None`` / ``value_status='unavailable'`` (FRED current-lane convention).

Firewall (CLAUDE.md, batch B-LAND-8): forecasts of MEASUREMENTS are eligible
``substituted_diagnostic`` inputs, ALWAYS labeled; the RECESS / Anxious probabilities
are GDP-decline probabilities, NEVER NBER recession-label products (comparator-only).
This module lands data — it adopts nothing, merges nothing, and re-bases nothing.
"""

from __future__ import absolute_import

import io
import re
import zipfile

import openpyxl


class ForecastXlsxDataError(ValueError):
    """Raised when the SPF/Anxious xlsx bytes fail the reviewed contract."""


_SERIES_ID_RE = re.compile(r"^SPF_[A-Za-z0-9_]+$")
_NYFED_ID_BASE_RE = re.compile(r"^NYFED_[A-Z0-9_]+$")
_QUARTER_LABEL_RE = re.compile(r"^\d{4}Q[1-4]$")
_CANONICAL_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_VARCODE_RE = re.compile(r"^[A-Z][A-Z0-9]*$")
# SPF individual-panel horizon suffixes: numeric 1-6 = quarterly horizons,
# A-D = annual-average horizons. A column header is exactly <VARCODE><SUFFIX>.
_SPF_HORIZON_RE = re.compile(r"^(?:[1-6]|[A-D])$")

# The three "Forecasts By Horizon" value columns, keyed by the lowercased prefix
# of the (newline-bearing) header cell -> (id suffix, horizon label).
_NYFED_HORIZONS = (
    ("backcast", "BACKCAST", "backcast"),
    ("nowcast", "NOWCAST", "nowcast"),
    ("forecast", "FORECAST", "forecast"),
)
# SAS wrote a non-zero-padded W3CDTF hour: '...T 2:31:35' or '...T2:31:35'. Pad it.
_CORE_XML_HOUR_RE = re.compile(rb"T\s?(\d):")

_MISSING_TOKENS = frozenset(("", "#N/A", "#n/a", "NA", "N/A"))
_RECESS_SHADING_FLAG = 99999


def repair_core_xml_bytes(body):
    """Return a ``BytesIO`` of ``body`` with ``docProps/core.xml``'s W3CDTF hour
    zero-padded, so openpyxl can load it. Touches ONLY ``core.xml``; every other
    member is copied byte-for-byte. Used for PARSING only — the caller binds the
    original ``body``, never this rewritten zip."""
    if not isinstance(body, (bytes, bytearray)) or not body:
        raise ForecastXlsxDataError("forecast xlsx body must be nonempty bytes")
    try:
        zin = zipfile.ZipFile(io.BytesIO(bytes(body)))
    except zipfile.BadZipFile as exc:
        raise ForecastXlsxDataError("forecast xlsx was not a valid zip: %s" % exc)
    members = {name: zin.read(name) for name in zin.namelist()}
    core = members.get("docProps/core.xml")
    if core is not None:
        members["docProps/core.xml"] = _CORE_XML_HOUR_RE.sub(rb"T0\1:", core)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in members.items():
            zout.writestr(name, data)
    out.seek(0)
    return out


def _load_sheet_rows(body, sheet_name):
    repaired = repair_core_xml_bytes(body)
    try:
        workbook = openpyxl.load_workbook(
            repaired, read_only=True, data_only=True,
        )
    except Exception as exc:  # openpyxl raises a spread of types on bad input
        raise ForecastXlsxDataError(
            "openpyxl could not load forecast xlsx: %s" % exc
        )
    try:
        if sheet_name not in workbook.sheetnames:
            raise ForecastXlsxDataError(
                "forecast xlsx has no sheet %r (sheets: %r)"
                % (sheet_name, workbook.sheetnames)
            )
        worksheet = workbook[sheet_name]
        rows = [row for row in worksheet.iter_rows(values_only=True)]
    finally:
        workbook.close()
    return rows


def _quarter_period(year, quarter):
    """Map an SPF (year, quarter) to the canonical first-of-quarter ISO date."""
    try:
        year_i = int(round(float(year)))
        quarter_i = int(round(float(quarter)))
    except (TypeError, ValueError):
        raise ForecastXlsxDataError(
            "forecast xlsx had a non-numeric year/quarter: %r/%r" % (year, quarter)
        )
    if quarter_i < 1 or quarter_i > 4:
        raise ForecastXlsxDataError(
            "forecast xlsx quarter out of range 1-4: %r" % (quarter,)
        )
    if year_i < 1900 or year_i > 2100:
        raise ForecastXlsxDataError(
            "forecast xlsx year out of range: %r" % (year,)
        )
    return "%04d-%02d-01" % (year_i, quarter_i * 3 - 2)


def _canonical_value(cell):
    """Return (value, status): a shortest round-tripping decimal string for a real
    number, or (None, 'unavailable') for a missing cell. NEVER rounds; rejects
    scientific-notation output defensively (SPF magnitudes never reach it)."""
    if cell is None:
        return None, "unavailable"
    if isinstance(cell, str):
        token = cell.strip()
        if token in _MISSING_TOKENS:
            return None, "unavailable"
        try:
            number = float(token)
        except ValueError:
            raise ForecastXlsxDataError(
                "forecast xlsx cell was not numeric: %r" % (cell,)
            )
    elif isinstance(cell, bool):
        raise ForecastXlsxDataError("forecast xlsx cell was a bool: %r" % (cell,))
    elif isinstance(cell, (int, float)):
        number = float(cell)
    else:
        raise ForecastXlsxDataError(
            "forecast xlsx cell had an unexpected type: %r" % (cell,)
        )
    if number != number or number in (float("inf"), float("-inf")):
        raise ForecastXlsxDataError("forecast xlsx cell was not finite: %r" % (cell,))
    rendered = repr(number)
    if not _CANONICAL_DECIMAL_RE.match(rendered):
        raise ForecastXlsxDataError(
            "forecast xlsx cell did not render as a plain decimal: %r -> %r"
            % (cell, rendered)
        )
    return rendered, "actual"


def _find_header_row(rows, required_labels):
    """Return (index, header) for the first row that contains every required label
    (case-insensitive, whitespace-trimmed)."""
    wanted = [label.strip().lower() for label in required_labels]
    for index, row in enumerate(rows):
        cells = [
            str(cell).strip().lower() for cell in row if cell is not None
        ]
        if all(label in cells for label in wanted):
            return index, list(row)
    raise ForecastXlsxDataError(
        "forecast xlsx never found a header row with %r" % (required_labels,)
    )


def _validate_common(series_config):
    if not isinstance(series_config, dict):
        raise ForecastXlsxDataError("forecast series config must be an object")
    shape = series_config.get("forecast_shape")
    unit = series_config.get("unit")
    label = series_config.get("label")
    if not isinstance(unit, str) or not unit:
        raise ForecastXlsxDataError("forecast series unit was invalid")
    if not isinstance(label, str) or not label:
        raise ForecastXlsxDataError("forecast series label was invalid")
    return shape, unit, label


def _parse_anxious_index(series_config, body):
    shape, unit, label = _validate_common(series_config)
    series_id = series_config.get("series_id")
    if not isinstance(series_id, str) or not _SERIES_ID_RE.match(series_id):
        raise ForecastXlsxDataError(
            "anxious series_id must match SPF_* : %r" % (series_id,)
        )
    sheet = series_config.get("sheet", "Data")
    rows = _load_sheet_rows(body, sheet)
    header_index, header = _find_header_row(
        rows, ("Obs Year", "Obs Quarter", "Anxious Index"),
    )
    lower = [str(c).strip().lower() if c is not None else "" for c in header]
    y_i = lower.index("obs year")
    q_i = lower.index("obs quarter")
    v_i = lower.index("anxious index")

    observations = []
    seen = set()
    for row in rows[header_index + 1:]:
        if y_i >= len(row) or row[y_i] is None:
            continue
        cell = row[v_i] if v_i < len(row) else None
        # a survey quarter with no published Anxious Index yet (future target
        # quarter) is simply absent, not a missing-observation record.
        if cell is None:
            continue
        # the RECESS column is a 99999 chart-shading flag; the Anxious Index column
        # never legitimately carries that sentinel, but guard against it anyway.
        if cell == _RECESS_SHADING_FLAG:
            raise ForecastXlsxDataError(
                "anxious index cell carried the 99999 shading flag"
            )
        period = _quarter_period(row[y_i], row[q_i])
        value, status = _canonical_value(cell)
        key = (series_id, period)
        if key in seen:
            raise ForecastXlsxDataError(
                "anxious index produced a duplicate period: %r" % (key,)
            )
        seen.add(key)
        observations.append({
            "series_id": series_id,
            "observation_period": period,
            "value": value,
            "value_status": status,
            "unit": unit,
            "label": label,
            "spf_target_code": "ANXIOUS_INDEX",
        })
    if not observations:
        raise ForecastXlsxDataError("anxious index produced no observations")
    observations.sort(key=lambda o: o["observation_period"])
    return observations


def _parse_spf_aggregate(series_config, body):
    shape, unit, label = _validate_common(series_config)
    statistic = series_config.get("statistic")
    if statistic not in ("MEAN", "MEDIAN"):
        raise ForecastXlsxDataError(
            "spf aggregate statistic must be MEAN|MEDIAN: %r" % (statistic,)
        )
    sheet = series_config.get("sheet")
    if not isinstance(sheet, str) or not sheet:
        raise ForecastXlsxDataError("spf aggregate sheet was invalid")
    id_prefix = series_config.get("id_prefix", "SPF_")
    rows = _load_sheet_rows(body, sheet)
    header_index, header = _find_header_row(rows, ("YEAR", "QUARTER"))
    lower = [str(c).strip().lower() if c is not None else "" for c in header]
    y_i = lower.index("year")
    q_i = lower.index("quarter")

    value_columns = []
    for col_index, name in enumerate(header):
        if col_index in (y_i, q_i) or name is None:
            continue
        varcode = str(name).strip().upper()
        if not _VARCODE_RE.match(varcode):
            raise ForecastXlsxDataError(
                "spf aggregate value column was not a varcode: %r" % (name,)
            )
        series_id = "%s%s_%s" % (id_prefix, varcode, statistic)
        if not _SERIES_ID_RE.match(series_id):
            raise ForecastXlsxDataError(
                "spf aggregate series_id malformed: %r" % (series_id,)
            )
        value_columns.append((col_index, varcode, series_id))
    if not value_columns:
        raise ForecastXlsxDataError("spf aggregate had no value columns")

    observations = []
    seen = set()
    for row in rows[header_index + 1:]:
        if y_i >= len(row) or row[y_i] is None:
            continue
        period = _quarter_period(row[y_i], row[q_i])
        for col_index, varcode, series_id in value_columns:
            cell = row[col_index] if col_index < len(row) else None
            value, status = _canonical_value(cell)
            key = (series_id, period)
            if key in seen:
                raise ForecastXlsxDataError(
                    "spf aggregate produced a duplicate (series, period): %r" % (key,)
                )
            seen.add(key)
            observations.append({
                "series_id": series_id,
                "observation_period": period,
                "value": value,
                "value_status": status,
                "unit": unit,
                "label": "%s [%s]" % (label, varcode),
                "spf_target_code": varcode,
            })
    if not observations:
        raise ForecastXlsxDataError("spf aggregate produced no observations")
    if not any(o["value_status"] == "actual" for o in observations):
        raise ForecastXlsxDataError("spf aggregate produced no available observations")
    observations.sort(key=lambda o: (o["series_id"], o["observation_period"]))
    return observations


def _panel_int(cell):
    """Return a panel ID / INDUSTRY code as an int, or None for a #N/A / missing
    cell. Codes are anonymous integers (CH-R49); never a float, never a name."""
    if cell is None:
        return None
    if isinstance(cell, bool):
        raise ForecastXlsxDataError("spf individual code was a bool: %r" % (cell,))
    if isinstance(cell, str):
        token = cell.strip()
        if token in _MISSING_TOKENS:
            return None
        try:
            number = float(token)
        except ValueError:
            raise ForecastXlsxDataError(
                "spf individual code was not numeric: %r" % (cell,)
            )
    elif isinstance(cell, (int, float)):
        number = float(cell)
    else:
        raise ForecastXlsxDataError(
            "spf individual code had an unexpected type: %r" % (cell,)
        )
    if number != number or number in (float("inf"), float("-inf")):
        raise ForecastXlsxDataError("spf individual code was not finite: %r" % (cell,))
    if number != int(number):
        raise ForecastXlsxDataError("spf individual code was not integral: %r" % (cell,))
    return int(number)


def _parse_spf_individual(series_config, body):
    """Parse one SPF individual-forecaster panel (B-LAND-8-R2).

    The panel is a forecaster x survey-quarter x horizon grid: columns YEAR,
    QUARTER, ID (anonymous forecaster integer — CH-R49 verdict ANONYMOUS_ID_ONLY),
    INDUSTRY (code 1-3, or #N/A before industry tracking), then one
    ``<VARCODE><HORIZON>`` column per horizon (1-6 quarterly, A-D annual-average).
    Each horizon column lands as its own ``SPF_<VARCODE>_IND_<HORIZON>`` series;
    every emitted observation additionally carries the anonymous forecaster_id, the
    industry code, and the horizon as panel dimensions. The grid is >99% empty, so
    ONLY actual (non-#N/A) cells are emitted — never a dense unavailable row per
    cell. Firewall: FORECAST class, never aliased to a construction series."""
    shape, unit, label = _validate_common(series_config)
    varcode = series_config.get("spf_target_code")
    if not isinstance(varcode, str) or not _VARCODE_RE.match(varcode):
        raise ForecastXlsxDataError(
            "spf individual target code invalid: %r" % (varcode,)
        )
    sheet = series_config.get("sheet")
    if not isinstance(sheet, str) or not sheet:
        raise ForecastXlsxDataError("spf individual sheet was invalid")
    id_prefix = series_config.get("id_prefix", "SPF_")
    rows = _load_sheet_rows(body, sheet)
    header_index, header = _find_header_row(
        rows, ("YEAR", "QUARTER", "ID", "INDUSTRY")
    )
    lower = [str(c).strip().lower() if c is not None else "" for c in header]
    y_i = lower.index("year")
    q_i = lower.index("quarter")
    id_i = lower.index("id")
    ind_i = lower.index("industry")

    fixed = {y_i, q_i, id_i, ind_i}
    horizon_columns = []  # (col_index, horizon, series_id)
    for col_index, name in enumerate(header):
        if col_index in fixed or name is None:
            continue
        column = str(name).strip().upper()
        if not column.startswith(varcode):
            raise ForecastXlsxDataError(
                "spf individual column %r is not a %r horizon column"
                % (name, varcode)
            )
        horizon = column[len(varcode):]
        if not _SPF_HORIZON_RE.match(horizon):
            raise ForecastXlsxDataError(
                "spf individual horizon suffix invalid: %r" % (column,)
            )
        series_id = "%s%s_IND_%s" % (id_prefix, varcode, horizon)
        if not _SERIES_ID_RE.match(series_id):
            raise ForecastXlsxDataError(
                "spf individual series_id malformed: %r" % (series_id,)
            )
        horizon_columns.append((col_index, horizon, series_id))
    if not horizon_columns:
        raise ForecastXlsxDataError("spf individual had no horizon columns")

    observations = []
    seen = set()
    for row in rows[header_index + 1:]:
        if y_i >= len(row) or row[y_i] is None:
            continue
        period = _quarter_period(row[y_i], row[q_i])
        forecaster_id = _panel_int(row[id_i] if id_i < len(row) else None)
        if forecaster_id is None:
            raise ForecastXlsxDataError(
                "spf individual row missing forecaster id at period %r" % (period,)
            )
        industry = _panel_int(row[ind_i] if ind_i < len(row) else None)
        for col_index, horizon, series_id in horizon_columns:
            cell = row[col_index] if col_index < len(row) else None
            value, status = _canonical_value(cell)
            if status != "actual":
                continue  # sparse: the empty grid cells are not emitted
            key = (series_id, period, forecaster_id, industry)
            if key in seen:
                raise ForecastXlsxDataError(
                    "spf individual produced a duplicate panel key: %r" % (key,)
                )
            seen.add(key)
            observations.append({
                "series_id": series_id,
                "observation_period": period,
                "value": value,
                "value_status": status,
                "unit": unit,
                "label": "%s [%s IND h=%s fid=%s]" % (
                    label, varcode, horizon, forecaster_id),
                "spf_target_code": varcode,
                "spf_forecaster_id": forecaster_id,
                "spf_industry": industry,
                "spf_horizon": horizon,
            })
    if not observations:
        raise ForecastXlsxDataError("spf individual produced no observations")
    observations.sort(key=lambda o: (
        o["series_id"], o["observation_period"], o["spf_forecaster_id"],
        -1 if o["spf_industry"] is None else o["spf_industry"],
    ))
    return observations


def _iso_forecast_date(cell):
    """Return an ISO ``YYYY-MM-DD`` string for a forecast-date cell that is either
    an openpyxl ``datetime``/``date`` or an already-ISO string. Rejects anything
    else so a stray header/blank never becomes a fake observation date."""
    if hasattr(cell, "isoformat") and hasattr(cell, "year"):
        # datetime or date; the NY Fed forecast dates carry no meaningful time.
        return "%04d-%02d-%02d" % (cell.year, cell.month, cell.day)
    if isinstance(cell, str):
        token = cell.strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", token):
            return token
    raise ForecastXlsxDataError(
        "nyfed nowcast forecast-date was not a date: %r" % (cell,)
    )


def _parse_nyfed_nowcast(series_config, body):
    """New York Fed Staff Nowcast "Forecasts By Horizon" tidy sheet.

    One weekly row carries the backcast (previous quarter), nowcast (current
    quarter), and forecast (next quarter) of real GDP growth. Emits up to three
    flat series ``<id_base>_{BACKCAST,NOWCAST,FORECAST}`` keyed by the ISO
    forecast date, each row's ``Reference quarter`` preserved as the additive
    ``nyfed_reference_quarter`` dimension. Empty horizon cells are SKIPPED (a
    week tracking no previous/next quarter is absent, not a missing record)."""
    shape, unit, label = _validate_common(series_config)
    id_base = series_config.get("id_base")
    if not isinstance(id_base, str) or not _NYFED_ID_BASE_RE.match(id_base):
        raise ForecastXlsxDataError(
            "nyfed nowcast id_base must match NYFED_* : %r" % (id_base,)
        )
    sheet = series_config.get("sheet")
    if not isinstance(sheet, str) or not sheet:
        raise ForecastXlsxDataError("nyfed nowcast sheet was invalid")
    rows = _load_sheet_rows(body, sheet)
    header_index, header = _find_header_row(
        rows, ("Forecast date", "Reference quarter"),
    )
    lower = [
        " ".join(str(c).split()).strip().lower() if c is not None else ""
        for c in header
    ]
    d_i = lower.index("forecast date")
    q_i = lower.index("reference quarter")

    horizon_columns = []
    for prefix, suffix, horizon in _NYFED_HORIZONS:
        matches = [
            i for i, name in enumerate(lower)
            if i not in (d_i, q_i) and name.startswith(prefix)
        ]
        if len(matches) != 1:
            raise ForecastXlsxDataError(
                "nyfed nowcast expected exactly one %r column, found %d"
                % (prefix, len(matches))
            )
        horizon_columns.append((matches[0], "%s_%s" % (id_base, suffix), horizon))

    observations = []
    seen = set()
    for row in rows[header_index + 1:]:
        if d_i >= len(row) or row[d_i] is None:
            continue
        if q_i >= len(row) or row[q_i] is None:
            continue
        ref_quarter = " ".join(str(row[q_i]).split()).strip().upper()
        if not _QUARTER_LABEL_RE.match(ref_quarter):
            raise ForecastXlsxDataError(
                "nyfed nowcast reference quarter malformed: %r" % (row[q_i],)
            )
        period = _iso_forecast_date(row[d_i])
        for col_index, series_id, horizon in horizon_columns:
            cell = row[col_index] if col_index < len(row) else None
            if cell is None:
                continue
            value, status = _canonical_value(cell)
            key = (series_id, period)
            if key in seen:
                raise ForecastXlsxDataError(
                    "nyfed nowcast produced a duplicate (series, period): %r"
                    % (key,)
                )
            seen.add(key)
            observations.append({
                "series_id": series_id,
                "observation_period": period,
                "value": value,
                "value_status": status,
                "unit": unit,
                "label": "%s [%s]" % (label, horizon),
                "nyfed_reference_quarter": ref_quarter,
                "nyfed_horizon": horizon,
            })
    if not observations:
        raise ForecastXlsxDataError("nyfed nowcast produced no observations")
    observations.sort(key=lambda o: (o["series_id"], o["observation_period"]))
    return observations


def parse_forecast_xlsx_bytes(series_config, body):
    """Return deterministic observation dicts for one SPF/Anxious xlsx source.

    Dispatches on ``series_config['forecast_shape']``. Each observation carries:
    series_id, observation_period (ISO first-of-quarter), value (canonical decimal
    string or None), value_status ('actual'|'unavailable'), unit, label, and the
    additive ``spf_target_code`` dimension. Missing (#N/A) aggregate cells ARE
    emitted (value=None); absent future Anxious quarters are skipped.
    """
    if not isinstance(series_config, dict):
        raise ForecastXlsxDataError("forecast series config must be an object")
    shape = series_config.get("forecast_shape")
    if shape == "anxious_index":
        return _parse_anxious_index(series_config, body)
    if shape == "spf_aggregate":
        return _parse_spf_aggregate(series_config, body)
    if shape == "spf_individual":
        return _parse_spf_individual(series_config, body)
    if shape == "nyfed_nowcast":
        return _parse_nyfed_nowcast(series_config, body)
    raise ForecastXlsxDataError("unknown forecast_shape: %r" % (shape,))
