"""Strict normalization for the Dallas Fed Weekly Economic Index native workbook.

This module performs no network I/O. It parses the on-disk (prefetch-cached)
``weekly-economic-index.xlsx`` bytes with the stdlib zip/XML reader — no
third-party spreadsheet dependency, so the parse is deterministic and auditable.

The workbook's ``2008-current`` sheet carries the current WEI (col B) plus a set
of embedded publisher AS-OF snapshot columns (each header ``WEI as of M/D/YYYY``).
Owner ruling 2026-08-06 (question ``20260806T065219Z_B-OFFLINE-3``): these land as
ONE flat offline-current EVIDENCE lane of distinct series — the current column
and one series per as-of snapshot — under a SINGLE declared information-set mode
(``substituted_diagnostic``). Each as-of column is preserved with its snapshot
date both in the series_id and as the additive per-record field
``provider_asof_date``. They are DIAGNOSTIC EVIDENCE, never store-native
``archive_snapshot_asof`` vintages (the single-vintage offline-current binder
cannot represent true multi-vintage as-of lanes; that is a separate follow-up,
``B-OFFLINE-6``). This parser therefore neither reconstructs nor promotes them to
replayable vintages — it copies the published cell values verbatim.
"""

from __future__ import absolute_import

import re
import zipfile
from datetime import datetime
from xml.etree import ElementTree as ET


_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS = {"m": _MAIN_NS}

_ASOF_HEADER_RE = re.compile(r"^WEI as of (\d{1,2})/(\d{1,2})/(\d{4})$")
_US_DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_FINITE_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_SERIES_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")


class DallasWeiDataError(ValueError):
    """Raised when the WEI workbook bytes fail the reviewed contract."""


def _q(tag):
    return "{%s}%s" % (_MAIN_NS, tag)


def _open_workbook(body):
    if not isinstance(body, (bytes, bytearray)) or not body:
        raise DallasWeiDataError("WEI workbook body must be nonempty bytes")
    try:
        archive = zipfile.ZipFile(_BytesReader(bytes(body)))
    except zipfile.BadZipFile as exc:
        raise DallasWeiDataError("WEI workbook was not a valid xlsx: %s" % exc)
    names = set(archive.namelist())
    for required in ("xl/workbook.xml", "xl/_rels/workbook.xml.rels"):
        if required not in names:
            raise DallasWeiDataError("WEI workbook lacked %s" % required)
    return archive


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


def _shared_strings(archive):
    if "xl/sharedStrings.xml" not in set(archive.namelist()):
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for si in root.findall("m:si", _NS):
        strings.append("".join(node.text or "" for node in si.iter(_q("t"))))
    return strings


def _sheet_path_for(archive, sheet_name):
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_target = {}
    for rel in rels:
        rel_target[rel.get("Id")] = rel.get("Target")
    for sheet in workbook.iter(_q("sheet")):
        if sheet.get("name") == sheet_name:
            rid = sheet.get("{%s}id" % _REL_NS)
            target = rel_target.get(rid)
            if not target:
                raise DallasWeiDataError(
                    "WEI workbook sheet relationship was missing"
                )
            if target.startswith("/"):
                return target.lstrip("/")
            return "xl/" + target
    raise DallasWeiDataError(
        "WEI workbook lacked the '%s' sheet" % sheet_name
    )


def _col_letter(cell_ref):
    letters = []
    for char in cell_ref:
        if char.isalpha():
            letters.append(char)
        else:
            break
    return "".join(letters)


def _cell_value(cell, strings):
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        node = cell.find("m:is", _NS)
        return "".join(t.text or "" for t in node.iter(_q("t"))) if node is not None else None
    value_node = cell.find("m:v", _NS)
    if value_node is None:
        return None
    text = value_node.text
    if text is None:
        return None
    if cell_type == "s":
        index = int(text)
        if index < 0 or index >= len(strings):
            raise DallasWeiDataError("WEI workbook shared-string index invalid")
        return strings[index]
    return text


def _canonical_cell_value(cell):
    """Render a published numeric cell as a deterministic plain decimal string.

    Excel stores WEI cells as IEEE-754 doubles, some written in scientific
    notation (e.g. ``7.0000000000000007E-2``). We reproduce the SHORTEST decimal
    that round-trips to the stored double (Python's float repr), so ``…E-2``
    becomes ``0.07`` while a genuinely-noisy stored double (``1.1100000000000001``)
    is preserved as-is. No rounding is applied — this is a faithful copy of the
    published value, not a re-derivation. WEI magnitudes never reach the range
    where the shortest repr is itself scientific; we reject it defensively if so.
    """
    text = cell.strip()
    if not text:
        raise DallasWeiDataError("WEI cell was empty after strip")
    try:
        number = float(text)
    except (TypeError, ValueError):
        raise DallasWeiDataError("WEI value was not numeric: %r" % text)
    if number != number or number in (float("inf"), float("-inf")):
        raise DallasWeiDataError("WEI value was not finite: %r" % text)
    rendered = repr(number)
    if not _FINITE_DECIMAL_RE.match(rendered):
        raise DallasWeiDataError(
            "WEI value did not render as a plain decimal: %r -> %r"
            % (text, rendered)
        )
    return rendered


def _us_date_to_iso(value):
    match = _US_DATE_RE.match(value)
    if not match:
        raise DallasWeiDataError("WEI date was not MM/DD/YYYY: %r" % value)
    month, day, year = match.groups()
    try:
        parsed = datetime(int(year), int(month), int(day))
    except ValueError:
        raise DallasWeiDataError("WEI date was not a real date: %r" % value)
    return parsed.strftime("%Y-%m-%d")


def _header_asof_iso(header):
    match = _ASOF_HEADER_RE.match(header)
    if not match:
        return None
    month, day, year = (int(g) for g in match.groups())
    try:
        parsed = datetime(year, month, day)
    except ValueError:
        raise DallasWeiDataError("WEI as-of header date was invalid: %r" % header)
    return parsed.strftime("%Y-%m-%d")


def _read_grid(archive, sheet_name, strings):
    sheet_path = _sheet_path_for(archive, sheet_name)
    root = ET.fromstring(archive.read(sheet_path))
    rows = []
    for row in root.iter(_q("row")):
        cells = {}
        for cell in row.findall("m:c", _NS):
            ref = cell.get("r")
            if not ref:
                raise DallasWeiDataError("WEI cell lacked a reference")
            cells[_col_letter(ref)] = _cell_value(cell, strings)
        rows.append(cells)
    if not rows:
        raise DallasWeiDataError("WEI sheet '%s' had no rows" % sheet_name)
    return rows


def _validate_members(series_config):
    if not isinstance(series_config, dict):
        raise DallasWeiDataError("WEI series config must be an object")
    unit = series_config.get("unit")
    if not isinstance(unit, str) or not unit:
        raise DallasWeiDataError("WEI series unit was invalid")
    sheet = series_config.get("vintage_sheet")
    if not isinstance(sheet, str) or not sheet:
        raise DallasWeiDataError("WEI vintage_sheet was invalid")
    members = series_config.get("members")
    if not isinstance(members, list) or not members:
        raise DallasWeiDataError("WEI series members were invalid")
    current = None
    asof_by_date = {}
    seen_ids = set()
    for member in members:
        if not isinstance(member, dict):
            raise DallasWeiDataError("WEI member was not an object")
        series_id = member.get("series_id")
        label = member.get("label")
        kind = member.get("column_kind")
        asof = member.get("asof_date")
        if (
            not isinstance(series_id, str) or
            not _SERIES_ID_RE.match(series_id) or
            series_id in seen_ids or
            series_id == "WEI" or
            not isinstance(label, str) or not label
        ):
            raise DallasWeiDataError("WEI member identity was invalid")
        seen_ids.add(series_id)
        if kind == "current":
            if asof is not None:
                raise DallasWeiDataError("WEI current member must not carry an as-of date")
            if current is not None:
                raise DallasWeiDataError("WEI config had more than one current member")
            current = member
        elif kind == "asof":
            if not isinstance(asof, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", asof):
                raise DallasWeiDataError("WEI as-of member date was invalid")
            if asof in asof_by_date:
                raise DallasWeiDataError("WEI config duplicated an as-of date")
            asof_by_date[asof] = member
        else:
            raise DallasWeiDataError("WEI member column_kind was invalid")
    if current is None:
        raise DallasWeiDataError("WEI config lacked the current member")
    return unit, sheet, current, asof_by_date


def parse_dallas_wei_workbook(series_config, body):
    """Return deterministic observation dicts for every configured WEI series.

    Each observation carries: series_id, observation_period (ISO), value (the
    verbatim published cell decimal string, or None), unit, label,
    provider_asof_date (None for the current column, else the snapshot ISO date),
    column_kind. The set of file columns and the set of configured members must
    map one-to-one — an unmapped file column or a phantom config member is a hard
    error, so the admission gate's derived series set equals the emitted set.
    """
    unit, sheet, current_member, asof_by_date = _validate_members(series_config)
    archive = _open_workbook(body)
    strings = _shared_strings(archive)
    rows = _read_grid(archive, sheet, strings)

    header = rows[0]
    if header.get("A") != "Date" or header.get("B") != "WEI":
        raise DallasWeiDataError("WEI header row A/B were not Date/WEI")

    # Map file columns -> (kind, asof_iso). B is the current column; every other
    # populated header must be a 'WEI as of DATE' column.
    col_to_member = {}
    file_asof_dates = set()
    for col_letter, header_text in header.items():
        if col_letter == "A":
            continue
        if header_text is None or header_text == "":
            continue
        if col_letter == "B":
            col_to_member[col_letter] = current_member
            continue
        asof_iso = _header_asof_iso(header_text)
        if asof_iso is None:
            raise DallasWeiDataError(
                "WEI column header was not a recognized as-of header: %r"
                % header_text
            )
        member = asof_by_date.get(asof_iso)
        if member is None:
            raise DallasWeiDataError(
                "WEI file as-of column %s is absent from the config" % asof_iso
            )
        file_asof_dates.add(asof_iso)
        col_to_member[col_letter] = member

    # every configured as-of member must be present in the file
    missing = set(asof_by_date) - file_asof_dates
    if missing:
        raise DallasWeiDataError(
            "WEI config as-of members absent from the file: %s"
            % ", ".join(sorted(missing))
        )

    observations = []
    seen = set()
    for row in rows[1:]:
        raw_date = row.get("A")
        if raw_date is None or raw_date == "":
            # trailing blank rows in the workbook are ignored
            if all(row.get(c) in (None, "") for c in col_to_member):
                continue
            raise DallasWeiDataError("WEI data row lacked a date")
        observation_period = _us_date_to_iso(raw_date)
        for col_letter, member in col_to_member.items():
            cell = row.get(col_letter)
            if cell is None or cell == "":
                continue
            value = _canonical_cell_value(cell)
            key = (member["series_id"], observation_period)
            if key in seen:
                raise DallasWeiDataError(
                    "WEI produced a duplicate (series, period): %r" % (key,)
                )
            seen.add(key)
            observations.append({
                "series_id": member["series_id"],
                "observation_period": observation_period,
                "value": value,
                "unit": unit,
                "label": member["label"],
                "provider_asof_date": member.get("asof_date"),
                "column_kind": member["column_kind"],
            })
    if not observations:
        raise DallasWeiDataError("WEI workbook produced no observations")
    observations.sort(key=lambda row: (row["series_id"], row["observation_period"]))
    return observations
