import csv,re,json
from datetime import date
rows=list(csv.DictReader(open("research/chr43_series_meta.csv")))
def d(s):
    try: return date.fromisoformat(s)
    except: return None
def cad(r):
    try: return int(r["span_days"])/max(int(r["n"])-1,1)
    except: return 9999
# deterioration direction on the LEVEL.  good_sign=+1 higher=better, -1 higher=worse
UP_BAD=[r"unemploy",r"jobless",r"\bclaims\b",r"initial claims",r"continued claims",r"insured unemploy",
 r"delinqu",r"default",r"charge-?off",r"\bspread\b",r"financial stress",r"financial conditions",
 r"volatilit",r"\bvix\b",r"bankrupt",r"uncertainty",r"layoff",r"discouraged",r"part.time for economic",
 r"vacan(cy|t) rate",r"foreclos"]
DOWN_BAD=[r"payroll",r"all employees",r"\bemploy(ed|ment|ees)\b",r"industrial production",r"\bproduction\b",
 r"real personal income",r"personal income",r"\bsales\b",r"new orders",r"\borders\b",r"housing starts",
 r"\bstarts\b",r"permit",r"capacity util",r"sentiment",r"confidence",r"average weekly hours",r"\bhours\b",
 r"real gross domestic",r"\bgdp\b",r"shipments",r"retail",r"consumption",r"\bincome\b",r"real disposable",
 r"manufactur",r"purchasing",r"business activity",r"new one family houses",r"capital goods",
 r"real m2\b",r"\bexports\b",r"real output",r"help.wanted",r"job openings",r"quits",r"hires",
 r"\bpce\b",r"durable goods",r"vehicle sales",r"real value"]
AMBIG=[r"price index",r"\bcpi\b",r"\bppi\b",r"deflator",r"interest rate",r"\byield\b",r"treasury",
 r"exchange rate",r"\bm1\b",r"\bm2\b(?! money stock real)",r"money stock",r"discount rate",r"\brate\b",
 r"debt",r"reserves",r"currency",r"per capita",r"population",r"\bcredit\b",r"loans",r"deposits",
 r"velocity",r"savings rate",r"tax",r"government",r"federal funds",r"commercial paper",r"pig iron",
 r"steel ingot",r"freight",r"per barrel",r"\bwti\b",r"crude",r"housing price",r"case.shiller"]
def sign(lbl,sid):
    L=(lbl or "").lower()
    for p in AMBIG:
        if re.search(p,L): return 0,"ambig"
    up=any(re.search(p,L) for p in UP_BAD)
    dn=any(re.search(p,L) for p in DOWN_BAD)
    # unemployment beats generic employ (handled: unemploy in UP_BAD, but 'employ' also matches DOWN via \bemploy\b won't match 'unemployment' word-bound? 'unemployment' -> \bemploy fails since preceded by 'un')
    if "unemploy" in L or "jobless" in L: return -1,"up_bad"   # higher=worse
    if up and not dn: return -1,"up_bad"
    if dn and not up: return +1,"down_bad"
    if dn and up: return 0,"conflict"
    return 0,"none"
inc=[]
for r in rows:
    c=cad(r); n=int(r["n"]); 
    if not(20<=c<=45): continue        # monthly cadence
    if n<60: continue                  # >=5yr
    s,why=sign(r["label"],r["series_id"])
    if s==0: continue
    inc.append(dict(series_id=r["series_id"],src=r["best_source"],sign=s,first=r["first"],
                    last=r["last"],n=n,cls=why,label=(r["label"] or "")[:70]))
json.dump(inc,open("research/chr43_signed_universe.json","w"),indent=0)
from collections import Counter
print("signed monthly universe:",len(inc))
print("by class",Counter(x["cls"] for x in inc))
print("down_bad(+1):",sum(1 for x in inc if x["sign"]==1),"up_bad(-1):",sum(1 for x in inc if x["sign"]==-1))
# coverage over time
for yr in [1948,1955,1960,1970,1980,1990,2000]:
    c=sum(1 for x in inc if d(x["first"]) and d(x["first"])<=date(yr,12,31))
    print(f"  members with data by {yr}: {c}")
# show a sample of each
print("-- sample up_bad --")
for x in [x for x in inc if x["sign"]==-1][:12]: print("  ",x["series_id"],x["label"])
print("-- sample down_bad --")
for x in [x for x in inc if x["sign"]==1][:12]: print("  ",x["series_id"],x["label"])
