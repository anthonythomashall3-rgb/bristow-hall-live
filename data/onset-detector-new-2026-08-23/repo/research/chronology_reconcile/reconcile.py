#!/usr/bin/env python3
"""B-CHRONOLOGY-RECONCILE — read-only three-way chronology comparison + z-baseline impact.

Reads current-revised raw CSVs (data_archive/current_revised_and_spatial/) and the frozen
target ledger. Replicates the index_v1.py loader + deterioration transforms + z-standardisation
EXACTLY (no nowcast fills injected — baseline mu/sd only, which is what step 2 measures).

WRITES ONLY under research/chronology_reconcile/. Touches no store byte, no ledger, no value.
"""
import csv, datetime as dt, json, os, bisect
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data_archive", "current_revised_and_spatial")
LEDGER = os.path.join(ROOT, "model_authority", "target_ledger",
                      "instrument_onset_target_ledger.v1.json")
OUT = os.path.join(ROOT, "research", "chronology_reconcile")

# ---- loader: byte-for-byte the index_v1.py load() ----
def load(sid):
    out = {}
    for r in csv.reader(open(os.path.join(RAW, sid + ".csv"))):
        if r[0][0:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            out[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
    return out

MEMBERS_RAW = ["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU",
    "GACDFSA066MSFRBPHI","NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST","PERMIT",
    "UMCSENT","W875RX1","GS10","GS1","USRECD"]
S = {s: load(s) for s in MEMBERS_RAW}
BAAAAA = {d: S["BAA"][d] - S["AAA"][d] for d in S["BAA"] if d in S["AAA"]}

START = dt.date(1976, 6, 1)
END = max(max(S[k]) for k in ("ICSA","NASDAQCOM","VIXCLS","NFCI","BAA10Y"))

# ---- transforms (index_v1.py verbatim) ----
def yoy(series):
    out = {}; ks = sorted(series)
    for k in ks:
        prior = k - dt.timedelta(days=365)
        i = bisect.bisect_left(ks, prior)
        cand = [x for x in (ks[max(0,i-1):i+2]) if abs((x - prior).days) <= 20]
        if cand:
            p = min(cand, key=lambda x: abs((x - prior).days))
            if series[p] != 0: out[k] = (series[k] / series[p] - 1) * 100
    return out

def _window_extreme(series, look, fn):
    out = {}; ks = sorted(series); vals = [series[k] for k in ks]
    lo = 0; dq = deque(); ismax = (fn is max)
    for i, k in enumerate(ks):
        while lo < i and (k - ks[lo]).days > look: lo += 1
        while dq and dq[0] < lo: dq.popleft()
        while dq and ((vals[dq[-1]] <= vals[i]) if ismax else (vals[dq[-1]] >= vals[i])): dq.pop()
        dq.append(i)
        out[k] = vals[dq[0]]
    return out, ks, vals

def drawdown(series):
    mx, ks, vals = _window_extreme(series, 370, max)
    return {k: (series[k]/mx[k]-1)*100 if mx[k] else 0 for k in ks}

def rise_floor(series, look=370):
    mn, ks, vals = _window_extreme(series, look, min)
    return {k: series[k]-mn[k] for k in ks}

T = {}
T["ICSA"]   = yoy(S["ICSA"])
T["IURSA"]  = rise_floor(S["IURSA"])
T["SAHM"]   = S["SAHMREALTIME"]
T["UNRATEv"]= {k: v for k, v in rise_floor(S["UNRATE"], 120).items()}
T["INDPRO"] = {k: -v for k, v in yoy(S["INDPRO"]).items()}
T["CMRMT"]  = {k: -v for k, v in yoy(S["CMRMTSPL"]).items()}
T["TCU"]    = {k: -v for k, v in yoy(S["TCU"]).items()}
T["PHILLY"] = {k: -v for k, v in S["GACDFSA066MSFRBPHI"].items()}
T["NASDAQ"] = {k: -v for k, v in drawdown(S["NASDAQCOM"]).items()}
T["BAAAAA"] = BAAAAA
T["BAA10Y"] = S["BAA10Y"]
T["NFCI"]   = S["NFCI"]
T["VIX"]    = S["VIXCLS"]
T["PERMIT"] = {k: -v for k, v in yoy(S["PERMIT"]).items()}
T["HOUST"]  = {k: -v for k, v in yoy(S["HOUST"]).items()}
T["UMCSENT"]= {k: -v for k, v in drawdown(S["UMCSENT"]).items()}
T["W875"]   = {k: -v for k, v in yoy(S["W875RX1"]).items()}

# ---- chronology 1: USRECD daily 0/1 → contiguous recession windows ----
def usrecd_windows():
    ks = sorted(S["USRECD"]); wins = []; start = None; prev = None
    for k in ks:
        v = S["USRECD"][k]
        if v == 1 and start is None:
            start = k
        elif v == 0 and start is not None:
            wins.append((start, prev)); start = None
        prev = k
    if start is not None: wins.append((start, prev))
    return wins  # (first rec-day, last rec-day) per episode, daily granularity

USRECD_WINS = usrecd_windows()

# ---- chronology 2: RECS (index_v1.py:207) ----
RECS = {"1980":(dt.date(1980,1,1),dt.date(1980,7,1)),"1981-82":(dt.date(1981,7,1),dt.date(1982,11,1)),
 "1990-91":(dt.date(1990,7,1),dt.date(1991,3,1)),"2001":(dt.date(2001,3,1),dt.date(2001,11,1)),
 "2007-09":(dt.date(2007,12,1),dt.date(2009,6,1)),"2020":(dt.date(2020,2,1),dt.date(2020,4,1)),
 "2022-24*":(dt.date(2024,4,1),dt.date(2024,8,1))}

# ---- chronology 3: frozen ledger (READ ONLY) ----
LED = json.load(open(LEDGER))["recession_targets"]
def pd(s): return dt.date(int(s[:4]),int(s[5:7]),int(s[8:10])) if s else None
LEDGER_EPS = [(e["episode_id"], pd(e["onset_T_star"]), pd(e["end"]), pd(e.get("nber_peak_comparator")))
              for e in LED]

# ---- z-standardisation under a supplied recession-day predicate ----
EXCL = [(dt.date(2020,1,1), dt.date(2021,12,31)), (dt.date(2023,1,1), dt.date(2025,6,30))]
def in_excl(d):
    return any(a <= d <= b for a, b in EXCL)

# baseline (a): USRECD recessions (as-now)
_rk = sorted(S["USRECD"])
def in_rec_usrecd(d):
    i = bisect.bisect_right(_rk, d) - 1
    return i >= 0 and S["USRECD"][_rk[i]] == 1

# baseline (b): ledger onset_T_star..end windows as the recession set
LED_WINS = [(o, e) for (_id, o, e, _p) in LEDGER_EPS]
def in_rec_ledger(d):
    return any(o <= d <= e for o, e in LED_WINS)

def zbaseline(in_rec):
    """return {member: (mu, sd)} using is_baseline = not in_rec and not in_excl."""
    res = {}
    for name, series in T.items():
        base = [series[k] for k in sorted(series) if not in_rec(k) and not in_excl(k)]
        mu = sum(base)/len(base)
        sd = (sum((x-mu)**2 for x in base)/len(base))**0.5 or 1.0
        res[name] = (mu, sd, len(base))
    return res

MU_A = zbaseline(in_rec_usrecd)
MU_B = zbaseline(in_rec_ledger)

# ---- headline series under each baseline, sign-flip measurement ----
CHANNELS = {"labor":(0.30,["ICSA","IURSA","SAHM","UNRATEv"]),
 "realactivity":(0.25,["INDPRO","CMRMT","TCU","PHILLY"]),
 "creditequity":(0.20,["NASDAQ","BAAAAA","BAA10Y","VIX"]),
 "finconditions":(0.10,["NFCI"]),
 "housingincome":(0.15,["PERMIT","HOUST","UMCSENT","W875"])}
_KEYS = {name: sorted(series) for name, series in T.items()}
def zval(name, d, MU):
    keys = _KEYS[name]; i = bisect.bisect_right(keys, d) - 1
    if i < 0: return None
    mu, sd, _ = MU[name]
    return (T[name][keys[i]] - mu) / sd
def headline(d, MU):
    tot = wsum = 0.0
    for name,(w,members) in CHANNELS.items():
        vals = [zval(m, d, MU) for m in members]; vals=[v for v in vals if v is not None]
        if vals: tot += w*(sum(vals)/len(vals)); wsum += w
    return tot/wsum if wsum else None

def drange(a,b):
    d=a
    while d<=b: yield d; d+=dt.timedelta(days=1)
flips = 0; maxdelta = 0.0; maxdelta_d = None; n=0
for d in drange(START, END):
    ha = headline(d, MU_A); hb = headline(d, MU_B)
    if ha is None or hb is None: continue
    n += 1
    delta = abs(ha - hb)
    if delta > maxdelta: maxdelta, maxdelta_d = delta, d
    if (ha >= 0) != (hb >= 0): flips += 1

# ---- assemble three-way table ----
def iso(d): return d.isoformat() if d else None
def days_between(a,b):
    return (a-b).days if (a and b) else None

table = {
 "usrecd_windows_all": [[iso(a),iso(b)] for a,b in USRECD_WINS],
 "recs_index_v1_line207": {k:[iso(a),iso(b)] for k,(a,b) in RECS.items()},
 "ledger_frozen": [{"id":i,"onset_T_star":iso(o),"end":iso(e),"nber_peak_comparator":iso(p)}
                   for (i,o,e,p) in LEDGER_EPS],
}

# episode alignment: ledger (13) is superset; map RECS + USRECD onto it by year overlap
def usrecd_win_for(year_lo, year_hi):
    for a,b in USRECD_WINS:
        if a.year<=year_hi and b.year>=year_lo and a>=dt.date(1948,1,1):
            if abs(a.year-year_lo)<=1 or abs(b.year-year_hi)<=1:
                return (a,b)
    return None

# map by nber_peak year for robustness
def usrecd_win_covering(peak):
    if not peak: return None
    for a,b in USRECD_WINS:
        if a <= peak <= b or (a - dt.timedelta(days=45)) <= peak <= (b + dt.timedelta(days=45)):
            return (a,b)
    # nearest window whose start is within ~120d of peak
    best=None; bd=999999
    for a,b in USRECD_WINS:
        dd=abs((a-peak).days)
        if dd<bd: bd, best = dd,(a,b)
    return best if bd<=200 else None

recs_by_year = {}
for k,(a,b) in RECS.items(): recs_by_year[k]=(a,b)
def recs_match(ledger_id, onset, end):
    # explicit product-episode alias first (same episode, different id+dates — the §24.7 defect)
    if ledger_id=="rec_2022_23":
        return ("2022-24*",)+RECS["2022-24*"]
    # otherwise match by window overlap of ledger onset..end vs RECS window
    best=None; bestov=0
    for k,(a,b) in RECS.items():
        if k=="2022-24*": continue
        ov = (min(end,b)-max(onset,a)).days
        if ov>bestov: bestov, best = ov,(k,a,b)
    return best

rows=[]
for (i,o,e,p) in LEDGER_EPS:
    uw = usrecd_win_covering(p or o)
    rm = recs_match(i,o,e)
    row={
      "ledger_id":i,
      "ledger_onset_T_star":iso(o),"ledger_end":iso(e),"ledger_nber_peak":iso(p),
      "usrecd_window":[iso(uw[0]),iso(uw[1])] if uw else None,
      "recs_id": rm[0] if rm else None,
      "recs_window":[iso(rm[1]),iso(rm[2])] if rm else None,
      # disagreements in DAYS
      "onset_minus_nberpeak_days": days_between(o,p),
      "onset_minus_usrecd_start_days": days_between(o, uw[0]) if uw else None,
      "recs_start_minus_ledger_onset_days": days_between(rm[1],o) if rm else None,
      "recs_end_minus_ledger_end_days": days_between(rm[2],e) if rm else None,
      "in_sample_post_START": (o >= START),
    }
    rows.append(row)
table["three_way_rows"]=rows

# z-shift per member A->B
zshift=[]
for name in T:
    muA,sdA,nA = MU_A[name]; muB,sdB,nB = MU_B[name]
    zshift.append({"member":name,
      "mu_a":round(muA,6),"mu_b":round(muB,6),"mu_delta":round(muB-muA,6),
      "sd_a":round(sdA,6),"sd_b":round(sdB,6),"sd_delta":round(sdB-sdA,6),
      "baseline_n_a":nA,"baseline_n_b":nB,
      # z of the latest obs under each baseline (does the reading move?)
      "z_latest_a": round(zval(name, END, MU_A),4) if zval(name,END,MU_A) is not None else None,
      "z_latest_b": round(zval(name, END, MU_B),4) if zval(name,END,MU_B) is not None else None})
for r in zshift:
    if r["z_latest_a"] is not None and r["z_latest_b"] is not None:
        r["z_latest_sign_change"] = (r["z_latest_a"]>=0)!=(r["z_latest_b"]>=0)
        r["z_latest_delta"]=round(r["z_latest_b"]-r["z_latest_a"],4)
table["z_shift_per_member"]=zshift

table["headline_sign_analysis"]={
  "days_compared":n,"sign_flips_a_vs_b":flips,
  "max_abs_headline_delta":round(maxdelta,6),"max_delta_date":iso(maxdelta_d),
  "headline_latest_a":round(headline(END,MU_A),6),"headline_latest_b":round(headline(END,MU_B),6),
  "any_headline_sign_change": flips>0}

table["meta"]={
  "START":iso(START),"END":iso(END),
  "raw_dir":os.path.relpath(RAW,ROOT),
  "note":"read-only; no store byte, ledger, or value modified. nowcast fills NOT injected (baseline mu/sd only)."}

json.dump(table, open(os.path.join(OUT,"three_way_table.v1.json"),"w"), indent=2)
print("WROTE three_way_table.v1.json")
print(f"USRECD windows total: {len(USRECD_WINS)} (all history 1854+)")
print(f"ledger episodes: {len(LEDGER_EPS)}   RECS episodes: {len(RECS)}")
print(f"headline days compared: {n}  sign_flips A->B: {flips}  max|delta|: {maxdelta:.4f} @ {iso(maxdelta_d)}")
print(f"headline latest A: {headline(END,MU_A):+.4f}  B: {headline(END,MU_B):+.4f}")
print("\nper-member z_latest A vs B (sign change flagged):")
for r in zshift:
    sc = r.get("z_latest_sign_change")
    print(f"  {r['member']:8} mudelta {r['mu_delta']:+.4f} sddelta {r['sd_delta']:+.4f} "
          f"zA {r['z_latest_a']} zB {r['z_latest_b']} signchg {sc}")
