"""B-LAND-3C-R2 §1 — FRED-MD monthly macro panel -> FRED output_type=2 wide
matrix transcoder for ONE base column (the second counted new shape, §2.4).

FRED-MD (McCracken / St. Louis Fed) publishes one CSV per monthly vintage:

    line 0   sasdate,RPI,W875RX1,DPCERA3M086SBEA,CMRMTSPLx,...      (~127 columns)
    line 1   Transform:,5,5,5,5,...                                 (per-column
                                                                     transform code
                                                                     -- part of the
                                                                     schema, NOT a
                                                                     data row)
    line 2+  01/01/1959,<value>,<value>,...                         (sasdate =
                                                                     MM/DD/YYYY)

The proven deep parser (adapters.parse_fred_json_api_vintages_deep) already owns
.DEEPASOF naming, the 2000-2019 deep-window gate and mode tagging, but only from
the FRED keyed-API output_type=2 JSON body. This module reshapes, for ONE
requested base column, every vintage panel into that exact wide matrix so the
proven parser -- never a bespoke one -- does the record emission. It is the FRED
-MD half of B-LAND-3C's "one new shape"; the ALFRED long-CSV half lives in
``vintage_csv_transcoder`` and is untouched here.

Owner ruling (2026-08-05): a base is matched by EXACT panel column name (the
transform-code row is never a rename cue and suffixes are never stripped). So
``W875RX1`` maps to the canonical W875RX1 identity (confirmed by value overlap);
``CLAIMSx`` / ``CMRMTSPLx`` keep their OWN suffixed ids (NEAR class) and are
never aliased onto ICSA / CMRMTSPL.

Contract (as ``vintage_csv_transcoder``): no network, no AI, deterministic.
ORIGINAL panel bytes are read, never written; each panel's sha256 and its
per-base transform code are recorded as provenance alongside this module's
parser_version and the emitted response schema sha256. The emitted body is
byte-identical in SHAPE to the ALFRED transcoder's body, so it reuses that
module's ``body_bytes`` / ``response_schema_sha256`` and feeds the same parser.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

# Reuse the emitted-body canonicaliser and shape-sha from the ALFRED transcoder:
# both shapes emit the identical output_type=2 wide matrix, so the response
# schema half of the shape id is shared. Only the parser_version (the source
# CSV shape) differs -- this is the FRED-MD panel half.
from .vintage_csv_transcoder import body_bytes, response_schema_sha256  # noqa: F401

TRANSCODER_PARSER_VERSION = "rmv2-live/fredmd_panel_to_output_type2.v1"

_BASE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
# vintage stamp from a panel filename: 1999-08.csv, FRED-MD_2024m12.csv,
# fred_md_2026-06.csv all yield <YYYY><MM>. The publish day is not carried in the
# panel filename; FRED-MD is a first-of-month named monthly release, so the
# vintage day is pinned to 01 (kept distinct from the ALFRED per-revision day so
# the two providers' as-of lanes never collide on a shared series id).
_FILE_VINTAGE_RE = re.compile(r"(\d{4})[-_ ]?m?(\d{2})")
_TRANSFORM_MARKER = "Transform:"


class PanelTranscodeError(ValueError):
    """A panel did not match the exact FRED-MD shape; refuse, never guess."""


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def vintage_yyyymmdd(filename: str) -> str:
    """<YYYYMM01> for a FRED-MD vintage panel filename (day pinned to 01)."""
    match = _FILE_VINTAGE_RE.search(Path(filename).name)
    if not match:
        raise PanelTranscodeError(
            "filename carries no <YYYY><MM> vintage: %s" % filename
        )
    year, month = match.group(1), match.group(2)
    if not ("01" <= month <= "12"):
        raise PanelTranscodeError("vintage month out of range: %s" % filename)
    return "%s%s01" % (year, month)


def _iso_period(sasdate: str) -> str:
    """FRED-MD sasdate (MM/DD/YYYY, occasionally YYYY-MM-DD) -> YYYY-MM-DD.

    The deep parser requires a canonical %Y-%m-%d observation date; anything
    that is not exactly one of the two accepted spellings is refused rather than
    coerced."""
    text = sasdate.strip()
    slash = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if slash:
        month, day, year = slash.group(1), slash.group(2), slash.group(3)
        return "%04d-%02d-%02d" % (int(year), int(month), int(day))
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if iso:
        return text
    raise PanelTranscodeError("unrecognised sasdate %r" % sasdate)


def parse_panel(path, base):
    """Return (vintage, transform_code, [(period, value_str), ...], sha256) for
    ONE base column of one FRED-MD panel. Raises PanelTranscodeError on any shape
    surprise -- a silent skip would understate what was landed (§19.4)."""
    p = Path(path)
    raw = p.read_bytes()
    vintage = vintage_yyyymmdd(p.name)

    lines = raw.decode("utf-8").splitlines()
    if len(lines) < 2:
        raise PanelTranscodeError("panel too short: %s" % p.name)
    header = lines[0].split(",")
    if not header or header[0].strip() != "sasdate":
        raise PanelTranscodeError("panel header does not start with sasdate: %s" % p.name)
    if base not in header:
        raise PanelTranscodeError("base %s absent from panel %s" % (base, p.name))
    base_idx = header.index(base)

    transform = lines[1].split(",")
    if not transform or transform[0].strip() != _TRANSFORM_MARKER:
        raise PanelTranscodeError("panel line 2 is not the Transform row: %s" % p.name)
    if len(transform) <= base_idx:
        raise PanelTranscodeError("transform row is short in %s" % p.name)
    transform_code = transform[base_idx].strip()

    rows = []
    for line in lines[2:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) != len(header):
            raise PanelTranscodeError(
                "row width %d != header %d in %s" % (len(parts), len(header), p.name)
            )
        period = _iso_period(parts[0])
        value = parts[base_idx].strip()
        if value in ("", "."):
            continue  # cell did not exist as-of this vintage -> absence, not a hole
        rows.append((period, value))
    return vintage, transform_code, rows, _sha256_hex(raw)


def transcode_base(files, source=None):
    """Merge ONE base column across every FRED-MD vintage panel into a FRED
    output_type=2 body. Duck-type compatible with
    ``vintage_csv_transcoder.transcode_base`` (the same (files, source) shape
    ``offline_binding.bind_offline_vintage`` calls), so the proven binder reuses
    it unchanged.

    Returns (body_dict, provenance). The base column is taken from
    ``source['series']['series_id']`` -- an EXACT column-name match, per the owner
    identity rule; a missing base raises rather than guessing an alias. Rows are
    sparse (the deep parser iterates present columns; absence is not a hole).
    Deterministic: dates and columns are sorted. Duplicate (vintage, period)
    cells are refused."""
    if not isinstance(source, dict):
        raise PanelTranscodeError("transcode_base requires the source (for base id)")
    series = source.get("series")
    if not isinstance(series, dict) or not isinstance(series.get("series_id"), str):
        raise PanelTranscodeError("source series_id is missing")
    base = series["series_id"]
    if not _BASE_RE.match(base):
        raise PanelTranscodeError("base series_id is not a valid id: %r" % base)

    by_date = {}          # observation_period -> {column_name: value}
    provenance = []
    for f in files:
        vintage, transform_code, rows, sha = parse_panel(f, base)
        column = "%s_%s" % (base, vintage)
        for period, value in rows:
            cell = by_date.setdefault(period, {})
            if column in cell:
                raise PanelTranscodeError("duplicate cell %s @ %s" % (column, period))
            cell[column] = value
        provenance.append({
            "source_path": str(f),
            "source_sha256": sha,
            "base": base,
            "vintage": vintage,
            "row_count": len(rows),
            "transform_code": transform_code,
        })

    observations = []
    for period in sorted(by_date):
        row = {"date": period}
        for column in sorted(by_date[period]):
            row[column] = by_date[period][column]
        observations.append(row)
    body = {"file_type": "json", "output_type": "2", "observations": observations}
    return body, provenance
