"""B-LAND-12 — ATSIX inflation-expectations term-structure xlsx -> flat records.

ATSIX (Aruoba, *Term Structure of Inflation Expectations*, Philadelphia Fed) is a
MODEL OUTPUT, not an RTDSM realized-vintage matrix.  Measured layout
(research/_bland12_sheets.json, recorded before any parse-at-scale):

    sheet InfExp:  _date_, infexp3 … infexp120   (expected inflation at HORIZON n months)
    sheet Real:    _date_, real3   … real120     (ex-ante real rate term structure)
    sheet Factors: _date_, level, slope, curvature, lambda   (Nelson-Siegel factors)
    rows 2+     : <YYYY-MM-01 datetime>, value, value, ...

Each cell is ONE value at (reference date, horizon/factor).  There is NO vintage-date
column axis, so this is fundamentally a different shape from ``rtdsm_xlsx`` (whose columns
ARE the as-of vintages).  CH-R39 already classed atsix "forecast-class, not real-time
realized data"; every peer Fed model output (GDPNow, Cleveland/NY nowcasts, SPF, Livingston)
is catalogued ``forecast_comparator``.  This module therefore only PARSES the bytes into
``(sheet, series, date, value)`` records; the identity/information-set-mode/firewall
decision is owner territory and lives outside the parse logic (B-LAND-12 owner question
20260806T162209Z), exactly as ``rtdsm_xlsx`` keeps the naming ruling out of ``parse_matrix``.

openpyxl refuses the Phil-Fed workbooks' date-only ``<modified>`` core property, so
``load_named_worksheet`` strips ``docProps/core.xml`` before loading (sheet bytes untouched).
"""
from __future__ import annotations

import datetime
import hashlib
import io
import re
import zipfile

import openpyxl

PARSER_VERSION = "rmv2-live/atsix_termstructure.v1"

# The first header cell of every ATSIX sheet is the literal date marker.
_DATE_MARKER = "_date_"
# A landed value is a canonical decimal (optionally signed, optional exponent) — anything
# else that is not blank is a shape surprise and is refused, never coerced to a number.
_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")
_ABSENCE = frozenset(("", ".", "#N/A", "NA", "N/A", "None"))


class AtsixShapeError(ValueError):
    """A workbook, column, cell or value did not match the measured ATSIX shape.

    Raised rather than skipping, so a shape surprise can never silently understate
    what was parsed."""


def _canon_date(cell) -> str:
    """ATSIX ``_date_`` cell -> canonical ``YYYY-MM-DD`` (always first-of-month).

    The sampled files store true datetimes at day 01; a string ``YYYY-MM-DD`` /
    ``YYYY-MM-DD HH:MM:SS`` form is accepted for robustness against read_only casts."""
    if isinstance(cell, (datetime.datetime, datetime.date)):
        return "%04d-%02d-01" % (cell.year, cell.month)
    text = str(cell).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if not m:
        raise AtsixShapeError("unrecognised ATSIX date cell: %r" % (cell,))
    year, month = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        raise AtsixShapeError("date month out of range: %r" % (cell,))
    return "%04d-%02d-01" % (year, month)


def load_named_worksheet(body: bytes, sheet_name: str):
    """Named worksheet of an ATSIX workbook (docProps/core.xml stripped)."""
    src = zipfile.ZipFile(io.BytesIO(body))
    buf = io.BytesIO()
    dst = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    for item in src.infolist():
        if item.filename == "docProps/core.xml":
            continue
        dst.writestr(item, src.read(item.filename))
    dst.close()
    src.close()
    buf.seek(0)
    wb = openpyxl.load_workbook(buf, read_only=True, data_only=True)
    if sheet_name not in wb.sheetnames:
        wb.close()
        raise AtsixShapeError("sheet %r not in workbook %r" % (sheet_name, wb.sheetnames))
    return wb[sheet_name], wb


def parse_sheet(body: bytes, sheet_name: str):
    """Parse one ATSIX sheet into flat term-structure records.

    Returns ``(records, sha256, meta)`` where each record is
    ``{"sheet", "series", "date", "value"}`` for every non-blank cell, sha256 is over
    the ORIGINAL workbook bytes (provenance), and meta carries the counted shape.
    Blank cells are absence (skipped, not zero, not a hole); any other malformed cell,
    header or value raises ``AtsixShapeError`` rather than being coerced/skipped."""
    sha = hashlib.sha256(body).hexdigest()
    ws, wb = load_named_worksheet(body, sheet_name)
    try:
        rows = ws.iter_rows(values_only=True)
        try:
            header = next(rows)
        except StopIteration:
            raise AtsixShapeError("sheet %r is empty" % sheet_name)
        header = [None if c is None else str(c).strip() for c in header]
        if not header or header[0] != _DATE_MARKER:
            raise AtsixShapeError(
                "sheet %r header does not start with %r: %r"
                % (sheet_name, _DATE_MARKER, header[:2])
            )
        series_cols = []  # (col_index, series_name)
        for idx, name in enumerate(header[1:], start=1):
            if name is None or name == "":
                continue
            series_cols.append((idx, name))
        if not series_cols:
            raise AtsixShapeError("sheet %r has no term-structure columns" % sheet_name)

        records = []
        seen = set()
        obs_rows = 0
        for raw in rows:
            if raw is None or raw[0] is None:
                continue
            date = _canon_date(raw[0])
            obs_rows += 1
            for idx, name in series_cols:
                if idx >= len(raw):
                    continue
                cell = raw[idx]
                if cell is None:
                    continue
                text = str(cell).strip()
                if text in _ABSENCE:
                    continue
                if not _DECIMAL_RE.match(text):
                    raise AtsixShapeError(
                        "non-decimal value %r at %s series %r" % (text, date, name)
                    )
                key = (date, name)
                if key in seen:
                    raise AtsixShapeError("duplicate cell %s @ %s" % (name, date))
                seen.add(key)
                records.append(
                    {"sheet": sheet_name, "series": name, "date": date, "value": text}
                )
        meta = {
            "sheet": sheet_name,
            "horizons": len(series_cols),
            "obs_rows": obs_rows,
            "records": len(records),
            "parser_version": PARSER_VERSION,
        }
        if not records:
            raise AtsixShapeError("no records parsed from sheet %r" % sheet_name)
        return records, sha, meta
    finally:
        wb.close()
