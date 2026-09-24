"""B-ACQ-3 — five orthogonal FRED categories landed as offline-current frozen
snapshots on the PROVEN fred_json_api shape (mirrors B-ACQ-4 / B-OFFLINE-2).

CH1 measured effective-N per channel ~1.6-2.4 of 4; more of the same buys
nothing. These categories are mechanically related to downturns and absent
from the model. §6.1 caps SHAPES not sources; every landed source here is the
already-proven fred_json_api shape (zero new shapes). §3.1 each series its own
id, never aliased. §22.4 acquisition only, admitted to no channel. Owner ruling
2026-08-08: current_revised, BARRED from any as-of / real-time claim.

7 candidates were already present (AMTMNO, BUSLOANS, DGORDER, ISRATIO, JTSQUR,
NEWORDER, TDSP) and are not re-landed; category d (inventory/orders) added 0 new.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "live_data/config/sources.v1.json"
CACHE = ROOT / "research/prefetch/bacq3"

sys.path.insert(0, str(ROOT / "live_data"))

# source_id -> (series_id, category, min_records)
LANDED = {
    "fred_drtscilm_api_current_offline": ("DRTSCILM", "a_credit_quantity", 140),
    "fred_drtscis_api_current_offline": ("DRTSCIS", "a_credit_quantity", 140),
    "fred_drtsclcc_api_current_offline": ("DRTSCLCC", "a_credit_quantity", 120),
    "fred_totbkcr_api_current_offline": ("TOTBKCR", "a_credit_quantity", 2700),
    "fred_jtshir_api_current_offline": ("JTSHIR", "b_labor_flows", 300),
    "fred_jtsldr_api_current_offline": ("JTSLDR", "b_labor_flows", 300),
    "fred_jtstsr_api_current_offline": ("JTSTSR", "b_labor_flows", 300),
    "fred_coralacbs_api_current_offline": ("CORALACBS", "c_corporate_distress", 160),
    "fred_corblacbs_api_current_offline": ("CORBLACBS", "c_corporate_distress", 160),
    "fred_dralacbs_api_current_offline": ("DRALACBS", "c_corporate_distress", 160),
    "fred_drblacbs_api_current_offline": ("DRBLACBS", "c_corporate_distress", 150),
    "fred_drcclacbs_api_current_offline": ("DRCCLACBS", "e_consumer_stress", 140),
    "fred_drsfrmacbs_api_current_offline": ("DRSFRMACBS", "e_consumer_stress", 140),
    "fred_fodsp_api_current_offline": ("FODSP", "e_consumer_stress", 170),
}


def _sources():
    return {s["source_id"]: s for s in json.load(open(CFG))["sources"]}


def test_bacq3_landed_sources_present_and_shaped():
    srcs = _sources()
    for source_id, (series_id, _cat, _n) in LANDED.items():
        assert source_id in srcs, "missing landed source %s" % source_id
        s = srcs[source_id]
        assert s["adapter"] == "fred_json_api", source_id
        assert s["enabled"] is False, source_id
        assert s["archival"] is True, source_id
        assert s["information_set_mode"] == "current_revised", source_id
        assert s["coverage_source_ids"] == ["fred_current_provider"], source_id
        assert s["series"]["series_id"] == series_id, source_id
        # §22.4 bar recorded in the label
        assert "BARRED from as-of" in s["label"], source_id


def test_bacq3_cached_bytes_parse_ascending_distinct():
    from rmv2_live.adapters import normalize
    srcs = _sources()
    for source_id, (series_id, _cat, min_n) in LANDED.items():
        body = (CACHE / (series_id + ".obs.json")).read_bytes()
        recs = normalize(srcs[source_id], body, "2026-08-08T00:00:00Z")
        periods = sorted(r["observation_period"] for r in recs
                         if r["observation_period"])
        assert len(recs) >= min_n, "%s only %d recs" % (series_id, len(recs))
        assert periods == sorted(set(periods)), series_id  # ascending, distinct
