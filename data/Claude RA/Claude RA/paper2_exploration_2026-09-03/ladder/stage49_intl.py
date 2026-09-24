# Round 19: international replay of the v7 structure, US thresholds unchanged.
# Chronology: OECD-based recession indicators (RECM, peak through trough), monthly.
import os, glob, json
import pandas as pd, numpy as np

ROOT = os.path.expanduser("~/mnt/Onset Detector Data")
INTL = os.path.join(ROOT, "19_international", "monthly")
FETCH = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/intl")
CHR  = os.path.join(ROOT, "22_recession_chronologies/monthly/recession_probabilities")

def load(sid):
    for d in (FETCH, INTL):
        p = os.path.join(d, sid + ".csv")
        if os.path.exists(p):
            x = pd.read_csv(p)
            x.columns = ["date", "v"]
            x["date"] = pd.to_datetime(x["date"])
            x = x[pd.to_numeric(x["v"], errors="coerce").notna()]
            s = pd.Series(x["v"].astype(float).values, index=x["date"].values)
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

# ---------------- chronology ----------------
def episodes(iso):
    p = os.path.join(CHR, iso + "RECM.csv")
    if not os.path.exists(p): return None
    x = pd.read_csv(p); x.columns = ["date", "v"]
    x["date"] = pd.to_datetime(x["date"])
    x = x[pd.to_numeric(x["v"], errors="coerce").notna()]
    s = pd.Series(x["v"].astype(float).values, index=x["date"].values).sort_index()
    s = (s >= 0.5).astype(int)
    eps, inr = [], False
    for i, (d, v) in enumerate(s.items()):
        if v == 1 and not inr:
            inr = True; start = d
        elif v == 0 and inr:
            inr = False; eps.append((start, s.index[i-1]))
    if inr: eps.append((start, s.index[-1]))
    # RECM marks peak month through trough month: peak = first flagged month,
    # trough = last flagged month.
    return [(a, b) for a, b in eps], s

# ---------------- v7 structure, US thresholds ----------------
# fast channels are gated by an inverted term spread in the prior 12 months.
TH = dict(fast_u=0.35, back_u=0.55, fast_r=1.43, back_r=2.50, back_ip=-2.0)
FRESH = 4        # months (~120 days)
GATE_LOOKBACK = 12

def run_country(iso, ur, st, lt, ip):
    idx = ur.index
    ug = pd.Series(index=idx, dtype=float)
    r3 = ur.rolling(3).mean()
    m12 = ur.rolling(12).min()
    ug = r3 - m12                       # Sahm-analogue gap, pp
    spread = None
    if st is not None and lt is not None:
        a = lt.reindex(idx, method="ffill"); b = st.reindex(idx, method="ffill")
        spread = a - b
    dr = None
    if st is not None:
        s = st.reindex(idx, method="ffill")
        dr = s.shift(0) - s.shift(3)     # 3-month change, pp (fall = negative)
    dip = None
    if ip is not None:
        p = ip.reindex(idx, method="ffill")
        dip = (p / p.shift(1) - 1) * 100

    gate = pd.Series(False, index=idx)
    if spread is not None:
        inv = spread < 0
        gate = inv.rolling(GATE_LOOKBACK, min_periods=1).max().astype(bool)

    fire = {}
    fire["u_fast"] = (ug >= TH["fast_u"]) & gate
    fire["u_back"] = (ug >= TH["back_u"])
    if dr is not None:
        fire["r_fast"] = (dr <= -TH["fast_r"]) & gate
        fire["r_back"] = (dr <= -TH["back_r"])
    if dip is not None:
        fire["ip_back"] = (dip <= TH["back_ip"]) & (dip.shift(1) <= TH["back_ip"])

    any_on = None
    for k, v in fire.items():
        v = v.fillna(False)
        any_on = v if any_on is None else (any_on | v)
    fresh = any_on.rolling(FRESH, min_periods=1).max().astype(bool)

    # publication lag: monthly labour and IP data are known the following month;
    # rates are known the same month.
    lag = {"u_fast": 1, "u_back": 1, "ip_back": 1, "r_fast": 0, "r_back": 0}
    calls = []   # (call month, channel)
    for k, v in fire.items():
        for d in idx[v.fillna(False).values]:
            cm = (pd.Timestamp(d) + pd.DateOffset(months=lag[k])).replace(day=1)
            calls.append((cm, k, pd.Timestamp(d)))
    calls.sort()
    return calls, fire, gate, ug

def state_machine(calls, ends_idx, chron):
    """Open an episode on the first call; close it when the chronology-free
    close condition (gap back under 0.20 for 3 months) holds. Returns openings."""
    opens, open_until = [], None
    for cm, k, ref in calls:
        if open_until is not None and cm <= open_until: continue
        opens.append((cm, k, ref))
        open_until = cm + pd.DateOffset(months=12)
    return opens

rows, per_country = [], {}
for iso in sorted(CC):
    e = episodes(iso)
    if e is None: continue
    eps, flag = e
    ur = load("LRHUTTTT%sM156S" % CC[iso]) 
    if ur is None: ur = load("LRUNTTTT%sM156S" % CC[iso])
    if ur is None: continue
    st = load("IR3TIB01%sM156N" % CC[iso])
    if st is None: st = load("IRSTCI01%sM156N" % CC[iso])
    lt = load("IRLTLT01%sM156N" % CC[iso])
    ip = load("%sPROINDMISMEI" % iso)
    per_country[iso] = dict(ur=ur, st=st, lt=lt, ip=ip, eps=eps, flag=flag)
    rows.append((iso, NAME[iso], str(ur.index[0].date()), str(ur.index[-1].date()),
                 len(eps), st is not None, lt is not None, ip is not None))

print("%-4s %-16s %-10s %-10s %5s %5s %5s %5s" % ("iso","country","ur from","ur to","eps","short","long","ip"))
for r in rows:
    print("%-4s %-16s %-10s %-10s %5d %5s %5s %5s" % r)
json.dump({k: [[str(a.date()), str(b.date())] for a, b in v["eps"]] for k, v in per_country.items()},
          open(os.path.join(os.path.dirname(__file__), "stage49_chron.json"), "w"), indent=0)
