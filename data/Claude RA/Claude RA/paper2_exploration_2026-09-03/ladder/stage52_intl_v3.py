# Round 19b: drop the employment channel (no faithful international analogue),
# score false alarms against the union of the two chronologies, attribute by channel.
import os, sys, json
import pandas as pd, numpy as np
BASE = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
src = open(os.path.join(BASE, "ladder", "stage51_intl_v2.py")).read()
src = src.split("NBER = [(")[0]
exec(src)

DROP = {"e_fast"}
def openings2(b, drop=DROP):
    idx, ug = b["idx"], b["ug"]
    ev = []
    for k, v in b["f"].items():
        if k in drop: continue
        for d in idx[v.values]:
            ev.append(((pd.Timestamp(d) + pd.DateOffset(months=LAG[k])).replace(day=1), k))
    ev.sort()
    q3 = (ug < 0.20).rolling(3).min().fillna(0).astype(bool)
    out, until = [], None
    for cm, k in ev:
        if until is not None and cm <= until: continue
        out.append((cm, k))
        later = q3.index[(q3.index > cm) & q3.values]
        until = later[0] if len(later) else idx[-1]
    return out

NBER = [("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),
        ("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),
        ("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),
        ("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),
        ("2024-04","2024-08")]
NBER = [(pd.Timestamp(a+"-01"), pd.Timestamp(b+"-01")) for a, b in NBER]

def score2(opens, eps, allwin, pre=6, post=3):
    res, used = [], set()
    for (P, T) in eps:
        hit = [o for o in opens if (P - pd.DateOffset(months=pre)) <= o[0] <= T]
        if hit:
            cm, k = hit[0]
            res.append(dict(peak=str(P.date()), trough=str(T.date()), call=str(cm.date()),
                            chan=k, lag=(cm.year-P.year)*12 + (cm.month-P.month)))
            used.add(hit[0])
        else:
            res.append(dict(peak=str(P.date()), trough=str(T.date()), call=None, chan=None, lag=None))
    fa = [(str(o[0].date()), o[1]) for o in opens if o not in used and
          not any((P - pd.DateOffset(months=pre)) <= o[0] <= (T + pd.DateOffset(months=post))
                  for (P, T) in allwin)]
    return res, fa

rep = {}
for iso in sorted(CC):
    b = build(iso)
    if b is None: continue
    ops = openings2(b)
    lo, hi = b["idx"][0], b["idx"][-1]
    tech, gsid = technical(iso)
    tech = [(P, T) for P, T in tech if P >= lo and T <= hi]
    oec  = [(P, T) for P, T in oecd(iso) if P >= lo and T <= hi]
    ref  = [(P, T) for P, T in NBER if P >= lo and T <= hi] if iso == "USA" else []
    allw = tech + oec + ref
    rA, faA = score2(ops, tech, allw)
    rB, faB = score2(ops, oec,  allw)
    e = dict(name=NAME[iso], span=[str(lo.date()), str(hi.date())], chans=sorted(b["f"].keys()),
             has=b["has"], techA=rA, oecdB=rB, fa=faA, gdp=gsid,
             opens=[[str(a.date()), k] for a, k in ops],
             years=(hi - lo).days/365.25)
    if iso == "USA":
        e["nber"], e["faN"] = score2(ops, ref, allw)
    rep[iso] = e
json.dump(rep, open(os.path.join(BASE, "ladder", "stage52_intl.json"), "w"), indent=1)

def show(title, key, minn=2, skipus=False):
    print("\n=== " + title + " ===")
    print("%-4s %-15s %-7s %-6s %-8s %-10s %-4s %s" %
          ("iso","country","det","<=+3m","med lag","range","FA","channels"))
    tot=hit=inw=fas=0; L=[]; yrs=0.0
    for iso in sorted(rep):
        if skipus and iso == "USA": continue
        e = rep[iso]; r = e[key]
        if len(r) < minn: continue
        h = [x for x in r if x["call"]]; l = [x["lag"] for x in h]
        tot += len(r); hit += len(h); L += l; inw += sum(1 for x in l if -3 <= x <= 3)
        fas += len(e["fa"]); yrs += e["years"]
        print("%-4s %-15s %2d/%-4d %-6d %-8s %-10s %-4d %s" % (
            iso, e["name"], len(h), len(r), sum(1 for x in l if -3 <= x <= 3),
            ("%.1f" % np.median(l)) if l else "-",
            ("%d..%d" % (min(l), max(l))) if l else "-", len(e["fa"]),
            ",".join(c.replace("_fast","F").replace("_back","B") for c in e["chans"] if c not in DROP)))
    print("-"*92)
    print("TOTAL detected %d/%d = %.0f%% | within +-3m %d/%d = %.0f%% | "
          "FA %d in %.0f country-years (1 per %.1f yr)" %
          (hit,tot,100*hit/max(tot,1), inw,hit,100*inw/max(hit,1), fas,yrs,yrs/max(fas,1)))
    return hit, tot, fas, yrs

hA,tA,faA,yA = show("A. technical recessions (two negative quarters of real GDP)", "techA")
hB,tB,faB,yB = show("B. OECD growth-cycle windows (RECM)", "oecdB")
hAx,tAx,fax,yx = show("A'. technical recessions, foreign only (US excluded)", "techA", skipus=True)

print("\n=== control: the same 4-channel monthly set on the US vs NBER + Apr 2024 ===")
e = rep["USA"]
for x in e["nber"]:
    print("  peak %s -> %-11s %-8s lag %s" % (x["peak"], x["call"], x["chan"], x["lag"]))
print("  false alarms:", e["faN"] if e["faN"] else "none")

from collections import Counter
c = Counter(k for e in rep.values() for _, k in e["fa"])
print("\nfalse alarms by channel:", dict(c))
c2 = Counter(x["chan"] for e in rep.values() for x in e["techA"] + e["oecdB"] if x["chan"])
print("detections by channel:", dict(c2))
