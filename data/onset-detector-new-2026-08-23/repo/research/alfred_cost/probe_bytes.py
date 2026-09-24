#!/usr/bin/env python3
"""CH-R100 step 2: real bytes + records per window via ONE bounded wide-matrix
fetch per series (output_type=2, realtime 2000-01-01..2019-12-31). Column-filter
client-side to get EXACT record+cell counts at each window floor. Read-only."""
import json, re, time, urllib.request

KEY=None
for line in open("live_data/config/local.env"):
    m=re.match(r'\s*(export\s+)?FRED_API_KEY\s*=\s*["\']?([A-Za-z0-9]+)',line)
    if m: KEY=m.group(2)

SERIES=["NFCI","ICSA","IURSA","HOUST","PERMIT"]
FLOORS=["2015-01-01","2009-01-01","2000-01-01"]
DEEP_MAX="2019-12-31"
UA="RecessionMonitorV2/1.0 publisher-direct local collector CH-R100 probe"

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    t=time.time()
    with urllib.request.urlopen(req,timeout=300) as r:
        body=r.read()
    return body, time.time()-t

out={}
for s in SERIES:
    url=("https://api.stlouisfed.org/fred/series/observations?series_id=%s"
         "&api_key=%s&file_type=json&output_type=2"
         "&realtime_start=2000-01-01&realtime_end=2019-12-31")%(s,KEY)
    body,dt=get(url)
    payload=json.loads(body)
    obs=payload.get("observations",[])
    colre=re.compile(r"^"+re.escape(s)+r"_(\d{8})$")
    # collect vintage columns
    cols=set()
    for row in obs:
        for c in row:
            m=colre.match(c)
            if m: cols.add(c)
    # per-window: count vintages (cols) with vintage-date in window, and records (non-'.' cells)
    perwin={}
    for f in FLOORS:
        fcompact=f.replace("-","")
        wincols=[c for c in cols if fcompact<=colre.match(c).group(1)<=DEEP_MAX.replace("-","")]
        recs=0
        for row in obs:
            for c in wincols:
                v=row.get(c)
                if v is not None and v!=".":
                    recs+=1
        perwin[f]={"vintages":len(wincols),"records":recs,
                   "records_per_vintage":round(recs/len(wincols),1) if wincols else 0}
    out[s]={"raw_payload_bytes":len(body),"fetch_wall_s":round(dt,2),
            "reference_periods_rows":len(obs),"total_vintage_cols":len(cols),
            "windows":perwin}
    w=perwin
    print("%s bytes=%d fetch=%.1fs rows=%d cols=%d | recs 2015=%d 2009=%d 2000=%d"%(
        s,len(body),dt,len(obs),len(cols),
        w["2015-01-01"]["records"],w["2009-01-01"]["records"],w["2000-01-01"]["records"]))

json.dump(out,open("research/alfred_cost/bytes.json","w"),indent=2)
print("WROTE research/alfred_cost/bytes.json")
