"""B-RESV-PROVEN — §5.3 RED test for the two net-new reservation instances
landed on PROVEN shapes as offline-current frozen snapshots (§6.2, zero new
parser shapes):

  fred_recprousm156n_api_current_offline  RECPROUSM156N  (fred_json_api)
  census_eits_mwtsadv_current_offline     mwtsadv EITS   (census_api)

RED pre-land (both source_ids absent); GREEN post-land. §22.4 acquisition only,
NOT admitted to any channel. Owner ruling 2026-08-08: current_revised, BARRED
from any as-of / real-time claim. RECPROUSM156N is a target-trained recession
probability — carried strictly as an EXTERNAL COMPARATOR, never a construction
input (CLAUDE.md boundary).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "live_data/config/sources.v1.json"
CACHE = ROOT / "research/prefetch/bresv"
sys.path.insert(0, str(ROOT / "live_data"))

FRED_SID = "fred_recprousm156n_api_current_offline"
CENSUS_SID = "census_eits_mwtsadv_current_offline"


def _sources():
    return {s["source_id"]: s for s in json.load(open(CFG))["sources"]}


def test_bresv_landed_sources_present_and_shaped():
    srcs = _sources()
    assert FRED_SID in srcs, "missing landed source %s" % FRED_SID
    f = srcs[FRED_SID]
    assert f["adapter"] == "fred_json_api"
    assert f["enabled"] is False and f["archival"] is True
    assert f["information_set_mode"] == "current_revised"
    assert f["coverage_source_ids"] == ["fred_current_provider"]
    assert f["series"]["series_id"] == "RECPROUSM156N"
    assert "BARRED" in f["label"] and "COMPARATOR" in f["label"].upper()

    assert CENSUS_SID in srcs, "missing landed source %s" % CENSUS_SID
    c = srcs[CENSUS_SID]
    assert c["adapter"] == "census_api"
    assert c["enabled"] is False and c["archival"] is True
    assert c["information_set_mode"] == "current_revised"
    assert c["coverage_source_ids"] == ["census_mtis_mwts"]
    assert c["series"]["dataset"] == "mwtsadv"
    assert len(c["series"]["items"]) == 24
    assert "BARRED" in c["label"]


def test_bresv_cached_bytes_parse():
    from rmv2_live.adapters import normalize
    srcs = _sources()
    fr = normalize(srcs[FRED_SID],
                   (CACHE / "fred_current_api.body").read_bytes(),
                   "2026-08-08T00:00:00Z")
    assert len(fr) > 600  # monthly 1967-06..2026-06
    assert all(r["series_id"] == "RECPROUSM156N" for r in fr)

    cr = normalize(srcs[CENSUS_SID],
                   (CACHE / "census_economic_indicators_current_api.body").read_bytes(),
                   "2026-08-08T00:00:00Z")
    sids = {r["series_id"] for r in cr}
    assert len(sids) == 24
    assert all(s.startswith("CENSUS.EITS.MWTSADV.") for s in sids)
