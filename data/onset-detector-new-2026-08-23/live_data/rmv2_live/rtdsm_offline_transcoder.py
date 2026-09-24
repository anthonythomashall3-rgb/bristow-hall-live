"""B-LAND-4-R2 §2 — RTDSM xlsx matrix -> FRED output_type=2 wide-matrix
transcoder (the RTDSM half of the "one counted new shape", §2.4).

The proven deep parser (adapters.parse_fred_json_api_vintages_deep) already owns
``.DEEPASOF`` naming, the deep-window gate, the earliest-prioritised growth cap
and mode tagging — but only from a FRED output_type=2 JSON body. ``rtdsm_xlsx``
reads the Philadelphia Fed Real-Time Data Set workbook (one xlsx per variable,
every as-of vintage a column) into ``(vintage, period, value)`` cells; this
module reshapes those cells, for ONE variable's OWN base id, into that exact
output_type=2 body, so the proven parser — never a bespoke one — does the record
emission, the naming, the window gate and the cap.

Duck-type compatible with ``vintage_csv_transcoder.transcode_base`` /
``fredmd_panel.transcode_base`` (the ``(files, source)`` shape
``offline_binding.bind_offline_vintage`` calls), so the proven offline binder
reuses this transcoder unchanged. Two differences from those two:

  * a single RTDSM workbook carries EVERY vintage as a column, so this takes
    exactly ONE file and the per-vintage provenance all shares that one
    workbook's sha256 (honest: every vintage really came from that one file);
  * the workbook's variable name (``source['rtdsm_var']``, e.g. ``RUC``) and the
    LANDED base id (``source['series']['series_id']``, e.g. ``RTDSM_RUC``) are
    distinct — the base is own-base (CLAIMSx precedent), never a FRED alias.

The emitted body is byte-identical in SHAPE to the ALFRED/FRED-MD transcoders'
body, so it reuses ``vintage_csv_transcoder``'s ``body_bytes`` /
``response_schema_sha256`` and feeds the same parser.

Contract (as the sibling transcoders): no network, no AI, deterministic. The
ORIGINAL workbook bytes are read, never written; the workbook sha256 and each
vintage's stamp are recorded as provenance alongside this module's
parser_version and the emitted response schema sha256.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import rtdsm_xlsx
# Reuse the emitted-body canonicaliser and shape-sha from the ALFRED transcoder:
# all three shapes emit the identical output_type=2 wide matrix, so the response
# schema half of the shape id is shared. Only the parser_version (the source
# shape) differs -- this is the RTDSM xlsx half.
from .vintage_csv_transcoder import body_bytes, response_schema_sha256  # noqa: F401

TRANSCODER_PARSER_VERSION = "rmv2-live/rtdsm_xlsx_to_output_type2.v1"

_BASE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
# Own-base convention (B-LAND-4-R2): the landed base id is RTDSM_<VAR>, so the
# workbook variable name is the base with the RTDSM_ prefix stripped. This lets
# the PERSISTED source object carry only the standard config keys (the config
# schema, config.py::_require_keys, refuses any extra source field), while the
# transcoder still knows which workbook column to read.
_OWN_BASE_PREFIX = "RTDSM_"


class RtdsmTranscodeError(ValueError):
    """The workbook / source did not match the exact RTDSM shape; refuse, never
    guess (a silent skip would understate what was landed, §19.4)."""


def _resolve_var(source, base):
    """Workbook variable name: an explicit ``source['rtdsm_var']`` if present
    (test/override), else derived from the ``RTDSM_<VAR>`` own-base id."""
    var = source.get("rtdsm_var")
    if isinstance(var, str) and var:
        return var
    if base.startswith(_OWN_BASE_PREFIX) and len(base) > len(_OWN_BASE_PREFIX):
        return base[len(_OWN_BASE_PREFIX):]
    raise RtdsmTranscodeError(
        "cannot resolve workbook variable: base %r is not RTDSM_<VAR> and no "
        "rtdsm_var override was given" % base
    )


def transcode_base(files, source=None):
    """Reshape ONE RTDSM variable workbook into a FRED output_type=2 body.

    Returns ``(body_dict, provenance)``. The LANDED base id is taken from
    ``source['series']['series_id']`` (own-base, e.g. ``RTDSM_RUC``); the
    workbook's variable name from ``source['rtdsm_var']`` (e.g. ``RUC``). Rows
    are sparse (the deep parser iterates present columns; absence is not a hole).
    Deterministic: dates and columns are sorted. A duplicate (vintage, period)
    cell is refused."""
    if not isinstance(source, dict):
        raise RtdsmTranscodeError("transcode_base requires the source (base id + var)")
    series = source.get("series")
    if not isinstance(series, dict) or not isinstance(series.get("series_id"), str):
        raise RtdsmTranscodeError("source series_id (landed base) is missing")
    base = series["series_id"]
    if not _BASE_RE.match(base):
        raise RtdsmTranscodeError("base series_id is not a valid id: %r" % base)
    var = _resolve_var(source, base)

    files = list(files)
    if len(files) != 1:
        raise RtdsmTranscodeError(
            "RTDSM binds exactly one workbook per variable (got %d)" % len(files)
        )
    path = Path(files[0])
    workbook_bytes = path.read_bytes()
    try:
        cells, sha, _meta = rtdsm_xlsx.parse_matrix(workbook_bytes, var)
    except rtdsm_xlsx.RtdsmShapeError as exc:
        raise RtdsmTranscodeError("workbook did not match the RTDSM shape: %s" % exc)

    by_date = {}          # observation_period -> {column_name: value}
    per_vintage_rows = {}  # vintage -> non-absence cell count
    for cell in cells:
        vintage = cell["vintage"]
        period = cell["period"]
        column = "%s_%s" % (base, vintage)
        row = by_date.setdefault(period, {})
        if column in row:
            raise RtdsmTranscodeError("duplicate cell %s @ %s" % (column, period))
        row[column] = cell["value"]
        per_vintage_rows[vintage] = per_vintage_rows.get(vintage, 0) + 1

    observations = []
    for period in sorted(by_date):
        row = {"date": period}
        for column in sorted(by_date[period]):
            row[column] = by_date[period][column]
        observations.append(row)
    body = {"file_type": "json", "output_type": "2", "observations": observations}

    provenance = [
        {
            "source_path": str(path),
            "source_sha256": sha,
            "base": base,
            "vintage": vintage,
            "row_count": per_vintage_rows[vintage],
        }
        for vintage in sorted(per_vintage_rows)
    ]
    return body, provenance
