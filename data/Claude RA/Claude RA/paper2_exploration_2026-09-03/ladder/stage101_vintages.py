"""Stage 101: how far back does the first-print replay can be pushed?  ALFRED vintage
coverage for every series v10 uses, plus the weekly-claims family."""
import os, json, urllib.request, time
ENV=os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env")
KEY=[l.split("=",1)[1].strip().strip('"').strip("'") for l in open(ENV) if "FRED" in l.upper() and "=" in l][0]
SER=["UNRATE","HOUST","PERMIT","PAYEMS","INDPRO","ICSA","CCSA","IURSA","DTB6","VIXCLS","BAA10Y","DGS10","DGS1",
     "HOUST1F","USREC","GDPC1","UNEMPLOY","CLF16OV","UMCSENT"]
print("%-10s %-9s %-12s %-12s" % ("series","vintages","first vintage","last vintage"))
out={}
for s in SER:
    try:
        u=("https://api.stlouisfed.org/fred/series/vintagedates?series_id="+s+
           "&api_key="+KEY+"&file_type=json&limit=10000")
        j=json.load(urllib.request.urlopen(u,timeout=25))
        vd=j.get("vintage_dates",[])
        out[s]=vd
        print("%-10s %-9d %-12s %-12s" % (s,len(vd),vd[0] if vd else "-",vd[-1] if vd else "-"))
    except Exception as e:
        print("%-10s %s" % (s,"no vintages / error"))
    time.sleep(0.3)
json.dump({k:[v[0],v[-1],len(v)] for k,v in out.items()},
          open(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/ladder/stage101_vintages.json"),"w"),indent=1)
