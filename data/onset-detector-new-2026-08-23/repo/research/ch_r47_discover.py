#!/usr/bin/env python3
"""CH-R47 discovery: enumerate daily-cadence series in store, tag category. read-only."""
import sys,re,json
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,"live_data")
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore
from datetime import date

PR=Path(".").resolve()
cfgp=PR/"live_data/config/sources.v1.json"
load_env_file(cfgp.parent/"local.env"); cfg=load_config(cfgp)
st=LiveStore(PR,cfg); st.initialize()
heads=st.all_source_heads()
VINT=re.compile(r"vintage|deep|asof|archive|_alfred|snapshot",re.I)

def pdate(s):
    s=str(s).strip()
    m=re.match(r"^(\d{4})-(\d{2})-(\d{2})$",s)
    if m: return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
    return None

# candidate daily series ids of interest
KEY={
 'curve':['DGS10','DGS2','DGS3MO','DGS1','DGS5','DGS30','DGS1MO','DGS6MO','DGS3','DGS7','DGS20'],
 'spread':['T10Y2Y','T10Y3M','T10YFF','T1YFFM','BAA10Y','AAA10Y'],
 'credit':['BAMLH0A0HYM2','BAMLC0A0CM','BAMLH0A0HYM2EY','BAMLHYH0A0HYM2TRIV'],
 'vix':['VIXCLS','VXOCLS','OVXCLS'],
 'oil':['DCOILWTICO','DCOILBRENTEU'],
 'dollar':['DTWEXBGS','DTWEXAFEGS','DTWEXM','DTWEXB'],
 'cp':['DCPF3M','DCPN3M','DCPF1M','DCPN30','RIFSPPFAAD90NB'],
 'ff':['DFF','DFEDTARU'],
 'stock':['SP500','DJIA','NASDAQCOM','WILL5000INDFC'],
}
want={}
for cat,ids in KEY.items():
    for i in ids: want[i]=cat

rows=[]
for sid,h in heads.items():
    if VINT.search(sid): continue
    try: norm=st.read_normalized(h["normalized_sha256"])
    except Exception as e: continue
    # gather series present
    per=defaultdict(list)
    for r in norm.get("records",[]):
        if r.get("information_set_mode")!="current_revised": continue
        si=r.get("series_id")
        d=pdate(r.get("observation_period"))
        if d is None: continue
        try: fv=float(r.get("value"))
        except: continue
        per[si].append((d,fv))
    for si,vals in per.items():
        if si in want and len(vals)>50:
            ds=sorted(vals)
            # median spacing
            gaps=[(ds[k][0]-ds[k-1][0]).days for k in range(1,len(ds))]
            gaps.sort(); med=gaps[len(gaps)//2] if gaps else None
            rows.append((want[si],si,sid,len(vals),ds[0][0].isoformat(),ds[-1][0].isoformat(),med))

rows.sort()
out=open("research/ch_r47_daily_candidates.txt","w")
out.write(f"{'cat':8} {'series':14} {'source':30} {'n':>7} {'start':12} {'end':12} {'medgap':>6}\n")
for r in rows:
    out.write(f"{r[0]:8} {r[1]:14} {r[2]:30} {r[3]:>7} {r[4]:12} {r[5]:12} {str(r[6]):>6}\n")
out.close()
print(f"found {len(rows)} daily-series/source rows; categories:", sorted(set(r[0] for r in rows)))
