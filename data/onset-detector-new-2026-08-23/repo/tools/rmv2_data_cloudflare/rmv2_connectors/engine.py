"""Fail-closed candidate-acquisition engine for the connectors.

Guarantees: atomic raw writes; immutable SHA-256 + attempt receipts; last-known-good
preserved on any failure (raw is only written after successful validation+parse);
duplicate-identical bytes are not rewritten; separate observation/provider/retrieval/
validation/release clocks; unavailable stays unavailable; credentials never persisted.
Never mutates production source heads, generations, or pointers.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

# reuse the overlay's proven atomic primitive
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.collector import _atomic_write, _safe_relative  # noqa: E402

from . import parsers, candidate
from .registry import ConnectorSpec

RECEIPT_SCHEMA = "recession-monitor-v2.connector-receipt.v1"


class HostNotAllowed(Exception):
    pass


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _parse_ts(value: str) -> dt.datetime:
    v = value.replace("Z", "+00:00")
    return dt.datetime.fromisoformat(v)


def _period_to_date(period: str) -> Optional[dt.datetime]:
    p = period.strip()
    try:
        if "M" in p:  # BLS 2025-M12
            y, m = p.split("-M"); return dt.datetime(int(y), int(m), 1, tzinfo=dt.timezone.utc)
        if p.count("-") == 2:  # 2026-06-01
            return _parse_ts(p + "T00:00:00+00:00")
        if p.count("-") == 1:  # 2026-06
            y, m = p.split("-"); return dt.datetime(int(y), int(m), 1, tzinfo=dt.timezone.utc)
    except Exception:
        return None
    return None


def _keychain_credential(name: str) -> str:
    """Read a credential from the macOS login keychain via `security
    find-generic-password -w -s <name>`. Returns "" if absent or on any error
    (non-macOS, locked keychain, item missing). The value is captured in memory
    only and never logged. Runs correctly under launchd (absolute tool path,
    no shell profile dependency)."""
    try:
        proc = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-w", "-s", name],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _credential_source(name: str) -> str:
    """Resolve credential and report WHICH source supplied it, without ever
    returning or logging the value. -> one of env|local_env|keychain|none."""
    if os.environ.get(name, ""):
        return "env"
    envf = Path(__file__).resolve().parents[3] / "live_data" / "config" / "local.env"
    if envf.is_file():
        for ln in envf.read_text().splitlines():
            ln = ln.strip()
            if ln.startswith(name + "=") and not ln.startswith("#"):
                if ln.split("=", 1)[1].strip():
                    return "local_env"
    if _keychain_credential(name):
        return "keychain"
    return "none"


def _read_credential(name: str) -> str:
    """Resolve a credential. Chain: environment variable first, then the
    gitignored live_data/config/local.env, then the macOS login keychain
    (§1.1: env wins; keychain is a fallback). Value is held in memory only and
    is never written to a file, receipt, log, or stdout (§1.2)."""
    val = os.environ.get(name, "")
    if val:
        return val
    envf = Path(__file__).resolve().parents[3] / "live_data" / "config" / "local.env"
    if envf.is_file():
        for ln in envf.read_text().splitlines():
            ln = ln.strip()
            if ln.startswith(name + "=") and not ln.startswith("#"):
                v = ln.split("=", 1)[1].strip()
                if v:
                    return v
    return _keychain_credential(name)


def _merge_bls_windows(payloads) -> bytes:
    """Merge several BLS v2 responses for one series into a single BLS-shaped
    envelope. Any window that did not succeed aborts the merge (fail-closed)."""
    merged = []
    series_id = None
    for b in payloads:
        doc = json.loads(b.decode("utf-8"))
        if doc.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError("BLS window status %r" % doc.get("status"))
        for s in doc.get("Results", {}).get("series", []):
            series_id = s.get("seriesID", series_id)
            merged.extend(s.get("data", []))
    envelope = {"status": "REQUEST_SUCCEEDED", "message": ["merged_bls_windows"],
                "Results": {"series": [{"seriesID": series_id, "data": merged}]}}
    return json.dumps(envelope).encode("utf-8")


def _bls_windowed_fetch(spec: ConnectorSpec) -> Tuple[bytes, str]:
    host = (urllib.parse.urlparse(spec.url_template).hostname or "").lower()
    if host not in {h.lower() for h in spec.allowed_hosts}:
        raise HostNotAllowed("request host %s not in allowlist" % host)
    reg_key = _read_credential("BLS_API_KEY")
    span = 19 if reg_key else 9  # registered v2 cap: 20 yrs/request; unregistered: 10
    end_year = dt.datetime.now(dt.timezone.utc).year
    start_year = spec.history_start_year or (end_year - span)
    payloads = []
    year = start_year
    while year <= end_year:
        window_end = min(year + span, end_year)
        window_body = {"seriesid": [spec.provider_code], "startyear": str(year), "endyear": str(window_end)}
        if reg_key:
            window_body["registrationkey"] = reg_key
        body = json.dumps(window_body).encode("utf-8")
        req = urllib.request.Request(spec.url_template, data=body,
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "rmv2-connector/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            final_host = (urllib.parse.urlparse(resp.geturl()).hostname or "").lower()
            if final_host not in {h.lower() for h in spec.allowed_hosts}:
                raise HostNotAllowed("redirected to disallowed host %s" % final_host)
            payloads.append(resp.read(50 * 1024 * 1024 + 1))
        year = window_end + 1
    return _merge_bls_windows(payloads), "application/json"


def _default_fetch(spec: ConnectorSpec) -> Tuple[bytes, str]:
    if spec.publisher_kind == "bls_v2_json" and spec.history_start_year:
        return _bls_windowed_fetch(spec)
    url = spec.url_template
    if spec.credential_env:
        # unified resolution chain (env -> local.env -> keychain); never logged
        key = _read_credential(spec.credential_env)
        url = url.replace("{key}", urllib.parse.quote(key, safe=""))
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host not in {h.lower() for h in spec.allowed_hosts}:
        raise HostNotAllowed("request host %s not in allowlist" % host)
    req = urllib.request.Request(url, headers={"User-Agent": "rmv2-connector/1.0",
                                               "Accept": ", ".join(spec.expected_content_types)})
    with urllib.request.urlopen(req, timeout=60) as resp:
        final_host = (urllib.parse.urlparse(resp.geturl()).hostname or "").lower()
        if final_host not in {h.lower() for h in spec.allowed_hosts}:
            raise HostNotAllowed("redirected to disallowed host %s" % final_host)
        data = resp.read(50 * 1024 * 1024 + 1)
        ct = resp.headers.get("Content-Type", "application/octet-stream")
    return data, ct


def _content_type_ok(spec: ConnectorSpec, content_type: str) -> bool:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    allowed = {c.split(";", 1)[0].strip().lower() for c in spec.expected_content_types}
    return (not allowed) or (normalized in allowed)


def run_connector(
    spec: ConnectorSpec,
    output_root,
    fetch: Optional[Callable[[ConnectorSpec], Tuple[bytes, str]]] = None,
    now: Optional[str] = None,
    stale_after_days: int = 180,
) -> Dict[str, Any]:
    output_root = Path(output_root)
    fetch = fetch or _default_fetch
    now_ts = now or _utc_now()
    retrieval_ts = now_ts
    receipt: Dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "connector_id": spec.connector_id,
        "legacy_id": spec.legacy_id,
        "canonical_id": spec.canonical_id,
        "url": spec.url_template,  # credential placeholder, never the filled url
        "retrieved_at": retrieval_ts,
        "status": "FAILED",
        "sha256": "",
        "bytes": 0,
        "content_type": "",
        "unchanged": False,
        "error": "",
    }
    result: Dict[str, Any] = {"receipt": receipt, "candidate": None, "normalized": None}

    try:
        data, content_type = fetch(spec)
    except HostNotAllowed as exc:
        receipt["error"] = "host not allowed: %s" % exc
        _write_receipt(output_root, spec, receipt)
        return result
    except Exception as exc:
        receipt["error"] = "%s: %s" % (type(exc).__name__, exc)
        _write_receipt(output_root, spec, receipt)
        return result

    receipt["content_type"] = content_type
    if not _content_type_ok(spec, content_type):
        receipt["error"] = "content type %s not allowed" % content_type
        _write_receipt(output_root, spec, receipt)
        return result

    try:
        normalized = parsers.parse(spec.publisher_kind, data)
    except parsers.ParseError as exc:
        receipt["error"] = "ParseError: %s" % exc
        _write_receipt(output_root, spec, receipt)
        return result  # last-known-good untouched; no raw written

    sha = _sha256(data)
    validation_ts = _utc_now() if now is None else now
    raw_path = output_root / _safe_relative(spec.raw_destination)

    unchanged = raw_path.exists() and _sha256(raw_path.read_bytes()) == sha
    if not unchanged:
        _atomic_write(raw_path, data)

    # stale determination against freshest available clock
    stale = False
    clock = normalized.provider_availability or normalized.coverage[1]
    cd = _period_to_date(clock) if clock else None
    if cd is not None:
        try:
            stale = (_parse_ts(now_ts) - cd).days > stale_after_days
        except Exception:
            stale = False

    cand = candidate.build_candidate(spec, normalized, sha, len(data), retrieval_ts, validation_ts, stale=stale)
    _atomic_write(output_root / "candidates" / (spec.connector_id + ".json"), _canonical_json(cand))

    receipt.update({
        "status": "SUCCESS_UNCHANGED" if unchanged else "SUCCESS",
        "sha256": sha, "bytes": len(data), "unchanged": unchanged, "error": "",
        "observation_count": normalized.count,
        "coverage_first": normalized.coverage[0], "coverage_last": normalized.coverage[1],
    })
    _write_receipt(output_root, spec, receipt)
    result["candidate"] = cand
    result["normalized"] = normalized
    return result


def _write_receipt(output_root: Path, spec: ConnectorSpec, receipt: Dict[str, Any]) -> None:
    _atomic_write(output_root / "receipts" / (spec.connector_id + ".json"), _canonical_json(receipt))
