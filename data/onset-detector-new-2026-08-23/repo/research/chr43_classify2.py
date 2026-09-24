import csv,re,json
from datetime import date
from collections import Counter
rows=list(csv.DictReader(open("research/chr43_series_meta.csv")))
def d(s):
    try: return date.fromisoformat(s)
    except: return None
def cad(r):
    try: return int(r["span_days"])/max(int(r["n"])-1,1)
    except: return 9999
# ---- exclusions (pollution / non-current-state) ----
EXCL_ID=[r"\.STATE\.",r"STATE\.\d",r"_FUTURE$",r"\.NSA",r"_NSA"]
EXCL_LBL=[r"six-month expectation",r"\bexpectations?\b",r"— (Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|District of Columbia|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New |North |Ohio|Oklahoma|Oregon|Pennsylvania|Rhode|South |Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)",
 r"earnings",r"not seasonally adjusted",r"future"]
UP_BAD=[r"unemploy",r"jobless",r"\bclaims\b",r"insured unemploy",r"delinqu",r"default",r"charge-?off",
 r"financial stress",r"financial conditions",r"volatilit",r"\bvix\b",r"bankrupt",r"uncertainty",
 r"layoff",r"discouraged",r"part.time for economic",r"foreclos"]
DOWN_BAD=[r"payroll",r"all employees",r"\bemploy(ed|ment|ees)\b",r"industrial production",r"\bproduction\b",
 r"real personal income",r"personal income",r"\bsales\b",r"new orders",r"\borders\b",r"housing starts",
 r"\bstarts\b",r"permit",r"capacity util",r"sentiment",r"confidence",r"average weekly hours",r"weekly hours",
 r"real gross domestic",r"shipments",r"retail",r"consumption",r"real disposable",r"manufactur",
 r"purchasing",r"business activity",r"capital goods",r"help.wanted",r"job openings",r"quits",r"hires",
 r"durable goods",r"vehicle sales",r"general activity",r"new one family"]
AMBIG=[r"price index",r"\bcpi\b",r"\bppi\b",r"deflator",r"interest rate",r"\byield\b",r"treasury",
 r"exchange rate",r"money stock",r"discount rate",r"\brate\b",r"\bdebt\b",r"reserves",r"currency",
 r"per capita",r"population",r"\bcredit\b",r"\bloans\b",r"deposits",r"velocity",r"savings rate",
 r"\btax\b",r"federal funds",r"commercial paper",r"pig iron",r"steel ingot",r"freight",r"per barrel",
 r"crude",r"case.shiller",r"cushing",r"\bwti\b",r"gasoline",r"inventor"]
def excluded(sid,lbl):
    for p in EXCL_ID:
        if re.search(p,sid): return True
    L=(lbl or "").lower()
    for p in EXCL_LBL:
        if re.search(p,L,re.I): return True
    return False
def sign(lbl):
    L=(lbl or "").lower()
    for p in AMBIG:
        if re.search(p,L): return 0,"ambig"
    if "unemploy" in L or "jobless" in L: return -1,"up_bad"
    up=any(re.search(p,L) for p in UP_BAD); dn=any(re.search(p,L) for p in DOWN_BAD)
    if up and not dn: return -1,"up_bad"
    if dn and not up: return +1,"down_bad"
    if dn and up: return 0,"conflict"
    return 0,"none"
inc=[]
for r in rows:
    c=cad(r); n=int(r["n"]); sid=r["series_id"]; lbl=r["label"]
    if not(20<=c<=45) or n<60: continue
    if excluded(sid,lbl): continue
    s,why=sign(lbl)
    if s==0: continue
    inc.append(dict(series_id=sid,src=r["best_source"],sign=s,first=r["first"],last=r["last"],n=n,cls=why,label=(lbl or "")[:70]))
json.dump(inc,open("research/chr43_signed_universe.json","w"),indent=0)
print("signed de-polluted monthly universe:",len(inc),"(-1 up_bad:",sum(1 for x in inc if x['sign']==-1),"+1 down_bad:",sum(1 for x in inc if x['sign']==1),")")
for yr in [1948,1955,1960,1970,1980,1990,2000,2010]:
    print(f"  members reporting by {yr}: {sum(1 for x in inc if d(x['first']) and d(x['first'])<=date(yr,12,31))}")
# concept-family duplication check: prefix before first dot / digit
fam=Counter(re.split(r'[.\d]',x['series_id'])[0][:12] for x in inc)
print("top source families:",fam.most_common(12))
print("-- earliest 20 --")
for x in sorted(inc,key=lambda x:x['first'])[:20]: print(f"  {x['first']} {x['sign']:+d} {x['series_id'][:28]:28} {x['label']}")
