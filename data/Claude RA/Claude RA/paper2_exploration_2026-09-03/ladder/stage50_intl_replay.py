# Round 19: international replay of the v7 STRUCTURE with US thresholds unchanged.
# Two chronologies: (A) technical recession from quarterly real GDP,
#                   (B) OECD growth-cycle windows (RECM).
# Control: the same reduced channel set on the US against NBER.
import os, glob, json, itertools
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

# ---------- chronology A: technical recession (two negative quarters) ----------
def gdp_series(iso):
    for sid in [("CLVMNACSCAB1GQ" + EU[iso]) if iso in EU else None,
                "NAEXKP01%sQ652S" % CC[iso],
                "NGDPRSAXDC%sQ" % CC[iso],
                "GDPC1" if iso == "USA" else None]:
        s = load(sid)
        if s is not None and len(s) >= 60: return s, sid
    return None, None

def technical(iso):
    g, sid = gdp_series(iso)
    if g is None: return [], None
    r = g.pct_change() * 100
    neg = (r < 0).values
    dates = list(r.index)
    eps, i = [], 0
    while i < len(neg):
        if neg[i]:
            j = i
            while j + 1 < len(neg) and neg[j + 1]: j += 1
            if j - i + 1 >= 2 and i >= 1:
                pk = dates[i - 1]                 # last quarter before the fall
                P = (pd.Timestamp(pk) + pd.DateOffset(months=2)).replace(day=1)
                T = (pd.Timestamp(dates[j]) + pd.DateOffset(months=2)).replace(day=1)
                eps.append((P, T))
            i = j + 1
        else: i += 1
    return eps, sid

# ---------- chronology B: OECD growth-cycle ----------
def oecd(iso):
    p = os.path.join(CHR, iso + "RECM.csv")
    if not os.path.exists(p): return []
    x = pd.read_csv(p); x.columns = ["date", "v"]
    x["date"] = pd.to_datetime(x["date"])
    x = x[pd.to_numeric(x["v"], errors="coerce").notna()]
    s = pd.Series(x["v"].astype(float).values, index=pd.DatetimeIndex(x["date"].values)).sort_index()
    s = (s >= 0.5).astype(int)
    eps, inr = [], False
    for i, (d, v) in enumerate(s.items()):
        if v == 1 and not inr: inr = True; a = d
        elif v == 0 and inr: inr = False; eps.append((a, s.index[i - 1]))
    if inr: eps.append((a, s.index[-1]))
    return eps

# ---------- the reduced v7 structure, US thresholds unchanged ----------
TH = dict(fast_u=0.35, back_u=0.55, fast_r=1.43, back_r=2.50, back_ip=-2.0)
FRESH, GATE_LB = 4, 12
LAG = dict(u_fast=1, u_back=1, ip_back=1, r_fast=0, r_back=0)

def channels(ur, st, lt, ip):
    idx = pd.DatetimeIndex(pd.date_range(ur.index[0], ur.index[-1], freq="MS"))
    u = ur.reindex(idx).interpolate(limit_area="inside")
    ug = u.rolling(3).mean() - u.rolling(12).min()
    gate = pd.Series(False, index=idx)
    if st is not None and lt is not None:
        sp = lt.reindex(idx, method="ffill") - st.reindex(idx, method="ffill")
        gate = (sp < 0).rolling(GATE_LB, min_periods=1).max().fillna(0).astype(bool)
    f = {}
    f["u_fast"] = (ug >= TH["fast_u"]) & gate
    f["u_back"] = (ug >= TH["back_u"])
    if st is not None:
        s = st.reindex(idx, method="ffill"); d = s - s.shift(3)
        f["r_fast"] = (d <= -TH["fast_r"]) & gate
        f["r_back"] = (d <= -TH["back_r"])
    if ip is not None:
        p = ip.reindex(idx, method="ffill"); d = (p / p.shift(1) - 1) * 100
        f["ip_back"] = (d <= TH["back_ip"]) & (d.shift(1) <= TH["back_ip"])
    f = {k: v.fillna(False) for k, v in f.items()}
    return idx, f, ug, gate

def openings(idx, f, ug):
    """freshness + state machine: an episode opens on the first firing month and
    stays open until the gap is back under 0.20 pp for three straight months."""
    on = None
    for v in f.values(): on = v if on is None else (on | v)
    ev = []
    for k, v in f.items():
        for d in idx[v.values]:
            ev.append(((pd.Timestamp(d) + pd.DateOffset(months=LAG[k])).replace(day=1), k, pd.Timestamp(d)))
    ev.sort()
    quiet = (ug < 0.20)
    q3 = quiet.rolling(3).min().fillna(0).astype(bool)
    out, open_until = [], None
    for cm, k, ref in ev:
        if open_until is not None and cm <= open_until: continue
        out.append((cm, k, ref))
        later = q3.index[(q3.index > ref) & q3.values]
        open_until = later[0] if len(later) else idx[-1]
    return out

def score(opens, eps, pre=6, post=3):
    """detection, lag and false alarms against a monthly peak/trough chronology."""
    res, used = [], set()
    for (P, T) in eps:
        lo = (P - pd.DateOffset(months=pre)); hi = T
        hit = [o for o in opens if lo <= o[0] <= hi]
        if hit:
            cm, k, ref = hit[0]
            lag = (cm.year - P.year) * 12 + (cm.month - P.month)
            res.append(dict(peak=str(P.date()), trough=str(T.date()), call=str(cm.date()),
                            chan=k, lag=lag))
            used.add(hit[0])
        else:
            res.append(dict(peak=str(P.date()), trough=str(T.date()), call=None,
                            chan=None, lag=None))
    fa = []
    for o in opens:
        if o in used: continue
        if any((P - pd.DateOffset(months=pre)) <= o[0] <= (T + pd.DateOffset(months=post))
               for (P, T) in eps): continue
        fa.append(str(o[0].date()) + ":" + o[1])
    return res, fa

# ---------- run ----------
NBER = [("1969-12-01","1970-11-01"),("1973-11-01","1975-03-01"),("1980-01-01","1980-07-01"),
        ("1981-07-01","1982-11-01"),("1990-07-01","1991-03-01"),("2001-03-01","2001-11-01"),
        ("2007-12-01","2009-06-01"),("2020-02-01","2020-04-01"),("2024-04-01","2024-08-01")]
NBER = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in NBER]

report = {}
for iso in sorted(CC):
    ur = load("LRHUTTTT%sM156S" % CC[iso]) 
    if ur is None: ur = load("LRUNTTTT%sM156S" % CC[iso])
    if ur is None: continue
    st = load("IR3TIB01%sM156N" % CC[iso])
    if st is None: st = load("IRSTCI01%sM156N" % CC[iso])
    lt = load("IRLTLT01%sM156N" % CC[iso])
    ip = load("%sPROINDMISMEI" % iso)
    idx, f, ug, gate = channels(ur, st, lt, ip)
    ops = openings(idx, f, ug)
    tech, gsid = technical(iso)
    tech = [(P, T) for P, T in tech if P >= idx[0] and T <= idx[-1]]
    oec  = [(P, T) for P, T in oecd(iso) if P >= idx[0] and T <= idx[-1]]
    rA, faA = score(ops, tech)
    rB, faB = score(ops, oec)
    entry = dict(name=NAME[iso], span=[str(idx[0].date()), str(idx[-1].date())],
                 chans=sorted(f.keys()), gdp=gsid,
                 techA=rA, faA=faA, oecdB=rB, faB=faB, n_open=len(ops))
    if iso == "USA":
        rN, faN = score(ops, NBER)
        entry["nber"] = rN; entry["faN"] = faN
    report[iso] = entry

json.dump(report, open(os.path.join(BASE, "ladder", "stage50_intl.json"), "w"), indent=1)

def line(iso, e, key, fak):
    r = e[key]; hit = [x for x in r if x["call"]]
    lags = [x["lag"] for x in hit]
    inq = sum(1 for l in lags if -3 <= l <= 3)
    print("%-4s %-15s %2d/%-2d  in+-3m %2d  lag med %5s  range %-9s  FA %d" % (
        iso, e["name"], len(hit), len(r), inq,
        ("%.1f" % np.median(lags)) if lags else "-",
        ("%d..%d" % (min(lags), max(lags))) if lags else "-", len(e[fak])))

print("\n=== A. technical recessions (two negative quarters of real GDP) ===")
print("%-4s %-15s %-6s %-10s %-14s %-16s %s" % ("iso","country","det","in+-3m","median lag","lag range","false alarms"))
for iso in sorted(report):
    if report[iso]["techA"]: line(iso, report[iso], "techA", "faA")
print("\n=== B. OECD growth-cycle windows (RECM) ===")
for iso in sorted(report):
    if report[iso]["oecdB"]: line(iso, report[iso], "oecdB", "faB")
if "USA" in report:
    print("\n=== control: same reduced channel set on the US vs NBER ===")
    e = report["USA"]; r = e["nber"]
    for x in r: print("  peak %s  call %s  chan %-7s lag %s" % (x["peak"], x["call"], x["chan"], x["lag"]))
    print("  false alarms:", e["faN"])
