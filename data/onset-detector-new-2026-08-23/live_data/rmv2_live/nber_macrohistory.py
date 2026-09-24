"""Strict normalization for the NBER Macrohistory Database fixed-layout ``.dat``
files (B-OFFLINE-4).

The NBER Macrohistory ``.dat`` rectangular-data files are a fixed-column text
format: a 4-character year, a right-justified period field (blank for an
annual-summary row, else month ``1``-``12``), a separator space, then a
left-padded plain-decimal value. There is NO in-file header block — the codebook
lives in the sibling ``.txt`` doc — so this parser validates the ROW STRUCTURE
and rejects a file whose rows do not parse rather than silently emitting a short
series (B-OFFLINE-4 contract). Layout measured by CH-R50
(``research/nber_layout_v1.json``) and re-verified from the cache bytes.

Column contract (measured across the shortlist, all chapters, LF line endings,
latin-1):

* ``year``   = ``line[0:4]``            — 4-digit integer
* ``period`` = ``line[4:9].strip()``    — ``''`` (annual-summary) or month 1-12
* ``value``  = ``line[9:].strip()``     — ``''`` / ``'.'`` == MISSING, else decimal

Using fixed columns (not a naive whitespace split) is required: a monthly row
with a blank value (``'1957   10 '``) tokenizes to two fields exactly like a
genuine annual-summary row (``'1919      108.'``); only the column position of the
period disambiguates them.

Owner ruling carried by the batch (B-OFFLINE-4, 2026-08-06): each series lands
under its OWN ``NBER_*`` id, NEVER aliased to a modern twin, class RESEARCH/NEAR,
frozen archival, out-of-sample validation scope only. This parser therefore never
merges, splices, or re-bases — it copies the published value verbatim (rendered as
the shortest decimal that round-trips the published number).
"""

from __future__ import absolute_import

import re


_SERIES_ID_RE = re.compile(r"^NBER_[A-Za-z0-9_]+$")
_NUMERIC_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)$")
_CANONICAL_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

_MISSING_TOKENS = frozenset(("", "."))
_MIN_YEAR = 1700
_MAX_YEAR = 2100


class NberMacrohistoryDataError(ValueError):
    """Raised when the NBER ``.dat`` bytes fail the reviewed contract."""


def _validate_config(series_config):
    if not isinstance(series_config, dict):
        raise NberMacrohistoryDataError("NBER series config must be an object")
    series_id = series_config.get("series_id")
    if not isinstance(series_id, str) or not _SERIES_ID_RE.match(series_id):
        raise NberMacrohistoryDataError(
            "NBER series_id must match NBER_* : %r" % (series_id,)
        )
    unit = series_config.get("unit")
    if not isinstance(unit, str) or not unit:
        raise NberMacrohistoryDataError("NBER series unit was invalid")
    label = series_config.get("label")
    if not isinstance(label, str) or not label:
        raise NberMacrohistoryDataError("NBER series label was invalid")
    return series_id, unit, label


def _canonical_value(token):
    """Render a published NBER decimal as the shortest round-tripping decimal.

    NBER values are plain decimals with variable precision (``8.81000``),
    trailing-dot integers (``103.``), and occasional negatives. We reproduce the
    shortest decimal that round-trips the published number (Python float repr),
    so ``8.81000`` -> ``8.81`` and ``103.`` -> ``103.0`` — the numeric value is
    unchanged, no rounding is applied. Scientific-notation output is rejected
    defensively (NBER magnitudes never reach that range).
    """
    if not _NUMERIC_RE.match(token):
        raise NberMacrohistoryDataError("NBER value was not numeric: %r" % token)
    try:
        number = float(token)
    except (TypeError, ValueError):
        raise NberMacrohistoryDataError("NBER value was not numeric: %r" % token)
    if number != number or number in (float("inf"), float("-inf")):
        raise NberMacrohistoryDataError("NBER value was not finite: %r" % token)
    rendered = repr(number)
    if not _CANONICAL_DECIMAL_RE.match(rendered):
        raise NberMacrohistoryDataError(
            "NBER value did not render as a plain decimal: %r -> %r"
            % (token, rendered)
        )
    return rendered


def parse_nber_macrohistory_dat(series_config, body):
    """Return deterministic observation dicts for one NBER Macrohistory series.

    Each observation carries: series_id, observation_period, value (canonical
    decimal string, or None for a missing cell), unit, label, nber_file_period
    (the raw published period token), period_granularity ('monthly'|'annual'),
    value_status ('actual'|'unavailable'). Missing cells ARE emitted (value=None)
    so the record count equals the file's row count and non-missing observations
    equal the published obs_count — mirroring the FRED current-lane convention.
    A row whose fixed columns do not parse is a hard error.
    """
    series_id, unit, label = _validate_config(series_config)
    if not isinstance(body, (bytes, bytearray)) or not body:
        raise NberMacrohistoryDataError("NBER .dat body must be nonempty bytes")
    text = bytes(body).decode("latin-1")

    observations = []
    seen = set()
    prev_year = None
    available = 0
    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")
        if line.strip() == "":
            continue
        if len(line) < 5:
            raise NberMacrohistoryDataError(
                "NBER data row was too short: %r" % raw_line
            )
        year_field = line[0:4]
        if not year_field.isdigit():
            raise NberMacrohistoryDataError(
                "NBER data row lacked a 4-digit year: %r" % raw_line
            )
        year = int(year_field)
        if year < _MIN_YEAR or year > _MAX_YEAR:
            raise NberMacrohistoryDataError(
                "NBER data row year out of range: %r" % raw_line
            )
        if prev_year is not None and year < prev_year:
            raise NberMacrohistoryDataError(
                "NBER data rows were not chronologically ordered near %r"
                % raw_line
            )
        prev_year = year

        period_token = line[4:9].strip()
        value_token = line[9:].strip()

        if period_token == "":
            granularity = "annual"
            observation_period = "%04d" % year
        else:
            if not period_token.isdigit():
                raise NberMacrohistoryDataError(
                    "NBER period field was not numeric: %r" % raw_line
                )
            month = int(period_token)
            if month < 1 or month > 12:
                raise NberMacrohistoryDataError(
                    "NBER month out of range 1-12: %r" % raw_line
                )
            granularity = "monthly"
            observation_period = "%04d-%02d-01" % (year, month)

        if value_token in _MISSING_TOKENS:
            value = None
            value_status = "unavailable"
        else:
            value = _canonical_value(value_token)
            value_status = "actual"
            available += 1

        key = (series_id, observation_period)
        if key in seen:
            raise NberMacrohistoryDataError(
                "NBER produced a duplicate (series, period): %r" % (key,)
            )
        seen.add(key)
        observations.append({
            "series_id": series_id,
            "observation_period": observation_period,
            "value": value,
            "unit": unit,
            "label": label,
            "nber_file_period": period_token,
            "period_granularity": granularity,
            "value_status": value_status,
        })

    if not observations:
        raise NberMacrohistoryDataError(
            "NBER .dat produced no observations for %s" % series_id
        )
    if not available:
        raise NberMacrohistoryDataError(
            "NBER .dat produced no available observations for %s" % series_id
        )
    observations.sort(key=lambda row: (row["series_id"], row["observation_period"]))
    return observations
