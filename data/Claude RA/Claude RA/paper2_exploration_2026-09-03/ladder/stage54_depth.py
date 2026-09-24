# Round 19d: does depth explain the misses abroad?
import os, json
import pandas as pd, numpy as np
BASE = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
src = open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0]
exec(src)
rep = json.load(open(os.path.join(BASE,"ladder","stage52_intl.json")))

NBER = [("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),
        ("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),
        ("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),
        ("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),
        ("2024-04","2024-08")]

def depth(iso, P, T):
    g, sid = gdp(iso)
    if g is None: return None, None
    q = g[(g.index >= pd.Timestamp(P) - pd.DateOffset(months=5)) &
          (g.index <= pd.Timestamp(T) + pd.DateOffset(months=1))]
    if len(q) < 2: return None, None
    return (q.min()/q.max() - 1)*100, len(q)

def urise(iso, P, T):
    ur = first("LRHUTTTT%sM156S"%CC[iso], "LRUNTTTT%sM156S"%CC[iso], "LRHUTTTT%sM156N"%CC[iso])
    if ur is None: return None
    w = ur[(ur.index >= pd.Timestamp(P) - pd.DateOffset(months=6)) &
           (ur.index <= pd.Timestamp(T) + pd.DateOffset(months=9))]
    if len(w) < 6: return None
    return float(w.max() - w.min())

rows = []
for iso, e in rep.items():
    for x in e["techA"]:
        d, n = depth(iso, x["peak"], x["trough"])
        du = urise(iso, x["peak"], x["trough"])
        rows.append(dict(iso=iso, peak=x["peak"], trough=x["trough"], det=x["call"] is not None,
                         lag=x["lag"], gdp=d, urise=du))
df = pd.DataFrame(rows).dropna(subset=["gdp","urise"])
df.to_csv(os.path.join(BASE,"ladder","stage54_depth.csv"), index=False)

def band(col, cuts, lab):
    print("\n%-22s %-5s %-6s %-9s %s" % (lab, "n", "det", "det rate", "median lag"))
    for i,(a,b) in enumerate(cuts):
        s = df[(df[col] <= a) & (df[col] > b)] if col=="gdp" else df[(df[col] >= a) & (df[col] < b)]
        if not len(s): continue
        L = [l for l in s["lag"] if l is not None and not pd.isna(l)]
        print("%-22s %-5d %-6d %-9s %s" % (
            ("%.1f..%.1f" % (a,b)) if col=="gdp" else ("%.1f..%.1f" % (a,b)),
            len(s), s["det"].sum(), "%.0f%%" % (100*s["det"].mean()),
            ("%.1f" % np.median(L)) if L else "-"))

print("foreign + US technical recessions with GDP depth and unemployment rise: %d" % len(df))
band("gdp", [(0,-0.5),(-0.5,-1.0),(-1.0,-2.0),(-2.0,-99)], "peak-to-trough GDP %")
band("urise", [(0,0.5),(0.5,1.0),(1.0,2.0),(2.0,99)], "unemployment rise pp")

f = df[df.iso != "USA"]
print("\nforeign only, by unemployment rise:")
for a,b,lab in [(0,0.5,"< 0.5 pp"),(0.5,1.0,"0.5-1.0"),(1.0,2.0,"1.0-2.0"),(2.0,99,"> 2.0 pp")]:
    s = f[(f.urise>=a)&(f.urise<b)]
    if len(s): print("  %-9s n=%-3d detected %d = %.0f%%" % (lab, len(s), s["det"].sum(), 100*s["det"].mean()))
print("\ncorrelation det ~ urise: %.2f ; det ~ gdp depth: %.2f" %
      (df["det"].astype(float).corr(df["urise"]), df["det"].astype(float).corr(-df["gdp"])))
print("\nmissed episodes (foreign), shallowest first:")
m = f[~f.det].sort_values("urise")
for _,r in m.iterrows():
    print("  %-4s %s..%s  GDP %.1f%%  unemployment +%.2f pp" % (r.iso, r.peak[:7], r.trough[:7], r.gdp, r.urise))
