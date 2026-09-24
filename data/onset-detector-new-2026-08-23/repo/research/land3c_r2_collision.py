import json,sys,re,os
sys.path.insert(0,"live_data")
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
from rmv2_live import fredmd_panel as fp
from pathlib import Path
root=Path(".").resolve()
cfg=load_config(root/"live_data/config/sources.v1.json")
store=LiveStore(root,cfg); store.initialize()
DMIN,DMAX="20000101","20191231"

# enumerate fredmd panels
roots=["data_archive/additional_vintages/fred_md_official/extracted",
       "data_archive/additional_vintages/fred_md_official/current"]
panels=[]
for r in roots:
    for dp,_,fns in os.walk(r):
        for fn in fns:
            if fn.lower().endswith(".csv"): panels.append(os.path.join(dp,fn))
panels=sorted(panels)
# derived series ids per base, deep window only
derived={}
for base in ["W875RX1","CLAIMSx","CMRMTSPLx"]:
    ids=set()
    for p in panels:
        v=fp.vintage_yyyymmdd(p)
        if DMIN<=v<=DMAX:
            ids.add(f"{base}.DEEPASOF{v}")
    derived[base]=ids
    print(base,"deep-window vintages:",len(ids), "min",min(ids) if ids else None,"max",max(ids) if ids else None)

# existing store series ids
def store_series_ids(sid):
    h=store.read_source_head(sid)
    if not h: return set()
    n=store.read_normalized(h["normalized_sha256"])
    recs=n["records"]
    return set(r["series_id"] for r in recs)

existing=set()
for sid in ["fred_w875rx1_api_vintages_deep","fred_w875rx1_api_vintages",
            "fred_w875rx1_api_current"]:
    existing|=store_series_ids(sid)
print("existing W875 series ids in store:",len(existing))
for base in derived:
    coll=derived[base]&existing
    print(f"COLLISION {base}: {len(coll)}", list(sorted(coll))[:5])
# also global: any of derived in ALL heads? check by scanning all heads for these ids (cheap: only W875 matters)
json.dump({b:sorted(v) for b,v in derived.items()},open("research/land3c_r2_derived_ids.json","w"))
