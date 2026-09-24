import csv
from datetime import date
rows=list(csv.DictReader(open("research/chr43_series_meta.csv")))
def d(s):
    try: return date.fromisoformat(s)
    except: return None
# missing members search
MEMB=["ICSA","IURSA","SAHM","UNRATE","INDPRO","CMRMTSPL","TCU","GACDFSA066","NASDAQ","BAA10Y","VIX","NFCI","PERMIT","HOUST","UMCSENT","W875RX1","PAYEMS","CLAIMS","T10YIE","T10Y2Y"]
print("== member id hits ==")
for m in MEMB:
    hit=[r["series_id"] for r in rows if m in r["series_id"]]
    print(m, hit[:6])
# coverage buckets
back1948=[r for r in rows if d(r["first"]) and d(r["first"])<=date(1948,12,31)]
back1959=[r for r in rows if d(r["first"]) and d(r["first"])<=date(1959,12,31)]
back1970=[r for r in rows if d(r["first"]) and d(r["first"])<=date(1970,12,31)]
# monthly-or-finer: span/n <=45 days approx and n>=120
def cadence(r):
    try:
        n=int(r["n"]); sp=int(r["span_days"])
        return sp/max(n-1,1)
    except: return 9999
monthly=[r for r in rows if 20<=cadence(r)<=45]
print("== coverage ==")
print("total",len(rows),"first<=1948",len(back1948),"<=1959",len(back1959),"<=1970",len(back1970))
print("monthly-cadence",len(monthly))
m1948=[r for r in back1948 if 20<=cadence(r)<=370]
print("first<=1948 & monthly-or-quarterly cadence",len(m1948))
for r in sorted(back1948,key=lambda r:r["first"])[:25]:
    print(" ",r["first"],r["last"],r["n"],r["series_id"],(r["label"] or "")[:45])
