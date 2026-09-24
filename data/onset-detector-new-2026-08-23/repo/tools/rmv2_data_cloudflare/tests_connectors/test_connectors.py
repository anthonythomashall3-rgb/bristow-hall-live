"""TDD suite for the legacy-to-canonical candidate connectors.

Written failing-first. Covers per the Phase-2 connector contract:
valid, malformed(HTML), truncated, wrong-type, redirect/host-allowlist,
duplicate, stale, atomicity, last-known-good, identity transition, and
candidate flags (candidate_only / reviewed=false / scientific_admission=false /
public_eligible=false). Deterministic: publisher responses are committed
fixtures and the network fetch is dependency-injected.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from rmv2_connectors import parsers, registry, candidate, engine

FIX = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> bytes:
    return (FIX / name).read_bytes()


# ---------------------------------------------------------------- parsers

def test_parse_oecd_sdmx_valid():
    n = parsers.parse("oecd_sdmx_json", _read("oecd_cli_nor_valid.json"))
    assert n.count >= 1
    assert n.latest_value is not None
    assert n.coverage[0] <= n.coverage[1]
    # amplitude-adjusted must NOT be silently accepted: this fixture is NOR
    assert n.provider_availability  # SDMX 'prepared' clock present


def test_parse_bls_v2_valid_value_parity():
    n = parsers.parse("bls_v2_json", _read("bls_lns13008396_valid.json"))
    assert n.count >= 1
    # BLS LNS13008396 2025-M12 == 2289 (proven equal to canonical UEMPLT5)
    dec = dict(n.observations)
    assert dec.get("2025-M12") == 2289.0


def test_parse_fred_api_valid():
    n = parsers.parse("fred_api_json", _read("fred_lautosa_valid.json"))
    assert n.count >= 1
    assert n.latest_value is not None


@pytest.mark.parametrize("kind", ["oecd_sdmx_json", "bls_v2_json", "fred_api_json"])
def test_parse_rejects_html(kind):
    with pytest.raises(parsers.ParseError):
        parsers.parse(kind, _read("malformed_html.txt"))


@pytest.mark.parametrize("kind", ["oecd_sdmx_json", "bls_v2_json", "fred_api_json"])
def test_parse_rejects_truncated(kind):
    with pytest.raises(parsers.ParseError):
        parsers.parse(kind, _read("truncated.json"))


@pytest.mark.parametrize("kind", ["oecd_sdmx_json", "bls_v2_json", "fred_api_json"])
def test_parse_rejects_empty(kind):
    with pytest.raises(parsers.ParseError):
        parsers.parse(kind, b"")


def test_parse_rejects_trailing_garbage_after_valid_json():
    # regression: a valid FRED object followed by an appended proxy error / HTML
    # must NOT be accepted as complete data (was a raw_decode bypass).
    good = _read("fred_lautosa_valid.json").rstrip()
    poisoned = good + b"<html>proxy error</html>"
    with pytest.raises(parsers.ParseError):
        parsers.parse("fred_api_json", poisoned)
    # but trailing whitespace only is fine
    parsers.parse("fred_api_json", good + b"\n\n  ")


def test_parse_bls_rejects_missing_status():
    body = json.dumps({"Results": {"series": [{"seriesID": "X", "data": [{"year": "2025", "period": "M01", "value": "1"}]}]}}).encode()
    with pytest.raises(parsers.ParseError):
        parsers.parse("bls_v2_json", body)


def test_parse_bls_dash_is_unavailable_not_zero():
    body = json.dumps({"status": "REQUEST_SUCCEEDED", "Results": {"series": [{"seriesID": "X",
        "data": [{"year": "2025", "period": "M10", "value": "-"},
                 {"year": "2025", "period": "M11", "value": "3.5"}]}]}}).encode()
    n = parsers.parse("bls_v2_json", body)
    dec = dict(n.observations)
    assert dec["2025-M10"] is None       # unavailable stays unavailable
    assert dec["2025-M11"] == 3.5


def test_engine_bls_window_merge_concatenates_series():
    def win(sid, rows):
        return json.dumps({"status": "REQUEST_SUCCEEDED", "Results": {"series": [{"seriesID": sid, "data": rows}]}}).encode()
    w1 = win("LNS13008396", [{"year": "1948", "period": "M01", "value": "1"}])
    w2 = win("LNS13008396", [{"year": "2025", "period": "M12", "value": "2289"}])
    merged = engine._merge_bls_windows([w1, w2])
    n = parsers.parse("bls_v2_json", merged)
    assert n.count == 2
    assert n.coverage == ("1948-M01", "2025-M12")


def test_engine_bls_window_merge_fails_closed_on_bad_window():
    ok = json.dumps({"status": "REQUEST_SUCCEEDED", "Results": {"series": [{"seriesID": "X", "data": []}]}}).encode()
    bad = json.dumps({"status": "REQUEST_NOT_PROCESSED", "Results": {}}).encode()
    with pytest.raises(Exception):
        engine._merge_bls_windows([ok, bad])


# ---------------------------------------------------------------- registry

def test_registry_resolved_connectors():
    ids = {c.canonical_id for c in registry.CONNECTORS}
    assert ids == {"USA_OECD_CLI_NOR", "UEMPLT5", "AHETPI", "CPROFIT", "LAUTOSA",
                   "IPG3361T3S", "CMRMTSPL", "GACDFSA066MSFRBPHI", "CE16OV"}
    legacy = {c.legacy_id for c in registry.CONNECTORS}
    # A466RX1Q020SBEA stays unresolved -> never a connector
    assert "A466RX1Q020SBEA" not in legacy
    # the Philly connector supersedes two legacy ids (GACDISA... and the PHIL alias)
    assert registry.get("fred_gacdfsa066msfrbphi").legacy_id == "GACDISA066MSFRBPHI"


def test_registry_identity_transitions_present():
    for c in registry.CONNECTORS:
        assert c.legacy_id
        assert c.canonical_id
        assert c.identity_evidence, "each connector must carry legacy->canonical evidence"
        assert c.originating_publisher
        assert c.rights_status


def test_registry_legacy_mnemonics_correct():
    m = {c.canonical_id: c.legacy_id for c in registry.CONNECTORS}
    assert m["UEMPLT5"] == "LNS13008396"
    assert m["AHETPI"] == "CES0500000008"
    assert m["CPROFIT"] == "CORPPROFIT"
    assert m["LAUTOSA"] == "AUTOSTOTALSA"
    assert m["USA_OECD_CLI_NOR"] == "USALOLITONOSTSAMEI"


# ---------------------------------------------------------------- candidate

def test_candidate_flags_are_conservative():
    spec = registry.get("bls_uemplt5")
    n = parsers.parse("bls_v2_json", _read("bls_lns13008396_valid.json"))
    raw = _read("bls_lns13008396_valid.json")
    doc = candidate.build_candidate(spec, n, hashlib.sha256(raw).hexdigest(), len(raw),
                                    retrieval_ts="2026-08-01T00:00:00Z", validation_ts="2026-08-01T00:00:01Z")
    assert doc["schema_version"] == "recession-monitor-v2.feed-discovery-spec.v1"
    assert doc["candidate_status"]["candidate_only"] is True
    assert doc["candidate_status"]["reviewed"] is False
    assert doc["candidate_status"]["scientific_admission"] is False
    assert doc["candidate_status"]["public_eligible"] is False
    assert doc["activation"]["scientific_effect"] == "none"
    # separate clocks retained
    for clock in ("observation_latest", "provider_availability", "retrieval", "validation", "release_schedule"):
        assert clock in doc["clocks"]
    # identity transition recorded, superseding (not deleting) the legacy malformed source
    assert doc["identity_transition"]["legacy_id"] == "LNS13008396"
    assert doc["identity_transition"]["canonical_id"] == "UEMPLT5"
    assert doc["identity_transition"]["legacy_status"]


# ---------------------------------------------------------------- engine

def _fetch_ok(name, ct):
    def _f(spec):
        return _read(name), ct
    return _f


def test_engine_success_writes_raw_receipt_candidate(tmp_path):
    spec = registry.get("bls_uemplt5")
    res = engine.run_connector(spec, tmp_path, fetch=_fetch_ok("bls_lns13008396_valid.json", "application/json"),
                               now="2026-08-01T00:00:00Z")
    assert res["receipt"]["status"] == "SUCCESS"
    raw_path = tmp_path / spec.raw_destination
    assert raw_path.exists()
    assert res["receipt"]["sha256"] == hashlib.sha256(raw_path.read_bytes()).hexdigest()
    assert (tmp_path / "receipts" / (spec.connector_id + ".json")).exists()
    assert (tmp_path / "candidates" / (spec.connector_id + ".json")).exists()


def test_engine_rejects_html_and_preserves_last_known_good(tmp_path):
    spec = registry.get("bls_uemplt5")
    # first: a good fetch establishes last-known-good
    engine.run_connector(spec, tmp_path, fetch=_fetch_ok("bls_lns13008396_valid.json", "application/json"),
                         now="2026-08-01T00:00:00Z")
    good = (tmp_path / spec.raw_destination).read_bytes()
    # then: a malformed HTML fetch must FAIL and must NOT overwrite the good bytes
    res = engine.run_connector(spec, tmp_path, fetch=_fetch_ok("malformed_html.txt", "text/html"),
                               now="2026-08-01T01:00:00Z")
    assert res["receipt"]["status"] == "FAILED"
    assert (tmp_path / spec.raw_destination).read_bytes() == good  # last-known-good intact


def test_engine_rejects_wrong_content_type(tmp_path):
    spec = registry.get("bls_uemplt5")
    res = engine.run_connector(spec, tmp_path, fetch=_fetch_ok("wrong_type.bin", "application/octet-stream"),
                               now="2026-08-01T00:00:00Z")
    assert res["receipt"]["status"] == "FAILED"


def test_engine_host_allowlist_blocks_exfil_redirect(tmp_path):
    spec = registry.get("bls_uemplt5")
    # simulate a fetch that resolved to a disallowed host (redirect/exfil)
    def _evil(spec):
        raise engine.HostNotAllowed("redirected to evil.example.com")
    res = engine.run_connector(spec, tmp_path, fetch=_evil, now="2026-08-01T00:00:00Z")
    assert res["receipt"]["status"] == "FAILED"
    assert "host" in res["receipt"]["error"].lower()


def test_engine_duplicate_identical_is_flagged_not_rewritten(tmp_path):
    spec = registry.get("bls_uemplt5")
    engine.run_connector(spec, tmp_path, fetch=_fetch_ok("bls_lns13008396_valid.json", "application/json"),
                         now="2026-08-01T00:00:00Z")
    mtime1 = (tmp_path / spec.raw_destination).stat().st_mtime_ns
    res = engine.run_connector(spec, tmp_path, fetch=_fetch_ok("bls_lns13008396_valid.json", "application/json"),
                               now="2026-08-01T02:00:00Z")
    assert res["receipt"]["status"] in ("SUCCESS_UNCHANGED", "SUCCESS")
    assert res["receipt"].get("unchanged") is True
    # unchanged identical bytes are not rewritten
    assert (tmp_path / spec.raw_destination).stat().st_mtime_ns == mtime1


def test_engine_stale_provider_clock_flagged_but_retained(tmp_path):
    spec = registry.get("bls_uemplt5")
    # now far in the future -> provider availability is stale
    res = engine.run_connector(spec, tmp_path, fetch=_fetch_ok("bls_lns13008396_valid.json", "application/json"),
                               now="2099-01-01T00:00:00Z", stale_after_days=90)
    assert res["candidate"]["clocks"]["stale"] is True
    assert res["receipt"]["status"] in ("SUCCESS", "SUCCESS_UNCHANGED")  # retained, not dropped


def test_engine_unavailable_stays_unavailable(tmp_path):
    spec = registry.get("bls_uemplt5")
    res = engine.run_connector(spec, tmp_path, fetch=_fetch_ok("malformed_html.txt", "text/html"),
                               now="2026-08-01T00:00:00Z")
    # a failed acquisition never fabricates observations
    assert res.get("candidate") is None or res["candidate"].get("observation_count", 0) == 0
    assert res["receipt"]["bytes"] == 0 or res["receipt"]["status"] == "FAILED"


def test_engine_atomicity_no_partial_on_parse_failure(tmp_path):
    spec = registry.get("bls_uemplt5")
    engine.run_connector(spec, tmp_path, fetch=_fetch_ok("truncated.json", "application/json"),
                         now="2026-08-01T00:00:00Z")
    # no raw file and no stray temp files left behind
    strays = list(tmp_path.rglob(".*.tmp"))
    assert strays == []
    assert not (tmp_path / spec.raw_destination).exists()
