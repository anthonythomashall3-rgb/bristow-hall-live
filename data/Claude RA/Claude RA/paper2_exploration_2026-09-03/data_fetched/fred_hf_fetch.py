"""Resumable fetch of every series in fred_hf_index_keep.csv (observations from 1960) into fred_daily/ fred_weekly/ (biweekly -> fred_weekly)."""
import os, json, urllib.request, urllib.parse, pandas as pd, time, sys
HOME=os.path.expanduser("~"); key=None
for line in open(HOME+"/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env"):
    if line.startswith("FRED_API_KEY="): key=line.strip().split("=",1)[1].strip().strip('"')
idx=pd.read_csv("fred_hf_index_keep.csv"); t0=time.time(); n=0; budget=float(sys.argv[1]) if len(sys.argv)>1 else 150
for _,r in idx.iterrows():
    d="fred_daily" if r.freq=="daily" else "fred_weekly"; f=f"{d}/{r.id}.csv"
    if os.path.exists(f): continue
    if time.time()-t0>budget: break
    try:
        u="https://api.stlouisfed.org/fred/series/observations?"+urllib.parse.urlencode(dict(series_id=r.id, api_key=key, file_type="json", observation_start="1960-01-01"))
        j=json.loads(urllib.request.urlopen(u, timeout=60).read()); df=pd.DataFrame(j["observations"])[["date","value"]]; df.to_csv(f, index=False); n+=1; time.sleep(0.7)
    except Exception as e: open("fetch_errors.log","a").write(f"{r.id}\t{str(e)[:100]}\n"); time.sleep(2)
done=sum(os.path.exists(f"{'fred_daily' if r.freq=='daily' else 'fred_weekly'}/{r.id}.csv") for _,r in idx.iterrows())
print(f"fetched {n} this run; {done}/{len(idx)} on disk; {round(time.time()-t0)}s")
