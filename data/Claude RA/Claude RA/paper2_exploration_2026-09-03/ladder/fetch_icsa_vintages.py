"""Pull ICSA as first prints (each week's value as first published) from ALFRED, 2009->."""
import os, json, time, urllib.request
import pandas as pd
ENV=os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env")
KEY=[l.split("=",1)[1].strip().strip('"').strip("'") for l in open(ENV) if "FRED" in l.upper() and "=" in l][0]
OUT=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other")
u=("https://api.stlouisfed.org/fred/series/observations?series_id=ICSA&api_key="+KEY+
   "&file_type=json&realtime_start=2009-05-28&realtime_end=9999-12-31&output_type=2")
j=json.load(urllib.request.urlopen(u,timeout=90))
obs=j["observations"]
print("rows",len(obs),"cols",len(obs[0]) if obs else 0)
rows=[]
for o in obs:
    d=o["date"]
    vals=[(k,v) for k,v in o.items() if k.startswith("ICSA_") and v not in (".",None)]
    if not vals: continue
    vals.sort(key=lambda kv: kv[0])
    first_vint=vals[0][0].split("_")[1]; first_val=float(vals[0][1])
    last_val=float(vals[-1][1])
    rows.append((d,first_vint,first_val,last_val))
df=pd.DataFrame(rows,columns=["week","first_vintage","first_print","current"])
df.to_csv(OUT+"/icsa_first_vs_current.csv",index=False)
print(df.head(3).to_string()); print("weeks:",len(df),df.week.min(),"->",df.week.max())
r=(df.current/df.first_print-1)*100
print("revision of the weekly level, percent: mean %.3f  sd %.3f  |max| %.2f  >1%%: %d of %d"
      % (r.mean(),r.std(),r.abs().max(),(r.abs()>1).sum(),len(r)))
