#!/usr/bin/env python3
"""CH-R100 step 1: ALFRED vintagedates count curve. Read-only. No store write."""
import json, re, time, urllib.request, urllib.parse, os

KEY=None
for line in open("live_data/config/local.env"):
    m=re.match(r'\s*(export\s+)?FRED_API_KEY\s*=\s*["\']?([A-Za-z0-9]+)',line)
    if m: KEY=m.group(2)
assert KEY

SERIES=["NFCI","ICSA","IURSA","HOUST","PERMIT"]
FLOORS=["2015-01-01","2009-01-01","2000-01-01"]
DEEP_MAX="2019-12-31"
UA="RecessionMonitorV2/1.0 publisher-direct local collector CH-R100 probe"

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    t=time.time()
    with urllib.request.urlopen(req,timeout=120) as r:
        body=r.read()
    return body, time.time()-t

out={}
for s in SERIES:
    url="https://api.stlouisfed.org/fred/series/vintagedates?series_id=%s&api_key=%s&file_type=json&limit=10000"%(s,KEY)
    body,dt=get(url)
    d=json.loads(body)
    vds=d.get("vintage_dates",[])
    rec={"vintagedates_bytes":len(body),"vintagedates_fetch_s":round(dt,3),
         "total_vintages":len(vds),"earliest":vds[0] if vds else None,"latest":vds[-1] if vds else None,
         "windows":{}}
    for f in FLOORS:
        inwin=[v for v in vds if f<=v<=DEEP_MAX]
        rec["windows"][f]={"count":len(inwin),"first":inwin[0] if inwin else None,"last":inwin[-1] if inwin else None}
    out[s]=rec
    print(s,"total=%d"%len(vds),"2015=%d 2009=%d 2000=%d"%(rec["windows"]["2015-01-01"]["count"],rec["windows"]["2009-01-01"]["count"],rec["windows"]["2000-01-01"]["count"]),"fetch=%.2fs"%dt)

json.dump(out,open("research/alfred_cost/counts.json","w"),indent=2)
print("WROTE research/alfred_cost/counts.json")
