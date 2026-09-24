import sys, os
sys.path.insert(0,"live_data")
from pathlib import Path
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
from rmv2_live import fredmd_panel as fp
ROOT=Path(".").resolve()
cfg=load_config(ROOT/"live_data/config/sources.v1.json")
store=LiveStore(ROOT,cfg); store.initialize()
# ALFRED W875RX1 deep head?
for sid in ["fred_w875rx1_api_vintages_deep","fred_w875rx1_api_vintages"]:
    h=store.read_source_head(sid)
    if h:
        n=store.read_normalized(h["normalized_sha256"])
        ids=sorted({r["series_id"] for r in n["records"] if r["series_id"].startswith("W875RX1.DEEPASOF")})
        vs=sorted(i.split(".DEEPASOF")[1] for i in ids)
        print(sid, "ndeepids", len(ids), "floor", vs[0] if vs else None, "ceil", vs[-1] if vs else None)
    else:
        print(sid, "ABSENT")
# FRED-MD panels in window
roots=["data_archive/additional_vintages/fred_md_official/extracted","data_archive/additional_vintages/fred_md_official/current"]
ps=[]
for r in roots:
    for dp,_,fns in os.walk(r):
        for fn in fns:
            if fn.lower().endswith(".csv"): ps.append(os.path.join(dp,fn))
inw=[]
for p in sorted(ps):
    try: v=fp.vintage_yyyymmdd(p)
    except Exception as e: print("BADNAME",p,e); continue
    if "20000101"<=v<="20191231": inw.append(v)
print("panels_total",len(ps),"in_window",len(inw),"vmin",inw[0] if inw else None,"vmax",inw[-1] if inw else None,"dups",len(inw)-len(set(inw)))
