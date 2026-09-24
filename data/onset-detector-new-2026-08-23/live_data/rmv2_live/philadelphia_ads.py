"""Strict normalization for the Philadelphia Fed ADS Business Conditions Index
current-vintage workbook (B-UNBLOCK-3 item 1).

This module performs NO network I/O. It parses the on-disk (prefetch-cached /
raw-captured) ``ADS_Index_Most_Current_Vintage.xlsx`` bytes with the stdlib
zip/XML reader — no third-party spreadsheet dependency, so the parse is
deterministic and auditable.

The workbook's single ``Sheet1`` carries three columns:
  A ``Date``       daily business-day date rendered ``YYYY:MM:DD``
  B ``ADS_Index``  the Aruoba-Diebold-Scotti daily business-conditions index
  C ``RECBARS``    an NBER recession-shading flag (0/1)

Only column B (``ADS_Index``) is normalized. Column C (``RECBARS``) is an NBER
recession-LABEL indicator — an EXTERNAL COMPARATOR / target, never a clean
construction input (CLAUDE.md) — and is DROPPED, not landed as a series.

FIREWALL (B-UNBLOCK-3 STOP + §10 + §22.4): the ADS index is a nowcast/COMPARATOR
of real business conditions. It is landed as a single evidence lane under its own
source id and MUST NEVER be admitted to a channel, member set, weight, or
severity dimension. Admitting it would be outcome-guided.

Values are copied verbatim as the shortest decimal string that round-trips the
stored IEEE-754 double (Excel stores some cells in scientific notation, e.g.
``4.6676039626174906E-2``); no rounding or re-derivation is applied.
"""

from __future__ import absolute_import

import re
import zipfile
from datetime import datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET


_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS = {"m": _MAIN_NS}

_ADS_DATE_RE = re.compile(r"^(\d{4}):(\d{2}):(\d{2})$")
_FINITE_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

_HEADER_DATE = "Date"
_HEADER_VALUE = "ADS_Index"
_HEADER_RECBARS = "RECBARS"


class PhiladelphiaAdsDataError(ValueError):
    """Raised when the ADS workbook bytes fail the reviewed contract."""


def _q(tag):
    return "{%s}%s" % (_MAIN_NS, tag)


class _BytesReader:
    """Minimal seekable file object so ZipFile can read in-memory bytes."""

    def __init__(self, data):
        self._data = data
        self._pos = 0

    def seek(self, offset, whence=0):
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = len(self._data) + offset
        else:
            raise ValueError("bad whence")
        return self._pos

    def tell(self):
        return self._pos

    def read(self, size=-1):
        if size is None or size < 0:
            chunk = self._data[self._pos:]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos:self._pos + size]
        self._pos += len(chunk)
        return chunk

    def seekable(self):
        return True


def _open_workbook(body):
    if not isinstance(body, (bytes, bytearray)) or not body:
        raise PhiladelphiaAdsDataError("ADS workbook body must be nonempty bytes")
    try:
        archive = zipfile.ZipFile(_BytesReader(bytes(body)))
    except zipfile.BadZipFile as exc:
        raise PhiladelphiaAdsDataError("ADS workbook was not a valid xlsx: %s" % exc)
    names = set(archive.namelist())
    for required in ("xl/workbook.xml", "xl/worksheets/sheet1.xml"):
        if required not in names:
            raise PhiladelphiaAdsDataError("ADS workbook lacked %s" % required)
    return archive


def _shared_strings(archive):
    try:
        raw = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(raw)
    strings = []
    for si in root.findall(_q("si")):
        strings.append("".join(node.text or "" for node in si.iter(_q("t"))))
    return strings


def _col_letter(cell_ref):
    letters = []
    for char in cell_ref:
        if char.isalpha():
            letters.append(char)
        else:
            break
    return "".join(letters)


def _cell_value(cell, strings):
    value_node = cell.find(_q("v"))
    if cell.get("t") == "inlineStr":
        node = cell.find(_q("is"))
        if node is None:
            return None
        return "".join(t.text or "" for t in node.iter(_q("t")))
    if value_node is None:
        return None
    text = value_node.text
    if text is None:
        return None
    if cell.get("t") == "s":
        return strings[int(text)]
    return text


def _canonical_value(text):
    """Render a published numeric ADS cell as a deterministic plain decimal.

    The stored cell text is the authoritative published value; Excel writes some
    cells in scientific notation (e.g. ``4.6676039626174906E-2``) and small ADS
    readings reach ``-1.0106097429019023E-5``. We parse the ORIGINAL text with
    ``decimal.Decimal`` — exact, no IEEE-754 float round-trip loss — and re-render
    it in plain (non-exponent) form with ``format(d, "f")``. No rounding is
    applied: this is a faithful copy of the published digits, only the exponent
    is normalized away so every value is a comparable plain decimal string.
    """
    text = text.strip()
    if not text:
        raise PhiladelphiaAdsDataError("ADS value cell was empty after strip")
    try:
        number = Decimal(text)
    except (TypeError, ValueError, InvalidOperation):
        raise PhiladelphiaAdsDataError("ADS value was not numeric: %r" % text)
    if not number.is_finite():
        raise PhiladelphiaAdsDataError("ADS value was not finite: %r" % text)
    rendered = format(number, "f")
    if not _FINITE_DECIMAL_RE.match(rendered):
        raise PhiladelphiaAdsDataError(
            "ADS value did not render as a plain decimal: %r -> %r"
            % (text, rendered)
        )
    return rendered


def _ads_date_to_iso(value):
    match = _ADS_DATE_RE.match(value.strip())
    if not match:
        raise PhiladelphiaAdsDataError("ADS date was not YYYY:MM:DD: %r" % value)
    year, month, day = match.groups()
    try:
        parsed = datetime(int(year), int(month), int(day))
    except ValueError:
        raise PhiladelphiaAdsDataError("ADS date was not a real date: %r" % value)
    return parsed.strftime("%Y-%m-%d")


def _read_rows(archive, strings):
    sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.findall(".//%s" % _q("row")):
        cells = {}
        for cell in row.findall(_q("c")):
            ref = cell.get("r")
            if not ref:
                continue
            cells[_col_letter(ref)] = _cell_value(cell, strings)
        rows.append(cells)
    return rows


def parse_philadelphia_ads_workbook(series, body):
    """Return the ADS_Index observations as a list of dicts.

    Each observation carries ``series_id`` (from the reviewed ``series`` config),
    ``observation_period`` (ISO date), ``value`` (plain-decimal string), ``unit``,
    and ``label``. RECBARS is validated as present-and-0/1 but never emitted.
    """
    if not isinstance(series, dict):
        raise PhiladelphiaAdsDataError("ADS series config must be an object")
    series_id = series.get("series_id")
    unit = series.get("unit")
    label = series.get("label")
    if not isinstance(series_id, str) or not series_id:
        raise PhiladelphiaAdsDataError("ADS series_id is missing")
    if not isinstance(unit, str) or not unit:
        raise PhiladelphiaAdsDataError("ADS unit is missing")

    archive = _open_workbook(body)
    strings = _shared_strings(archive)
    rows = _read_rows(archive, strings)
    if not rows:
        raise PhiladelphiaAdsDataError("ADS workbook had no rows")

    header = rows[0]
    if (
        header.get("A") != _HEADER_DATE
        or header.get("B") != _HEADER_VALUE
        or header.get("C") != _HEADER_RECBARS
    ):
        raise PhiladelphiaAdsDataError(
            "ADS header row was not [Date, ADS_Index, RECBARS]: %r" % header
        )

    observations = []
    seen = set()
    for row in rows[1:]:
        date_cell = row.get("A")
        value_cell = row.get("B")
        recbars_cell = row.get("C")
        if date_cell is None or str(date_cell).strip() == "":
            # trailing blank rows are permissible; skip them.
            continue
        period = _ads_date_to_iso(str(date_cell))
        if period in seen:
            raise PhiladelphiaAdsDataError("ADS duplicate date: %r" % period)
        seen.add(period)
        if value_cell is None or str(value_cell).strip() == "":
            raise PhiladelphiaAdsDataError(
                "ADS row %s had no ADS_Index value" % period
            )
        value = _canonical_value(str(value_cell))
        # RECBARS must be present and 0/1 but is a recession-LABEL comparator and
        # is intentionally NOT emitted as a series (CLAUDE.md, §10, §22.4).
        if recbars_cell is None or str(recbars_cell).strip() not in ("0", "1"):
            raise PhiladelphiaAdsDataError(
                "ADS RECBARS was not 0/1 at %s: %r" % (period, recbars_cell)
            )
        observations.append({
            "series_id": series_id,
            "observation_period": period,
            "value": value,
            "unit": unit,
            "label": label or series_id,
        })
    if not observations:
        raise PhiladelphiaAdsDataError("ADS workbook produced no observations")
    return observations
