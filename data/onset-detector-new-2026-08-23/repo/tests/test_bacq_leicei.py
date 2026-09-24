"""B-ACQ-LEI-CEI — Conference Board LEI/CEI benchmark components landed as
offline-current frozen snapshots on the PROVEN fred_json_api shape (mirrors
B-OFFLINE-2 / B-ACQ-3 / B-ACQ-4 / B-ACQ-5).

5 series land as current_revised lanes:
  ACOGNO   LEI new orders, consumer goods (closest free proxy)
  AWHAEMAN LEI avg weekly hours mfg, all-employee basis (complements present AWHMAN)
  PAYEMS   CEI payroll employment (previously only archive_snapshot_asof vintage lanes)
  SP500    LEI S&P 500 (§3.1: NOT NASDAQ; FRED-free rights-limited ~10yr history)
  UMCSENT  LEI consumer-expectations proxy (previously only vintage lanes)

Clobber-proof skip (already present in active snapshot): AWHMAN, CMRMTSPL,
INDPRO, NEWORDER, W875RX1. Licensed/not-landed: NAPMNOI (ISM New Orders, HTTP
400, ISM-proprietary), Leading Credit Index (CB proprietary, no free FRED id).
§22.4: acquisition only, not admitted to any channel (landing PAYEMS does NOT
admit it as a member). Owner ruling 2026-08-08: current_revised, BARRED from any
as-of / real-time claim.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "live_data/config/sources.v1.json"
CACHE = ROOT / "research/prefetch/bacq_leicei"

sys.path.insert(0, str(ROOT / "live_data"))

LANDED = {
    "fred_acogno_api_current_offline": "ACOGNO",
    "fred_awhaeman_api_current_offline": "AWHAEMAN",
    "fred_payems_api_current_offline": "PAYEMS",
    "fred_sp500_api_current_offline": "SP500",
    "fred_umcsent_api_current_offline": "UMCSENT",
}


def _sources():
    return {s["source_id"]: s for s in json.load(open(CFG))["sources"]}


def test_bacq_leicei_landed_sources_present_and_shaped():
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


def test_bacq_leicei_cached_bytes_parse_ascending_distinct():
    from rmv2_live.adapters import normalize
    srcs = _sources()
    for source_id, series_id in LANDED.items():
        body = (CACHE / (series_id + ".obs.json")).read_bytes()
        recs = normalize(srcs[source_id], body, "2026-08-08T00:00:00Z")
        periods = sorted(r["observation_period"] for r in recs
                         if r["observation_period"])
        assert len(recs) > 100, "%s only %d recs" % (series_id, len(recs))
        assert periods == sorted(set(periods))
