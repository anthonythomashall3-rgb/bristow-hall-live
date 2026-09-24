"""Source-specific deterministic parsers.

Each returns a Normalized record or raises ParseError. Parsers never fabricate
observations: a missing/"."/null value is preserved as ``None`` (unavailable
stays unavailable). HTML, empty, and truncated payloads are rejected.
"""
from __future__ import annotations

import dataclasses
import json
from typing import List, Optional, Tuple


class ParseError(Exception):
    """Raised when a payload cannot be parsed into a valid normalized series."""


@dataclasses.dataclass(frozen=True)
class Normalized:
    observations: List[Tuple[str, Optional[float]]]  # (period, value|None), chronological
    provider_availability: Optional[str]             # publisher-side availability clock, if any
    coverage: Tuple[str, str]                         # (first_period, last_period)
    count: int
    latest_value: Optional[float]


def _reject_html_or_empty(raw: bytes) -> None:
    if not raw or not raw.strip():
        raise ParseError("empty payload")
    head = raw[:512].lstrip().lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html") or head.startswith(b"<"):
        raise ParseError("HTML payload is not accepted as data")


def _loads(raw: bytes):
    text = raw.decode("utf-8", "strict") if isinstance(raw, bytes) else raw
    try:
        return json.loads(text)
    except Exception:
        # A source may legitimately append only trailing WHITESPACE. Accept that,
        # but reject any trailing non-whitespace (truncation / proxy-error / HTML
        # appended after a valid object must NOT pass as complete data).
        try:
            obj, end = json.JSONDecoder().raw_decode(text)
        except Exception as exc:
            raise ParseError("invalid JSON: %s" % exc)
        if text[end:].strip():
            raise ParseError("trailing non-whitespace after JSON document (truncated or corrupted payload)")
        return obj


def _finish(pairs: List[Tuple[str, Optional[float]]], provider: Optional[str]) -> Normalized:
    if not pairs:
        raise ParseError("no observations parsed")
    pairs = sorted(pairs, key=lambda kv: kv[0])
    latest = None
    for _, v in reversed(pairs):
        if v is not None:
            latest = v
            break
    return Normalized(observations=pairs, provider_availability=provider,
                      coverage=(pairs[0][0], pairs[-1][0]), count=len(pairs), latest_value=latest)


def _f(value) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", ".", "-", "NA", "NaN", "null", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_oecd_sdmx_json(raw: bytes) -> Normalized:
    _reject_html_or_empty(raw)
    doc = _loads(raw)
    data = doc.get("data") if isinstance(doc, dict) else None
    if not data:
        raise ParseError("SDMX: no data section")
    structs = data.get("structures") or ([data.get("structure")] if data.get("structure") else [])
    if not structs or not structs[0]:
        raise ParseError("SDMX: no structure block")
    obs_dim = structs[0]["dimensions"]["observation"][0]["values"]
    periods = [v["id"] for v in obs_dim]
    datasets = data.get("dataSets") or []
    if not datasets:
        raise ParseError("SDMX: no dataSets")
    series = datasets[0].get("series") or {}
    if not series:
        raise ParseError("SDMX: no series")
    key = sorted(series.keys())[0]
    obs = series[key].get("observations") or {}
    pairs = []
    for idx, arr in obs.items():
        period = periods[int(idx)]
        value = _f(arr[0]) if isinstance(arr, list) and arr else None
        pairs.append((period, value))
    provider = None
    meta = doc.get("meta") if isinstance(doc, dict) else None
    if isinstance(meta, dict):
        provider = meta.get("prepared")
    return _finish(pairs, provider)


def parse_bls_v2_json(raw: bytes) -> Normalized:
    _reject_html_or_empty(raw)
    doc = _loads(raw)
    if not isinstance(doc, dict):
        raise ParseError("BLS: not an object")
    if doc.get("status") != "REQUEST_SUCCEEDED":
        raise ParseError("BLS status not REQUEST_SUCCEEDED: %r" % doc.get("status"))
    results = doc.get("Results") or {}
    seriess = results.get("series") or []
    if not seriess:
        raise ParseError("BLS: no series")
    rows = seriess[0].get("data") or []
    pairs = []
    for r in rows:
        period = r.get("period", "")  # M01..M13, Q01..; keep BLS grain
        year = r.get("year", "")
        if not year or not period:
            continue
        pairs.append(("%s-%s" % (year, period), _f(r.get("value"))))
    return _finish(pairs, None)


def parse_fred_api_json(raw: bytes) -> Normalized:
    _reject_html_or_empty(raw)
    doc = _loads(raw)
    if not isinstance(doc, dict) or "observations" not in doc:
        raise ParseError("FRED: no observations")
    pairs = [(o.get("date", ""), _f(o.get("value"))) for o in doc["observations"] if o.get("date")]
    provider = doc.get("realtime_start")
    return _finish(pairs, provider)


_DISPATCH = {
    "oecd_sdmx_json": parse_oecd_sdmx_json,
    "bls_v2_json": parse_bls_v2_json,
    "fred_api_json": parse_fred_api_json,
}


def parse(kind: str, raw: bytes) -> Normalized:
    if kind not in _DISPATCH:
        raise ParseError("unknown parser kind: %s" % kind)
    return _DISPATCH[kind](raw)
