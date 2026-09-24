"""CH-R61 — Severity yardstick comparison from the LANDED store (read-only, §20-class).
Zero store writes. Computes OUR numbers; external figures are COMPARATORS only (labeled).
NBER peak/trough dates are external comparator chronology, flagged as such.
"""
import glob, json, collections, csv, datetime as dt

NORM = "live_data/store/normalized/sha256"

# --- series -> (series_id in store, cadence) ; UNRATE/PAYEMS have no bare current
#     lane, use latest landed vintage as current-revised proxy (noted in brief).
SERIES = {
    "GDPC1":  ("GDPC1",               "Q"),
    "INDPRO": ("INDPRO",              "M"),
    "UNRATE": ("UNRATE.ASOF20260702", "M"),
    "PAYEMS": ("PAYEMS.ASOF20260702", "M"),
}
WANT = set(v[0] for v in SERIES.values())

# load
raw = collections.defaultdict(dict)  # sid -> {date: float}
for f in glob.glob(NORM + "/**/*.json", recursive=True):
    try: blob = json.load(open(f))
    except: continue
    recs = blob.get("records") if isinstance(blob, dict) else None
    if not recs: continue
    for r in recs:
        sid = r.get("series_id")
        if sid not in WANT: continue
        p = r.get("observation_period"); v = r.get("value")
        if not p or v in (None, "", ".", "NaN"): continue
        try: val = float(v)
        except: continue
        try: d = dt.date.fromisoformat(p[:10])
        except: continue
        raw[sid][d] = val

def ser(name):
    sid = SERIES[name][0]
    return dict(sorted(raw[sid].items()))

G = ser("GDPC1"); IP = ser("INDPRO"); UR = ser("UNRATE"); PE = ser("PAYEMS")
for n, s in [("GDPC1",G),("INDPRO",IP),("UNRATE",UR),("PAYEMS",PE)]:
    ks = list(s)
    print("%s: %d obs %s..%s" % (n, len(s), ks[0], ks[-1]))

def ym(y, m): return dt.date(y, m, 1)

# NBER episodes: (label, peak(y,m), trough(y,m))  -- COMPARATOR chronology, flagged
EP = [
    ("1948-49", (1948,11), (1949,10)),
    ("1953-54", (1953, 7), (1954, 5)),
    ("1957-58", (1957, 8), (1958, 4)),
    ("1960-61", (1960, 4), (1961, 2)),
    ("1969-70", (1969,12), (1970,11)),
    ("1973-75", (1973,11), (1975, 3)),
    ("1980",    (1980, 1), (1980, 7)),
    ("1981-82", (1981, 7), (1982,11)),
    ("1990-91", (1990, 7), (1991, 3)),
    ("2001",    (2001, 3), (2001,11)),
    ("2007-09", (2007,12), (2009, 6)),
    ("2020",    (2020, 2), (2020, 4)),
    ("2022-24", None, None),  # no NBER chronology
]

def addm(d, n):
    y = d.year + (d.month - 1 + n)//12
    m = (d.month - 1 + n)%12 + 1
    return dt.date(y, m, 1)

def window(series, d0, d1):
    return {d:v for d,v in series.items() if d0 <= d <= d1}

def p2t_decline(series, pk, tr, pk_lead, pk_lag, tr_lag):
    """indicator's own peak-to-trough % decline. peak searched around NBER peak,
    trough searched from found peak through NBER trough + tr_lag."""
    ps = addm(ym(*pk), -pk_lead); pe_ = addm(ym(*pk), pk_lag)
    w = window(series, ps, pe_)
    if not w: return None
    pk_d = max(w, key=lambda d: w[d]); pk_v = w[pk_d]
    te = addm(ym(*tr), tr_lag)
    w2 = {d:v for d,v in series.items() if pk_d <= d <= te}
    if not w2: return None
    tr_d = min(w2, key=lambda d: w2[d]); tr_v = w2[tr_d]
    return dict(pk_date=pk_d.isoformat(), pk_val=pk_v, tr_date=tr_d.isoformat(),
               tr_val=tr_v, pct=100.0*(tr_v-pk_v)/pk_v)

def ur_metrics(pk, tr):
    # cycle low: min UR in [peak-6mo, peak+3mo]; peak UR: max in [peak, trough+18mo]
    lo_w = window(UR, addm(ym(*pk),-6), addm(ym(*pk),3))
    hi_w = window(UR, ym(*pk), addm(ym(*tr),18))
    if not lo_w or not hi_w: return None
    lo_d = min(lo_w, key=lambda d: lo_w[d]); lo_v = lo_w[lo_d]
    hi_d = max(hi_w, key=lambda d: hi_w[d]); hi_v = hi_w[hi_d]
    return dict(start_ur=lo_v, start_date=lo_d.isoformat(),
                peak_ur=hi_v, peak_date=hi_d.isoformat(), rise=hi_v-lo_v)

def recovery(series, pk, tr, pk_lead, pk_lag, tr_lag, cadence):
    """months from pre-recession peak until series first regains that level."""
    r = p2t_decline(series, pk, tr, pk_lead, pk_lag, tr_lag)
    if not r: return None
    pk_d = dt.date.fromisoformat(r["pk_date"]); pk_v = r["pk_val"]
    tr_d = dt.date.fromisoformat(r["tr_date"])
    after = {d:v for d,v in series.items() if d > tr_d and v >= pk_v}
    if not after:
        return dict(regained=False, months=None, pk_date=r["pk_date"])
    rd = min(after)
    months = (rd.year-pk_d.year)*12 + (rd.month-pk_d.month)
    return dict(regained=True, months=months, pk_date=r["pk_date"], regain_date=rd.isoformat())

rows = []
for label, pk, tr in EP:
    if pk is None:
        rows.append(dict(episode=label, status="UNREACHABLE",
            reason="No NBER peak/trough dated; product timeline needs a chronology. "
                   "Payrolls grew throughout; GDP dip H1-2022 never NBER-dated."))
        continue
    dur = (tr[0]-pk[0])*12 + (tr[1]-pk[1])
    gdp = p2t_decline(G, pk, tr, pk_lead=6, pk_lag=3, tr_lag=6)          # months; Q data
    ip  = p2t_decline(IP, pk, tr, pk_lead=3, pk_lag=3, tr_lag=6)
    pay = p2t_decline(PE, pk, tr, pk_lead=3, pk_lag=3, tr_lag=12)        # payroll troughs late
    urm = ur_metrics(pk, tr)
    grec = recovery(G, pk, tr, 6, 3, 6, "Q")
    erec = recovery(PE, pk, tr, 3, 3, 12, "M")
    rows.append(dict(
        episode=label, status="OK", nber_peak="%d-%02d"%pk, nber_trough="%d-%02d"%tr,
        duration_months=dur,
        gdp_pct=None if not gdp else round(gdp["pct"],2),
        gdp_pk=None if not gdp else gdp["pk_date"], gdp_tr=None if not gdp else gdp["tr_date"],
        ip_pct=None if not ip else round(ip["pct"],2),
        pay_pct=None if not pay else round(pay["pct"],2),
        ur_start=None if not urm else round(urm["start_ur"],1),
        ur_peak=None if not urm else round(urm["peak_ur"],1),
        ur_peak_date=None if not urm else urm["peak_date"],
        ur_rise=None if not urm else round(urm["rise"],1),
        gdp_recovery_months=None if not grec else grec["months"],
        emp_recovery_months=None if not erec else erec["months"],
    ))

# write CSV
cols = ["episode","status","nber_peak","nber_trough","duration_months","gdp_pct","gdp_pk",
        "gdp_tr","ip_pct","pay_pct","ur_start","ur_peak","ur_peak_date","ur_rise",
        "gdp_recovery_months","emp_recovery_months","reason"]
with open("research/yardstick_comparison_v1.csv","w",newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)

# ranking helper: rank episodes by a metric (1 = most severe)
ok = [r for r in rows if r["status"]=="OK"]
def rankby(key, more_severe_is):
    vals = [(r["episode"], r.get(key)) for r in ok if r.get(key) is not None]
    if more_severe_is == "min":   # e.g. gdp_pct negative -> most negative most severe
        vals.sort(key=lambda x: x[1])
    else:
        vals.sort(key=lambda x: -x[1])
    # ties => shared rank
    out={}; i=0
    while i < len(vals):
        j=i
        while j+1<len(vals) and abs(vals[j+1][1]-vals[i][1])<1e-9: j+=1
        for k in range(i,j+1): out[vals[k][0]] = i+1
        i=j+1
    return out

yardsticks = {
    "duration":   rankby("duration_months","max"),
    "gdp":        rankby("gdp_pct","min"),
    "ur_peak":    rankby("ur_peak","max"),
    "ur_rise":    rankby("ur_rise","max"),
    "payroll":    rankby("pay_pct","min"),
    "indpro":     rankby("ip_pct","min"),
    "gdp_recovery": rankby("gdp_recovery_months","max"),
    "emp_recovery": rankby("emp_recovery_months","max"),
}

# comparison matrix print
print("\n=== RANK MATRIX (1=most severe) ===")
hdr = ["episode"]+list(yardsticks)
print(" | ".join(hdr))
for r in ok:
    e=r["episode"]
    print(" | ".join([e]+[str(yardsticks[y].get(e,"-")) for y in yardsticks]))

# flip detection: for each pair, does severity order differ across yardsticks?
eps=[r["episode"] for r in ok]
flips=[]
for a_i in range(len(eps)):
    for b_i in range(a_i+1,len(eps)):
        a,b=eps[a_i],eps[b_i]
        winners=collections.Counter()
        detail={}
        for y,rk in yardsticks.items():
            if a in rk and b in rk:
                if rk[a]<rk[b]: winners["a"]+=1; detail[y]=a
                elif rk[b]<rk[a]: winners["b"]+=1; detail[y]=b
                else: detail[y]="tie"
        if winners["a"]>0 and winners["b"]>0:
            flips.append(dict(pair=[a,b], a_wins=[y for y,w in detail.items() if w==a],
                              b_wins=[y for y,w in detail.items() if w==b],
                              ties=[y for y,w in detail.items() if w=="tie"]))

# robust orderings: pairs where one dominates on every comparable yardstick
robust=[]
for a_i in range(len(eps)):
    for b_i in range(len(eps)):
        if a_i==b_i: continue
        a,b=eps[a_i],eps[b_i]
        comp=[(rk[a],rk[b]) for y,rk in yardsticks.items() if a in rk and b in rk]
        if len(comp)>=5 and all(x<y for x,y in comp):
            robust.append([a,b,len(comp)])

focus={}
def pair_detail(a,b):
    d={}
    for y,rk in yardsticks.items():
        if a in rk and b in rk:
            d[y]={"rank_"+a:rk[a],"rank_"+b:rk[b],
                  "winner": a if rk[a]<rk[b] else (b if rk[b]<rk[a] else "tie")}
    return d
focus["1981-82_vs_2007-09"]=pair_detail("1981-82","2007-09")
focus["1980_vs_1981-82"]=pair_detail("1980","1981-82")

out=dict(batch="CH-R61_YARDSTICK_COMPARISON", mode="read-only §20",
    note="Our numbers from landed store. NBER dates + all external figures are COMPARATORS.",
    ur_payems_lane="UNRATE/PAYEMS have NO bare current_revised lane; used latest landed "
                   "vintage ASOF20260702 as current-revised proxy (data gap, see brief).",
    rank_matrix={r["episode"]:{y:yardsticks[y].get(r["episode"]) for y in yardsticks} for r in ok},
    flips=flips, robust_dominations=robust, focus_pairs=focus)
json.dump(out, open("research/yardstick_comparison_flips_v1.json","w"), indent=1)
print("\nflips:",len(flips)," robust dominations:",len(robust))
print("wrote research/yardstick_comparison_v1.csv + research/yardstick_comparison_flips_v1.json")
