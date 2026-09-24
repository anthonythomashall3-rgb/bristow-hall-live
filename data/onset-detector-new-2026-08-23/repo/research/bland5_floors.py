import sys, json
sys.path.insert(0,"live_data")
from pathlib import Path
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
ROOT=Path(".").resolve()
cfg=load_config(ROOT/"live_data/config/sources.v1.json")
store=LiveStore(ROOT,cfg); store.initialize()
BASES=["INDPRO","PAYEMS","UNRATE","HOUST","GDPC1","TCU","UMCSENT","PERMIT"]
PROBE={"INDPRO":"19270126","PAYEMS":"19550506","UNRATE":"19600315","HOUST":"19600721",
       "GDPC1":"19911204","TCU":"19961115","UMCSENT":"19980731","PERMIT":"19990817"}
heads=store.all_source_heads()
# find deep source ids per base
deep_sids={b:[] for b in BASES}
for sid in heads:
    low=sid.lower()
    if "vintages_deep" not in low and "deep" not in low: continue
    for b in BASES:
        if b.lower() in low:
            deep_sids[b].append(sid); break
out={}
for b in BASES:
    fl=None;ce=None;cnt=0;sids=deep_sids[b]
    for sid in sids:
        n=store.read_normalized(heads[sid]["normalized_sha256"])
        vs=set()
        for r in n.get("records",[]):
            s=r.get("series_id","")
            if ".DEEPASOF" in s: vs.add(s.split(".DEEPASOF")[1])
        vs={v for v in vs if v.isdigit()}
        cnt+=len(vs)
        if vs:
            mn=min(vs);mx=max(vs)
            fl=mn if fl is None or mn<fl else fl
            ce=mx if ce is None or mx>ce else ce
    out[b]={"deep_source_ids":sids,"distinct_vintages":cnt,"floor":fl,"ceil":ce,
            "probe_floor":PROBE[b],"pre2000_present":(fl is not None and fl<"20000101")}
print(json.dumps(out,indent=1))
