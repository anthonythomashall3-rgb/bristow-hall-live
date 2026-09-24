"""Enumerate the most-popular daily and weekly FRED series (search endpoint, frequency filter), keep those with observations
starting by 1995 (>=3 recessions covered), write an index. Key read from local.env; never printed."""
import os, json, urllib.request, urllib.parse, pandas as pd, time
HOME=os.path.expanduser("~"); key=None
for line in open(HOME+"/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env"):
    if line.startswith("FRED_API_KEY="): key=line.strip().split("=",1)[1].strip().strip('"')
rows=[]
for freq in ["daily","weekly","biweekly"]:
    for off in [0,1000,2000,3000,4000]:
        u="https://api.stlouisfed.org/fred/tags/series?"+urllib.parse.urlencode(dict(tag_names=f"{freq};usa", order_by="popularity", sort_order="desc", limit=1000, offset=off, api_key=key, file_type="json"))
        try: j=json.loads(urllib.request.urlopen(u, timeout=90).read())
        except Exception as e: print(freq, off, "ERR", str(e)[:80]); break
        ss=j.get("seriess",[]); 
        for s in ss: rows.append(dict(id=s["id"], title=s["title"], freq=freq, start=s["observation_start"], end=s["observation_end"], units=s["units_short"], sa=s["seasonal_adjustment_short"], pop=s["popularity"]))
        print(freq, off, len(ss)); 
        if len(ss)<1000: break
        time.sleep(0.5)
df=pd.DataFrame(rows).drop_duplicates("id"); df.to_csv("fred_hf_index_all.csv", index=False)
keep=df[(df.start<="1995-12-31")&(df.end>="2024-01-01")]
keep.to_csv("fred_hf_index_keep.csv", index=False)
print("total", len(df), "kept (start<=1995, live)", len(keep)); print(keep.freq.value_counts().to_dict())
