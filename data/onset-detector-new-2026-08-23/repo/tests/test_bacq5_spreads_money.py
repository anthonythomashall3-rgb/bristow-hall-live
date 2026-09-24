"""B-ACQ-5 — four mechanisms (term structure, funding spreads, money & credit,
retail control) landed as offline-current frozen snapshots on the PROVEN
fred_json_api shape (mirrors B-OFFLINE-2 / B-ACQ-3 / B-ACQ-4).

10 series land; 14 fetched candidates were already present in the store
(clobber-proof skip) and MARTSSM44X72USS is skip-and-recorded (§5.5, not a
valid FRED id). §22.4: acquisition only, not admitted to any channel. Step 3:
the index_v1.py:26 curve gauge stays EXCLUDED from the headline (a §22.4
parameter, untouched). Owner ruling 2026-08-08: current_revised, BARRED from
any as-of / real-time claim.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "live_data/config/sources.v1.json"
CACHE = ROOT / "research/prefetch/bacq5"

sys.path.insert(0, str(ROOT / "live_data"))

LANDED = {
    "fred_bogmbase_api_current_offline": "BOGMBASE",
    "fred_dcpn3m_api_current_offline": "DCPN3M",
    "fred_dgs1_api_current_offline": "DGS1",
    "fred_dgs3mo_api_current_offline": "DGS3MO",
    "fred_dprime_api_current_offline": "DPRIME",
    "fred_m1sl_api_current_offline": "M1SL",
    "fred_nonborres_api_current_offline": "NONBORRES",
    "fred_t10yff_api_current_offline": "T10YFF",
    "fred_tedrate_api_current_offline": "TEDRATE",
    "fred_totresns_api_current_offline": "TOTRESNS",
}


def _sources():
    return {s["source_id"]: s for s in json.load(open(CFG))["sources"]}


def test_bacq5_landed_sources_present_and_shaped():
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
        # owner ruling 2026-08-08 bar recorded in the label
        assert "BARRED" in s["label"]


def test_bacq5_cached_bytes_parse_ascending_distinct():
    from rmv2_live.adapters import normalize
    srcs = _sources()
    for source_id, series_id in LANDED.items():
        body = (CACHE / (series_id + ".obs.json")).read_bytes()
        recs = normalize(srcs[source_id], body, "2026-08-08T00:00:00Z")
        periods = sorted(r["observation_period"] for r in recs
                         if r["observation_period"])
        assert len(recs) > 100, "%s only %d recs" % (series_id, len(recs))
        assert periods == sorted(set(periods))
