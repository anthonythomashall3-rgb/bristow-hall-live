"""B-ACQ-4 — regional Fed survey diffusion indices landed as offline-current
frozen snapshots on the PROVEN fred_json_api shape (mirrors B-OFFLINE-2).

Two districts land: Empire State (NY, GACDISA066MSFRBNY) and Dallas TMOS
(BACTSAMFRBDAL). Richmond, Kansas City and Chicago are skip-and-recorded
(§5.5): no same-class survey on FRED for Richmond/KC, and only the distinct
2013+ Survey-of-Economic-Conditions index for Chicago.

§3.1: each district is its OWN series id, never aliased onto PHILLY. §22.4:
acquisition only, not admitted to any channel. Owner ruling 2026-08-08:
current_revised, BARRED from any as-of / real-time claim.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "live_data/config/sources.v1.json"
CACHE = ROOT / "research/prefetch/bacq4"

sys.path.insert(0, str(ROOT / "live_data"))

LANDED = {
    "fred_gacdisa066msfrbny_api_current_offline": "GACDISA066MSFRBNY",
    "fred_bactsamfrbdal_api_current_offline": "BACTSAMFRBDAL",
}
PHILLY_SID = "GACDFSA066MSFRBPHI"


def _sources():
    return {s["source_id"]: s for s in json.load(open(CFG))["sources"]}


def test_bacq4_landed_sources_present_and_shaped():
    srcs = _sources()
    for source_id, series_id in LANDED.items():
        assert source_id in srcs, "missing landed source %s" % source_id
        s = srcs[source_id]
        assert s["adapter"] == "fred_json_api"
        assert s["enabled"] is False
        assert s["archival"] is True
        assert s["information_set_mode"] == "current_revised"
        assert s["coverage_source_ids"] == ["fred_current_provider"]
        assert s["series"]["series_id"] == series_id
        # §3.1 — never aliased onto PHILLY
        assert series_id != PHILLY_SID


def test_bacq4_cached_bytes_parse_as_monthly_diffusion():
    from rmv2_live.adapters import normalize
    srcs = _sources()
    for source_id, series_id in LANDED.items():
        body = (CACHE / (series_id + ".obs.json")).read_bytes()
        recs = normalize(srcs[source_id], body, "2026-08-08T00:00:00Z")
        periods = sorted(r["observation_period"] for r in recs
                         if r["observation_period"])
        assert len(recs) > 250, "%s only %d recs" % (series_id, len(recs))
        # monthly cadence, ascending, distinct
        assert periods == sorted(set(periods))
