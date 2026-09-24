import csv, json, datetime as dt
from pathlib import Path
D=Path("data_archive/current_revised_and_spatial")
def floor(path):
    lo=hi=None;n=0
    for r in csv.reader(open(path)):
        if r and r[0][:1].isdigit() and len(r)>1 and r[1] not in ("","."):
            try: d=dt.date(int(r[0][:4]),int(r[0][5:7]),int(r[0][8:10]))
            except: continue
            n+=1
            if lo is None or d<lo: lo=d
            if hi is None or d>hi: hi=d
    return (lo.isoformat() if lo else None, hi.isoformat() if hi else None, n)
# member -> series (BAAAAA derived from BAA & AAA)
SERIES=["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU",
 "GACDFSA066MSFRBPHI","NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS",
 "PERMIT","HOUST","UMCSENT","W875RX1"]
res={}
for s in SERIES:
    main=floor(D/f"{s}.csv")
    hp=D/"hist"/f"{s}.csv"
    hist=floor(hp) if hp.exists() else None
    res[s]={"main":{"min":main[0],"max":main[1],"n":main[2]},
            "hist":({"min":hist[0],"max":hist[1],"n":hist[2]} if hist else None)}
json.dump(res,open("research/ext1948/raw_floors.json","w"),indent=1)
for s in SERIES:
    r=res[s];m=r["main"];h=r["hist"]
    hs=f"  hist_min={h['min']}(n={h['n']})" if h else ""
    print(f"{s:20s} min={m['min']} max={m['max']} n={m['n']}{hs}")
