import json, urllib.parse, sys
from pathlib import Path
sys.path.insert(0,".")
from live_data.rmv2_live.config import load_config
from live_data.rmv2_live.store import LiveStore
cfg=load_config(Path("live_data/config/sources.v1.json"))
store=LiveStore(Path("."),cfg)
def fsid(s):
    ser=s.get("series")
    if isinstance(ser,dict) and ser.get("series_id"): return str(ser["series_id"]).upper()
    qs=urllib.parse.parse_qs(urllib.parse.urlparse(s.get("endpoint","")).query)
    for k in ("series_id","id"):
        if qs.get(k): return str(qs[k][0]).upper()
    return None
VINT={"fred_json_api_vintages","fred_json_api_vintages_deep"}
# series -> list of (source_id, adapter)
from collections import defaultdict
by_series=defaultdict(list)
for s in cfg["sources"]:
    f=fsid(s)
    if f: by_series[f].append((s["source_id"],s["adapter"]))
SERIES=["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU",
 "GACDFSA066MSFRBPHI","NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS",
 "PERMIT","HOUST","UMCSENT","W875RX1"]
def measure_source(sid):
    try:
        head=store.read_source_head(sid)
    except Exception as e:
        return None
    d=head["normalized_sha256"]
    p=store.root/"normalized"/"sha256"/d[:2]/(d+".json")
    obj=json.loads(p.read_text())
    recs=obj.get("records",[])
    ps=[r.get("observation_period") for r in recs if r.get("observation_period")]
    modes=set(r.get("information_set_mode") for r in recs)
    ps=[x for x in ps if x]
    if not ps: return {"source_id":sid,"n":0}
    return {"source_id":sid,"n":len(ps),"min":min(ps),"max":max(ps),"modes":sorted(m for m in modes if m)}
out={}
for ser in SERIES:
    cands=[(sid,ad) for sid,ad in by_series.get(ser,[]) if ad not in VINT]
    rows=[]
    for sid,ad in cands:
        m=measure_source(sid)
        if m: m["adapter"]=ad; rows.append(m)
    # earliest-min source = the byte-floor for current_revised
    rows=[r for r in rows if r.get("n")]
    best=min(rows,key=lambda r:r["min"]) if rows else None
    out[ser]={"candidates":rows,"floor":best["min"] if best else None,
              "floor_source":best["source_id"] if best else None,
              "max":best["max"] if best else None}
json.dump(out,open("research/ext1948/series_floors.json","w"),indent=1,default=str)
for ser in SERIES:
    o=out[ser]
    print(f"{ser:20s} floor={o['floor']} max={o['max']} src={o['floor_source']} ncand={len(o['candidates'])}")
