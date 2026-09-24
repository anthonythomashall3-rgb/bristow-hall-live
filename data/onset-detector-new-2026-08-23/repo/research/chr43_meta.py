import sys,re,json,time
sys.path.insert(0,"live_data")
from pathlib import Path
from collections import defaultdict
from datetime import date
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore
PR=Path(".").resolve()
cfgp=PR/"live_data/config/sources.v1.json"
load_env_file(cfgp.parent/"local.env"); cfg=load_config(cfgp)
st=LiveStore(PR,cfg); st.initialize()
heads=st.all_source_heads()
VINT=re.compile(r"vintage|deep|asof|archive|_alfred|snapshot",re.I)
kept=[sid for sid in heads if not VINT.search(sid)]
def pdate(s):
    s=str(s).strip()
    m=re.match(r"^(\d{4})-Q([1-4])$",s)
    if m: return date(int(m.group(1)),(int(m.group(2))-1)*3+1,1)
    m=re.match(r"^(\d{4})-(\d{2})-(\d{2})$",s)
    if m: return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
    m=re.match(r"^(\d{4})-(\d{2})$",s)
    if m: return date(int(m.group(1)),int(m.group(2)),1)
    m=re.match(r"^(\d{4})$",s)
    if m: return date(int(m.group(1)),1,1)
    return None
# per series pick richest source; store dates only (count) + label/unit + min/max
info=defaultdict(lambda:defaultdict(lambda:[0,None,None]))  # si->sid->[cnt,mn,mx]
label={};unit={}
t0=time.time()
for sid in kept:
    try: norm=st.read_normalized(heads[sid]["normalized_sha256"])
    except: continue
    for r in norm.get("records",[]):
        if r.get("information_set_mode")!="current_revised": continue
        si=r.get("series_id");
        if not si: continue
        try: float(r.get("value"))
        except: continue
        d=pdate(r.get("observation_period"))
        if d is None: continue
        e=info[si][sid]; e[0]+=1
        if e[1] is None or d<e[1]: e[1]=d
        if e[2] is None or d>e[2]: e[2]=d
        label.setdefault(si,r.get("label")); unit.setdefault(si,r.get("unit"))
import csv
w=csv.writer(open("research/chr43_series_meta.csv","w",newline=""))
w.writerow(["series_id","best_source","n","first","last","span_days","label","unit"])
for si,bys in info.items():
    best=max(bys,key=lambda s:bys[s][0]); cnt,mn,mx=bys[best]
    w.writerow([si,best,cnt,mn,mx,(mx-mn).days if mn and mx else "",(label.get(si) or "")[:80],unit.get(si) or ""])
print("series",len(info),"elapsed",round(time.time()-t0))
