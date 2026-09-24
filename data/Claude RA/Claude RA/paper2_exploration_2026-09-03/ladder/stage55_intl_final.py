# Round 19 final: international replay with episode-interval scoring.
#   detection = an episode is OPEN at some point in [peak, trough]
#   lag       = month the covering episode opened, minus the peak month
#   false alarm = an episode that overlaps no recession window at all
import os, json
import pandas as pd, numpy as np
BASE = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
src = open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0]
exec(src)
NBER = [("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),
        ("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),
        ("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),
        ("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),
        ("2024-04","2024-08")]
NBER = [(pd.Timestamp(a+"-01"), pd.Timestamp(b+"-01")) for a,b in NBER]
DROP = {"e_fast"}

def episodes_of(b):
    idx, ug = b["idx"], b["ug"]
    ev = []
    for k, v in b["f"].items():
        if k in DROP: continue
        for d in idx[v.values]:
            ev.append(((pd.Timestamp(d)+pd.DateOffset(months=LAG[k])).replace(day=1), k))
    ev.sort()
    q3 = (ug < 0.20).rolling(3).min().fillna(0).astype(bool)
    eps, until = [], None
    for cm, k in ev:
        if until is not None and cm <= until: continue
        later = q3.index[(q3.index > cm) & q3.values]
        until = later[0] if len(later) else idx[-1]
        eps.append((cm, until, k))
    return eps

def score(mach, recs):
    res, used = [], set()
    for (P, T) in recs:
        cov = [m for m in mach if m[0] <= T and m[1] >= P]
        if cov:
            o, c, k = cov[0]; used.add((o, c, k))
            res.append(dict(peak=str(P.date()), trough=str(T.date()), open=str(o.date()),
                            chan=k, lag=(o.year-P.year)*12 + (o.month-P.month)))
        else:
            res.append(dict(peak=str(P.date()), trough=str(T.date()), open=None, chan=None, lag=None))
    fa = [(str(o.date()), str(c.date()), k) for (o, c, k) in mach
          if (o, c, k) not in used and not any(o <= T and c >= P for (P, T) in recs)]
    return res, fa

rep = {}
for iso in sorted(CC):
    b = build(iso)
    if b is None: continue
    mach = episodes_of(b)
    lo, hi = b["idx"][0], b["idx"][-1]
    tech, gsid = technical(iso)
    tech = [(P,T) for P,T in tech if P >= lo and T <= hi]
    oec  = [(P,T) for P,T in oecd(iso) if P >= lo and T <= hi]
    ref  = [(P,T) for P,T in NBER if P >= lo and T <= hi] if iso=="USA" else []
    allw = tech + oec + ref
    rA, _   = score(mach, tech)
    rB, _   = score(mach, oec)
    _,  faU = score(mach, allw)
    e = dict(name=NAME[iso], span=[str(lo.date()), str(hi.date())], chans=sorted(k for k in b["f"] if k not in DROP),
             techA=rA, oecdB=rB, fa=faU, gdp=gsid, years=(hi-lo).days/365.25,
             mach=[[str(o.date()), str(c.date()), k] for o,c,k in mach])
    if iso=="USA": e["nber"], _ = score(mach, ref)
    rep[iso] = e
json.dump(rep, open(os.path.join(BASE,"ladder","stage55_intl.json"),"w"), indent=1)

def show(title, key, skipus=False, minn=2):
    print("\n=== "+title+" ===")
    print("%-4s %-15s %-7s %-7s %-8s %-10s %-4s %s" % ("iso","country","cover","<=+3m","med lag","range","FA","channels"))
    tot=hit=inw=fas=0; yrs=0.0; L=[]
    for iso in sorted(rep):
        if skipus and iso=="USA": continue
        e = rep[iso]; r = e[key]
        if len(r) < minn: continue
        h=[x for x in r if x["open"]]; l=[x["lag"] for x in h]
        tot+=len(r); hit+=len(h); L+=l; inw+=sum(1 for x in l if -3<=x<=3)
        fas+=len(e["fa"]); yrs+=e["years"]
        print("%-4s %-15s %2d/%-4d %-7d %-8s %-10s %-4d %s" % (
            iso, e["name"], len(h), len(r), sum(1 for x in l if -3<=x<=3),
            ("%.1f"%np.median(l)) if l else "-", ("%d..%d"%(min(l),max(l))) if l else "-",
            len(e["fa"]), ",".join(c.replace("_fast","F").replace("_back","B") for c in e["chans"])))
    print("-"*94)
    print("TOTAL covered %d/%d = %.0f%% | opened within +-3m %d/%d = %.0f%% | FA %d in %.0f country-years (1 per %.1f yr)"
          % (hit,tot,100*hit/max(tot,1), inw,hit,100*inw/max(hit,1), fas,yrs,yrs/max(fas,1)))
    return hit,tot,fas,yrs,L

A = show("A. technical recessions (two negative quarters of real GDP)", "techA")
Ax= show("A'. foreign only", "techA", skipus=True)
B = show("B. OECD growth-cycle windows (RECM)", "oecdB")
print("\n=== control: same monthly channel set on the US vs NBER + Apr 2024 ===")
for x in rep["USA"]["nber"]:
    print("  peak %s -> episode opened %-11s %-8s lag %s" % (x["peak"], x["open"], x["chan"], x["lag"]))
print("  false alarms:", rep["USA"]["fa"] if rep["USA"]["fa"] else "none")
