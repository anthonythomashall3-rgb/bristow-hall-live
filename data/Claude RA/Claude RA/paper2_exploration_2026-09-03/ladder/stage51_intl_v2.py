# Round 19: international replay of the v7 STRUCTURE, US thresholds unchanged.
# Channels are the monthly translations of v7's fast channels and backstops.
# Chronologies: (A) technical recession, two negative quarters of real GDP;
#               (B) OECD growth-cycle windows (RECM).
# Control: the identical reduced channel set on the US against NBER + Paper 1's 2024.
import os, json
import pandas as pd, numpy as np

BASE  = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
ROOT  = os.path.expanduser("~/mnt/Onset Detector Data")
INTL  = os.path.join(ROOT, "19_international", "monthly")
FETCH = os.path.join(BASE, "data_fetched", "intl")
CHR   = os.path.join(ROOT, "22_recession_chronologies/monthly/recession_probabilities")

def load(sid):
    if sid is None: return None
    for d in (FETCH, INTL):
        p = os.path.join(d, sid + ".csv")
        if os.path.exists(p):
            x = pd.read_csv(p); x.columns = ["date", "v"]
            x["date"] = pd.to_datetime(x["date"])
            x = x[pd.to_numeric(x["v"], errors="coerce").notna()]
            s = pd.Series(x["v"].astype(float).values, index=pd.DatetimeIndex(x["date"].values))
            return s[~s.index.duplicated()].sort_index()
    return None
def first(*sids):
    for s in sids:
        r = load(s)
        if r is not None and len(r) > 36: return r
    return None

CC = dict(AUS="AU", CAN="CA", DEU="DE", ESP="ES", FRA="FR", GBR="GB", ITA="IT",
          JPN="JP", KOR="KR", MEX="MX", NOR="NO", NZL="NZ", SWE="SE", CHE="CH",
          DNK="DK", FIN="FI", AUT="AT", BEL="BE", NLD="NL", PRT="PT", GRC="GR",
          IRL="IE", POL="PL", HUN="HU", CZE="CZ", TUR="TR", ZAF="ZA", CHL="CL",
          ISR="IL", USA="US")
NAME = dict(AUS="Australia", CAN="Canada", DEU="Germany", ESP="Spain", FRA="France",
            GBR="United Kingdom", ITA="Italy", JPN="Japan", KOR="Korea", MEX="Mexico",
            NOR="Norway", NZL="New Zealand", SWE="Sweden", CHE="Switzerland",
            DNK="Denmark", FIN="Finland", AUT="Austria", BEL="Belgium",
            NLD="Netherlands", PRT="Portugal", GRC="Greece", IRL="Ireland",
            POL="Poland", HUN="Hungary", CZE="Czechia", TUR="Turkey",
            ZAF="South Africa", CHL="Chile", ISR="Israel", USA="United States")
EU = dict(DEU="DE", ESP="ES", FRA="FR", ITA="IT", NLD="NL", BEL="BE", AUT="AT",
          PRT="PT", GRC="EL", IRL="IE", FIN="FI", DNK="DK", SWE="SE", POL="PL",
          HUN="HU", CZE="CZ", NOR="NO", CHE="CH", GBR="UK")

def gdp(iso):
    for sid in [("CLVMNACSCAB1GQ" + EU[iso]) if iso in EU else None,
                "NAEXKP01%sQ652S" % CC[iso], "GDPC1" if iso == "USA" else None]:
        s = load(sid)
        if s is not None and len(s) >= 60: return s, sid
    return None, None

def technical(iso):
    g, sid = gdp(iso)
    if g is None: return [], None
    r = (g.pct_change() * 100).dropna()
    neg = (r < 0).values; dates = list(r.index)
    eps, i = [], 0
    while i < len(neg):
        if neg[i]:
            j = i
            while j + 1 < len(neg) and neg[j + 1]: j += 1
            if j - i + 1 >= 2 and i >= 1:
                P = (pd.Timestamp(dates[i-1]) + pd.DateOffset(months=2)).replace(day=1)
                T = (pd.Timestamp(dates[j])   + pd.DateOffset(months=2)).replace(day=1)
                eps.append((P, T))
            i = j + 1
        else: i += 1
    return eps, sid

def oecd(iso):
    p = os.path.join(CHR, iso + "RECM.csv")
    if not os.path.exists(p): return []
    x = pd.read_csv(p); x.columns = ["date", "v"]
    x["date"] = pd.to_datetime(x["date"])
    x = x[pd.to_numeric(x["v"], errors="coerce").notna()]
    s = (pd.Series(x["v"].astype(float).values,
         index=pd.DatetimeIndex(x["date"].values)).sort_index() >= 0.5).astype(int)
    eps, inr = [], False
    for i, (d, v) in enumerate(s.items()):
        if v == 1 and not inr: inr, a = True, d
        elif v == 0 and inr: inr = False; eps.append((a, s.index[i-1]))
    if inr: eps.append((a, s.index[-1]))
    return eps

# ---- v7 thresholds, unchanged ----
TH = dict(u_fast=0.35, iu_fast=0.40, e_fast=-0.1, r_fast=1.43,
          u_back=0.55, iu_back=0.50, r_back=2.50, ip_back=-2.0)
FRESH, GATE_LB = 4, 12
LAG = dict(u_fast=1, iu_fast=1, e_fast=1, ip_back=1, u_back=1, iu_back=1,
           r_fast=0, r_back=0)

def build(iso):
    ur = first("LRHUTTTT%sM156S" % CC[iso], "LRUNTTTT%sM156S" % CC[iso],
               "LRHUTTTT%sM156N" % CC[iso])
    if ur is None: return None
    iu = first("LMUNRRTT%sM156S" % CC[iso], "LMUNRRTT%sM156N" % CC[iso])
    em = first("LFEMTTTT%sM647S" % CC[iso])
    st = first("IR3TIB01%sM156N" % CC[iso], "IRSTCI01%sM156N" % CC[iso])
    lt = first("IRLTLT01%sM156N" % CC[iso])
    ip = first("%sPROINDMISMEI" % iso)
    idx = pd.DatetimeIndex(pd.date_range(ur.index[0], ur.index[-1], freq="MS"))
    u = ur.reindex(idx).interpolate(limit_area="inside")
    ug = u.rolling(3).mean() - u.rolling(12).min()
    gate = pd.Series(False, index=idx)
    if st is not None and lt is not None:
        sp = lt.reindex(idx, method="ffill") - st.reindex(idx, method="ffill")
        gate = (sp < 0).rolling(GATE_LB, min_periods=1).max().fillna(0).astype(bool)
    f = {}
    f["u_fast"] = (ug >= TH["u_fast"]) & gate
    f["u_back"] = (ug >= TH["u_back"])
    if iu is not None:
        v = iu.reindex(idx).interpolate(limit_area="inside")
        g2 = v.rolling(3).mean() - v.rolling(12).min()
        f["iu_fast"] = (g2 >= TH["iu_fast"]) & gate
        f["iu_back"] = (g2 >= TH["iu_back"])
    if em is not None:
        v = em.reindex(idx).interpolate(limit_area="inside")
        f["e_fast"] = ((v / v.shift(1) - 1) * 100 <= TH["e_fast"]) & gate
    if st is not None:
        s = st.reindex(idx, method="ffill"); d = s - s.shift(3)
        f["r_fast"] = (d <= -TH["r_fast"]) & gate
        f["r_back"] = (d <= -TH["r_back"])
    if ip is not None:
        p = ip.reindex(idx, method="ffill"); d = (p / p.shift(1) - 1) * 100
        f["ip_back"] = (d <= TH["ip_back"]) & (d.shift(1) <= TH["ip_back"])
    f = {k: v.fillna(False).astype(bool) for k, v in f.items()}
    return dict(idx=idx, f=f, ug=ug, gate=gate,
                has=dict(iu=iu is not None, em=em is not None, st=st is not None,
                         lt=lt is not None, ip=ip is not None))

def openings(b):
    idx, f, ug = b["idx"], b["f"], b["ug"]
    ev = []
    for k, v in f.items():
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

def score(opens, eps, pre=6, post=3):
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
    fa = [str(o[0].date()) + ":" + o[1] for o in opens if o not in used
          and not any((P - pd.DateOffset(months=pre)) <= o[0] <= (T + pd.DateOffset(months=post))
                      for (P, T) in eps)]
    return res, fa

NBER = [("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),
        ("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),
        ("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),
        ("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),
        ("2024-04","2024-08")]
NBER = [(pd.Timestamp(a + "-01"), pd.Timestamp(b + "-01")) for a, b in NBER]

rep = {}
for iso in sorted(CC):
    b = build(iso)
    if b is None: continue
    ops = openings(b)
    lo, hi = b["idx"][0], b["idx"][-1]
    tech, gsid = technical(iso)
    tech = [(P, T) for P, T in tech if P >= lo and T <= hi]
    oec  = [(P, T) for P, T in oecd(iso) if P >= lo and T <= hi]
    rA, faA = score(ops, tech); rB, faB = score(ops, oec)
    e = dict(name=NAME[iso], span=[str(lo.date()), str(hi.date())], has=b["has"],
             chans=sorted(b["f"].keys()), gdp=gsid, n_open=len(ops),
             techA=rA, faA=faA, oecdB=rB, faB=faB,
             opens=[[str(a.date()), k] for a, k in ops])
    if iso == "USA":
        nb = [(P, T) for P, T in NBER if P >= lo and T <= hi]
        e["nber"], e["faN"] = score(ops, nb)
    rep[iso] = e
json.dump(rep, open(os.path.join(BASE, "ladder", "stage51_intl.json"), "w"), indent=1)

def show(title, key, fak, minn=2):
    print("\n=== " + title + " ===")
    print("%-4s %-15s %-7s %-6s %-9s %-11s %-4s %s" %
          ("iso","country","det","<=+3m","med lag","lag range","FA","channels"))
    tot = hit = inw = 0; lags = []; fas = 0; yrs = 0
    for iso in sorted(rep):
        e = rep[iso]; r = e[key]
        if len(r) < minn: continue
        h = [x for x in r if x["call"]]; L = [x["lag"] for x in h]
        tot += len(r); hit += len(h); lags += L
        inw += sum(1 for l in L if -3 <= l <= 3); fas += len(e[fak])
        yrs += (pd.Timestamp(e["span"][1]) - pd.Timestamp(e["span"][0])).days / 365.25
        print("%-4s %-15s %2d/%-4d %-6d %-9s %-11s %-4d %s" % (
            iso, e["name"], len(h), len(r), sum(1 for l in L if -3 <= l <= 3),
            ("%.1f" % np.median(L)) if L else "-",
            ("%d..%d" % (min(L), max(L))) if L else "-", len(e[fak]),
            ",".join(c.replace("_fast","F").replace("_back","B") for c in e["chans"])))
    print("-" * 96)
    print("TOTAL  detected %d/%d = %.0f%%   within +-3 months %d/%d = %.0f%%   "
          "false alarms %d in %.0f country-years (1 per %.1f yr)" %
          (hit, tot, 100*hit/max(tot,1), inw, hit, 100*inw/max(hit,1), fas, yrs,
           yrs/max(fas,1)))
    return hit, tot, fas, yrs

A = show("A. technical recessions (two negative quarters of real GDP)", "techA", "faA")
B = show("B. OECD growth-cycle windows (RECM)", "oecdB", "faB")

print("\n=== control: the identical reduced channel set on the US ===")
e = rep["USA"]
for x in e["nber"]:
    print("  peak %s trough %s -> call %-11s %-8s lag %s" %
          (x["peak"], x["trough"], x["call"], x["chan"], x["lag"]))
print("  false alarms:", e["faN"] if e["faN"] else "none")
print("  channels available:", ",".join(e["chans"]))
