import json,sys
sys.path.insert(0,"live_data")
from pathlib import Path
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
root=Path(".").resolve()
cfg=load_config(root/"live_data/config/sources.v1.json")
store=LiveStore(root,cfg); store.initialize()
def summarize(sid):
    h=store.read_source_head(sid)
    if not h: return f"{sid}: NO HEAD"
    n=store.read_normalized(h["normalized_sha256"])
    recs=n["records"]
    series=sorted(set(r["series_id"] for r in recs))
    vints=sorted(s.split(".DEEPASOF")[1] for s in series if ".DEEPASOF" in s)
    # earliest observation across all vintages + earliest observation of earliest vintage
    allobs=[r["observation_period"] for r in recs if r["observation_period"]]
    earliest_obs=min(allobs) if allobs else None
    earliest_vintage=vints[0] if vints else None
    # obs range of earliest vintage lane
    ev_sid=f"{series[0].split('.DEEPASOF')[0]}.DEEPASOF{earliest_vintage}"
    evobs=[r["observation_period"] for r in recs if r["series_id"]==ev_sid and r["observation_period"]]
    return (f"{sid}: records={len(recs)} vintage_lanes={len(vints)} "
            f"vintage_range={earliest_vintage}..{vints[-1] if vints else None} "
            f"earliest_obs_any={earliest_obs} earliest_vintage_obs_range={min(evobs)}..{max(evobs)}")
for sid in ["fred_claimsx_fredmd_panel_vintages_deep","fred_cmrmtsplx_fredmd_panel_vintages_deep"]:
    print(summarize(sid))
# canonical frontiers unchanged (owner consequence #3):
for sid in ["fred_icsa_api_vintages_deep","fred_cmrmtspl_api_vintages_deep","fred_w875rx1_api_vintages_deep"]:
    print(summarize(sid))
