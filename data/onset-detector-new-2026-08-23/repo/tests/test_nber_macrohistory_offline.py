"""B-OFFLINE-4 — NBER Macrohistory fixed-layout .dat adapter.

The NBER Macrohistory .dat files are a fixed-column text format (4-char year,
right-justified period field, separator space, left-padded decimal value). Each
shortlist series lands under its OWN NBER_* id, NEVER aliased to a modern twin,
class RESEARCH/NEAR, frozen archival, out-of-sample validation scope only
(owner ruling carried by the batch). Counts are CH-R50's measured obs_count /
missing_count (research/nber_layout_v1.json), re-verified from the cache bytes.
"""
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import normalize  # noqa: E402
from live_data.rmv2_live.nber_macrohistory import (  # noqa: E402
    NberMacrohistoryDataError,
    parse_nber_macrohistory_dat,
)

CACHE_ROOT = os.path.join(
    str(PROJECT_ROOT), "research", "prefetch", "nber_macrohistory", "data",
)

# file_id -> (chapter, series_id, unit, rec_count, available, missing,
#             first_period, last_period)
SHORTLIST = {
    "m13002": ("13", "NBER_M13002", "PERCENT", 1380, 1380, 0,
               "1857-01-01", "1971-12-01"),
    "m01130a": ("01", "NBER_M01130A", "THOUSANDS OF GROSS TONS", 780, 780, 0,
                "1877-01-01", "1941-12-01"),
    "m01135a": ("01", "NBER_M01135A",
                "THOUSANDS OF LONG TONS PER AVERAGE WORKING DAY", 492, 492, 0,
                "1899-01-01", "1939-12-01"),
    "m03030": ("03", "NBER_M03030", "index (FRB freight carloadings)", 413, 413,
               0, "1919", "1953-04-01"),
    "m13001": ("13", "NBER_M13001", "PERCENT", 1368, 1367, 1,
               "1857-01-01", "1970-12-01"),
    "m06001a": ("06", "NBER_M06001A", "1919-100", 72, 66, 6,
                "1914-01-01", "1919-12-01"),
    "m06002b": ("06", "NBER_M06002B", "1957-1959=100", 540, 540, 0,
                "1919-01-01", "1963-12-01"),
}


def _body(file_id):
    chapter = SHORTLIST[file_id][0]
    path = os.path.join(CACHE_ROOT, chapter, "%s.dat" % file_id)
    with open(path, "rb") as handle:
        return handle.read()


def _config(file_id):
    _, series_id, unit = SHORTLIST[file_id][:3]
    return {
        "series_id": series_id,
        "unit": unit,
        "label": "NBER Macrohistory %s validation-scope-only" % series_id,
    }


@pytest.mark.parametrize("file_id", sorted(SHORTLIST))
def test_counts_match_ch_r50(file_id):
    (_, series_id, unit, rec, avail, miss, first, last) = SHORTLIST[file_id]
    obs = parse_nber_macrohistory_dat(_config(file_id), _body(file_id))
    assert all(o["series_id"] == series_id for o in obs)
    assert len(obs) == rec
    available = [o for o in obs if o["value_status"] == "actual"]
    missing = [o for o in obs if o["value_status"] == "unavailable"]
    assert len(available) == avail
    assert len(missing) == miss
    assert all(o["value"] is None for o in missing)
    assert all(o["value"] is not None for o in available)
    assert obs[0]["observation_period"] == first
    assert obs[-1]["observation_period"] == last
    assert all(o["unit"] == unit for o in obs)


def test_m03030_carries_the_single_annual_summary_row():
    obs = parse_nber_macrohistory_dat(_config("m03030"), _body("m03030"))
    annual = [o for o in obs if o["period_granularity"] == "annual"]
    monthly = [o for o in obs if o["period_granularity"] == "monthly"]
    assert len(annual) == 1
    assert annual[0]["observation_period"] == "1919"
    assert annual[0]["value"] == "108.0"  # published '108.' -> canonical
    assert len(monthly) == 412


def test_commercial_paper_1857_first_cell_value():
    obs = parse_nber_macrohistory_dat(_config("m13002"), _body("m13002"))
    first = obs[0]
    assert first["observation_period"] == "1857-01-01"
    # published '8.81000' -> shortest round-trip decimal
    assert first["value"] == "8.81"
    assert first["period_granularity"] == "monthly"


def test_call_money_trailing_missing_is_unavailable_not_dropped():
    obs = parse_nber_macrohistory_dat(_config("m13001"), _body("m13001"))
    last = obs[-1]
    assert last["observation_period"] == "1970-12-01"
    assert last["value"] is None
    assert last["value_status"] == "unavailable"


def test_deterministic_across_two_parses():
    a = parse_nber_macrohistory_dat(_config("m13002"), _body("m13002"))
    b = parse_nber_macrohistory_dat(_config("m13002"), _body("m13002"))
    assert a == b


def test_rejects_non_nber_series_id():
    cfg = _config("m13002")
    cfg["series_id"] = "ICSA"  # a modern twin id must be refused
    with pytest.raises(NberMacrohistoryDataError):
        parse_nber_macrohistory_dat(cfg, _body("m13002"))


def test_rejects_empty_body():
    with pytest.raises(NberMacrohistoryDataError):
        parse_nber_macrohistory_dat(_config("m13002"), b"")


def test_rejects_non_chronological_rows():
    body = b"1900    1 5.0\n1899    1 4.0\n"
    with pytest.raises(NberMacrohistoryDataError):
        parse_nber_macrohistory_dat(_config("m13002"), body)


def test_rejects_bad_month():
    body = b"1900   13 5.0\n"
    with pytest.raises(NberMacrohistoryDataError):
        parse_nber_macrohistory_dat(_config("m13002"), body)


def test_rejects_all_missing_series():
    body = b"1900    1 .\n1900    2 .\n"
    with pytest.raises(NberMacrohistoryDataError):
        parse_nber_macrohistory_dat(_config("m13002"), body)


def test_normalize_stamps_source_and_mode():
    src = {
        "adapter": "nber_macrohistory_dat",
        "endpoint": "https://data.nber.org/databases/macrohistory/rectdata/13/m13002.dat",
        "information_set_mode": "substituted_diagnostic",
        "method_version": "nber_macrohistory_offline.v1",
        "publisher": "National Bureau of Economic Research",
        "publisher_release_clock": "closed historical compilation; never revised",
        "rights_status": "public_domain_research",
        "series": _config("m13002"),
        "source_id": "nber_macrohistory_m13002",
        "value_status": "actual",
    }
    records = normalize(src, _body("m13002"), "2026-08-06T00:00:00Z")
    assert records
    for record in records:
        assert record["information_set_mode"] == "substituted_diagnostic"
        assert record["source_id"] == "nber_macrohistory_m13002"
        assert record["series_id"] == "NBER_M13002"
        assert record["value_status"] in ("actual", "unavailable")
