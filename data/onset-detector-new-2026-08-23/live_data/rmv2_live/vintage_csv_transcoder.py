"""Deterministic on-disk ALFRED long-CSV -> FRED output_type=2 wide-matrix
transcoder (B-LAND-1 §2.4 — the ONE counted new shape).

The existing deep vintage parser (adapters.parse_fred_json_api_vintages_deep)
admits genuine pre-2020 as-of vintages, but ONLY from the FRED keyed API
output_type=2 JSON body. The class-(a) on-disk vault vintages are the SAME
data in a different, long-CSV shape:

    file  <BASE>_<YYYY-MM-DD>.csv
    head  observation_date,<BASE>_<YYYYMMDD>
    rows  <reference_period>,<value>

This module reshapes those CSVs into the wide matrix the deep parser already
accepts, so the proven parser (not a bespoke one) does the record emission,
.DEEPASOF naming, deep-window gating and mode-tagging. It is the measured
answer to B-LAND-1's refuted premise ("reuse the existing vintage parser" —
the existing parser is JSON-only, so the schemas measurably differ; this
transcoder is that one new shape, §2.4).

Contract: no network, no AI, deterministic. Source CSV bytes are read, never
written; each file's sha256 is recorded as provenance alongside this module's
parser_version and the emitted response schema sha256.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

# (adapter, parser_version, response_schema_sha256) is the shape; this is the
# parser_version half. The adapter is the existing "fred_json_api_vintages_deep"
# and the response schema is the output_type=2 body this module emits.
TRANSCODER_PARSER_VERSION = "rmv2-live/vintage_csv_to_output_type2.v1"

_HEADER_RE = re.compile(r"^observation_date,([A-Za-z][A-Za-z0-9_.-]{0,127})_(\d{8})$")
_FILENAME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.-]{0,127})_(\d{4})-(\d{2})-(\d{2})\.csv$")


class TranscodeError(ValueError):
    """The on-disk CSV did not match the exact vintage shape; refuse, never guess."""


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_vintage_csv(path):
    """Return (base, vintage_yyyymmdd, [(reference_period, value_str), ...],
    source_sha256) for one <BASE>_<YYYY-MM-DD>.csv. Raises TranscodeError on any
    shape surprise — a silent skip would understate what was landed (§19.4)."""
    p = Path(path)
    raw = p.read_bytes()
    fm = _FILENAME_RE.match(p.name)
    if not fm:
        raise TranscodeError("filename is not <BASE>_<YYYY-MM-DD>.csv: %s" % p.name)
    file_base = fm.group(1)
    file_vintage = "%s%s%s" % (fm.group(2), fm.group(3), fm.group(4))

    lines = raw.decode("utf-8").splitlines()
    if not lines:
        raise TranscodeError("empty vintage csv: %s" % p.name)
    hm = _HEADER_RE.match(lines[0].strip())
    if not hm:
        raise TranscodeError("unexpected header %r in %s" % (lines[0], p.name))
    base, vintage = hm.group(1), hm.group(2)
    if base != file_base or vintage != file_vintage:
        raise TranscodeError(
            "header/filename disagree in %s: %s_%s vs %s_%s"
            % (p.name, base, vintage, file_base, file_vintage)
        )

    rows = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != 2:
            raise TranscodeError("row is not <period>,<value> in %s: %r" % (p.name, line))
        rows.append((parts[0], parts[1]))
    return base, vintage, rows, _sha256_hex(raw)


def transcode_base(files, source=None):
    """Merge every <BASE>_*.csv for ONE base into a FRED output_type=2 body.

    Returns (body_dict, provenance). Rows are sparse: a vintage column appears in
    a date row only where that vintage actually carries a cell (the deep parser
    iterates present columns; absence is not a hole). Deterministic: dates and
    columns are sorted. Duplicate (vintage, period) cells are refused.

    ``source`` is accepted for a uniform transcoder signature (the FRED-MD panel
    transcoder needs the base id from it); this ALFRED long-CSV shape carries the
    base in the filenames, so the argument is ignored here."""
    by_date = {}          # reference_period -> {column_name: value}
    provenance = []
    base_seen = None
    for f in files:
        base, vintage, rows, sha = parse_vintage_csv(f)
        if base_seen is None:
            base_seen = base
        elif base != base_seen:
            raise TranscodeError("mixed bases in one transcode: %s vs %s" % (base_seen, base))
        column = "%s_%s" % (base, vintage)
        for reference_period, value in rows:
            cell = by_date.setdefault(reference_period, {})
            if column in cell:
                raise TranscodeError("duplicate cell %s @ %s" % (column, reference_period))
            cell[column] = value
        provenance.append({
            "source_path": str(f),
            "source_sha256": sha,
            "base": base,
            "vintage": vintage,
            "row_count": len(rows),
        })

    observations = []
    for reference_period in sorted(by_date):
        row = {"date": reference_period}
        for column in sorted(by_date[reference_period]):
            row[column] = by_date[reference_period][column]
        observations.append(row)
    body = {"file_type": "json", "output_type": "2", "observations": observations}
    return body, provenance


def body_bytes(body):
    """Canonical UTF-8 bytes for the emitted body — stable input to the deep
    parser and a stable response_schema/response sha256."""
    return json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")


def response_schema_sha256(body):
    """sha256 of the body's SHAPE (sorted key set + the two file/output markers),
    independent of the cell values — the response_schema half of the shape id."""
    columns = set()
    for row in body.get("observations", []):
        columns.update(k for k in row if k != "date")
    descriptor = {
        "file_type": body.get("file_type"),
        "output_type": body.get("output_type"),
        "row_keys": ["date"],
        "column_pattern": r"^<BASE>_\d{8}$",
    }
    return hashlib.sha256(
        json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
