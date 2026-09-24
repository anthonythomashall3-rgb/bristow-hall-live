import json,sys
sys.path.insert(0,"live_data")
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
from pathlib import Path
root=Path(".").resolve()
cfg=load_config(root/"live_data/config/sources.v1.json")
store=LiveStore(root,cfg); store.initialize()
for sid in ["fred_w875rx1_api_current","fred_w875rx1_api_vintages","fred_w875rx1_api_vintages_deep"]:
    h=store.read_source_head(sid)
    print("==",sid,"head?",bool(h))
    if not h: continue
    print("  head_keys",sorted(h.keys()))
    norm=store.read_normalized(h["normalized_sha256"])
    if isinstance(norm,dict):
        print("  norm_keys",sorted(norm.keys()))
        recs=norm.get("records",norm.get("observations"))
    else:
        recs=norm
    print("  n_records",len(recs) if recs else 0)
    if recs:
        r0=recs[0]
        print("  rec0_keys",sorted(r0.keys()) if isinstance(r0,dict) else type(r0))
        # distinct series ids
        sids=set(r.get("series_id") for r in recs if isinstance(r,dict))
        print("  distinct_series_ids", len(sids), list(sorted(sids))[:6])
