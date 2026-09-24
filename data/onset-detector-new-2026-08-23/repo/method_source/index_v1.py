#!/usr/bin/env python3
"""Recession Seismograph v1 — coincident daily recession index, 1976+.
Decisions locked: official line starts 1976-06; FRED-only backbone; current-vintage;
yield curve held OUT of the headline (separate leading gauge). Every reading is a
signed deterioration z (positive = more recessionary) standardized against a clean
expansion baseline (NBER recessions, COVID, and the 2022-24 ambiguous window excluded).
Channels collapse collinear members, then combine with fixed published weights."""
import csv, datetime as dt, math

RAW = "raw/"
def load(sid):
    out = {}
    for r in csv.reader(open(RAW + sid + ".csv")):
        if r[0][0:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            out[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
    return out

S = {s: load(s) for s in ["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU",
     "GACDFSA066MSFRBPHI","NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST","PERMIT",
     "UMCSENT","W875RX1","GS10","GS1","USRECD",
     # live-edge nowcast bridge inputs (used only by nowcast_live; not headline members)
     "RRSFS","MORTGAGE30US","PAYEMS","CCSA","DBAA","DAAA"]}
# BAA-AAA quality spread (monthly)
BAAAAA = {d: S["BAA"][d] - S["AAA"][d] for d in S["BAA"] if d in S["AAA"]}
# curve (leading gauge, not in headline): GS10-GS1 monthly
CURVE = {d: S["GS10"][d] - S["GS1"][d] for d in S["GS10"] if d in S["GS1"]}

START = dt.date(1976, 6, 1)
END = max(max(S[k]) for k in ("ICSA","NASDAQCOM","VIXCLS","NFCI","BAA10Y"))
def drange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)
DAYS = list(drange(START, END))

import bisect
_ASOF_KEYS = {}
def asof(series, d):
    """last value at or before d (step function carry-forward); binary search."""
    kid = id(series)
    keys = _ASOF_KEYS.get(kid)
    if keys is None:
        keys = sorted(series); _ASOF_KEYS[kid] = keys
    i = bisect.bisect_right(keys, d) - 1
    return series[keys[i]] if i >= 0 else None
# recession-day set as a fast lookup (USRECD is a daily 0/1 step series)
_REC_KEYS = None
def in_recession_fast(d, urd):
    global _REC_KEYS
    if _REC_KEYS is None: _REC_KEYS = sorted(urd)
    i = bisect.bisect_right(_REC_KEYS, d) - 1
    return i >= 0 and urd[_REC_KEYS[i]] == 1

import bisect as _bi
def yoy(series):
    """year-over-year % change, keyed by date (nearest prior obs ~365d back)."""
    out = {}; ks = sorted(series)
    for k in ks:
        prior = k - dt.timedelta(days=365)
        i = _bi.bisect_left(ks, prior)
        cand = [x for x in (ks[max(0,i-1):i+2]) if abs((x - prior).days) <= 20]
        if cand:
            p = min(cand, key=lambda x: abs((x - prior).days))
            if series[p] != 0: out[k] = (series[k] / series[p] - 1) * 100
    return out

def _window_extreme(series, look, fn):
    """sliding-window extreme over trailing `look` days; O(n)."""
    out = {}; ks = sorted(series); vals = [series[k] for k in ks]
    lo = 0
    from collections import deque
    dq = deque()  # indices, monotonic
    ismax = (fn is max)
    for i, k in enumerate(ks):
        while lo < i and (k - ks[lo]).days > look: lo += 1
        while dq and dq[0] < lo: dq.popleft()
        while dq and ((vals[dq[-1]] <= vals[i]) if ismax else (vals[dq[-1]] >= vals[i])): dq.pop()
        dq.append(i)
        out[k] = vals[dq[0]]
    return out, ks, vals

def drawdown(series):
    """% below trailing 12-month max."""
    mx, ks, vals = _window_extreme(series, 370, max)
    return {k: (series[k]/mx[k]-1)*100 if mx[k] else 0 for k in ks}

def rise_floor(series, look=370):
    """Sahm-style: current minus trailing-min."""
    mn, ks, vals = _window_extreme(series, look, min)
    return {k: series[k]-mn[k] for k in ks}

# ---- per-metric deterioration transforms, oriented so HIGHER = more recessionary ----
T = {}
T["ICSA"]   = yoy(S["ICSA"])                                   # claims up = bad
T["IURSA"]  = rise_floor(S["IURSA"])                           # insured-U rate rise = bad
T["SAHM"]   = S["SAHMREALTIME"]                                # already deterioration
T["UNRATEv"]= {k: v for k, v in rise_floor(S["UNRATE"], 120).items()}  # 3-4mo rise
T["INDPRO"] = {k: -v for k, v in yoy(S["INDPRO"]).items()}     # output down = bad
T["CMRMT"]  = {k: -v for k, v in yoy(S["CMRMTSPL"]).items()}
T["TCU"]    = {k: -v for k, v in yoy(S["TCU"]).items()}
T["PHILLY"] = {k: -v for k, v in S["GACDFSA066MSFRBPHI"].items()}   # diffusion <0 = contraction
T["NASDAQ"] = {k: -v for k, v in drawdown(S["NASDAQCOM"]).items()}  # drawdown (neg) -> flip to positive
T["BAAAAA"] = BAAAAA
T["BAA10Y"] = S["BAA10Y"]
T["NFCI"]   = S["NFCI"]
T["VIX"]    = S["VIXCLS"]
T["PERMIT"] = {k: -v for k, v in yoy(S["PERMIT"]).items()}
T["HOUST"]  = {k: -v for k, v in yoy(S["HOUST"]).items()}
T["UMCSENT"]= {k: -v for k, v in drawdown(S["UMCSENT"]).items()}
T["W875"]   = {k: -v for k, v in yoy(S["W875RX1"]).items()}

# ---- clean expansion baseline: exclude NBER recessions, COVID, and 2022-24 window ----
def in_recession(d):
    return in_recession_fast(d, S["USRECD"])
EXCL = [(dt.date(2020,1,1), dt.date(2021,12,31)),   # COVID + rebound distortion
        (dt.date(2023,1,1), dt.date(2025,6,30))]     # 2022-24 miss + aftermath (ambiguous)
def is_baseline(d):
    if in_recession(d): return False
    for a, b in EXCL:
        if a <= d <= b: return False
    return True

# standardize each transform to z vs expansion baseline
Z = {}
MU, SD = {}, {}   # stashed baseline mean/sd per member (for the live-edge nowcast)
for name, series in T.items():
    ks = sorted(series)
    base = [series[k] for k in ks if is_baseline(k)]
    mu = sum(base) / len(base)
    sd = (sum((x - mu)**2 for x in base) / len(base))**0.5 or 1.0
    MU[name], SD[name] = mu, sd
    Z[name] = ({k: (series[k] - mu) / sd for k in ks}, sorted(series))

import bisect
def zval(name, d):
    series, keys = Z[name]
    i = bisect.bisect_right(keys, d) - 1
    return series[keys[i]] if i >= 0 else None

# ---- live-edge nowcast: replace carry-forward D0 with the validated STACK ----
# (bridge fills + revision-bias correction) for UNPUBLISHED months of stale members
# ONLY. Fills are keyed strictly after each member's last real obs, so every day at
# or before nowcast_from returns the exact same z as before; only days > nowcast_from
# move. We compute the fills here but INJECT them AFTER the expansion baseline
# (exp_mu/exp_sd) is fixed from the carry-forward line, so the frozen baseline and all
# published history are byte-identical to the pre-nowcast build. Disable: NOWCAST_DISABLE=1.
import os as _os
nowcast_from = None
_fills = {}
if not _os.environ.get("NOWCAST_DISABLE"):
    from nowcast_live import live_edge_fills
    _fills, nowcast_from = live_edge_fills(S, MU, SD, END)

# ---- channels (collapse collinear members), then fixed weights ----
CHANNELS = {
 "labor":       (0.30, ["ICSA","IURSA","SAHM","UNRATEv"]),
 "realactivity":(0.25, ["INDPRO","CMRMT","TCU","PHILLY"]),
 "creditequity":(0.20, ["NASDAQ","BAAAAA","BAA10Y","VIX"]),
 "finconditions":(0.10, ["NFCI"]),
 "housingincome":(0.15, ["PERMIT","HOUST","UMCSENT","W875"]),
}
def channel_score(members, d):
    vals = [zval(m, d) for m in members]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None

def headline(d):
    tot = 0.0; wsum = 0.0
    for name, (w, members) in CHANNELS.items():
        cs = channel_score(members, d)
        if cs is not None:
            tot += w * cs; wsum += w
    return tot / wsum if wsum else None   # renormalize over available channels

# ---- build daily line ----
line = {d: headline(d) for d in DAYS}
line = {d: v for d, v in line.items() if v is not None}

# ---- backtest: AUROC vs USRECD, per-recession hump ----
def auroc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg: return None
    # rank-based AUROC
    allv = sorted(pos + neg)
    rank = {}; i = 0
    srt = sorted(range(len(pos+neg)), key=lambda j: (pos+neg)[j])
    combined = pos + neg
    order = sorted(combined)
    # simple O(n log n) via rank sum
    import statistics
    vals = sorted((v, 1) for v in pos)
    vals += sorted((v, 0) for v in neg)
    vals.sort()
    r = 0; rsum = 0
    for idx, (v, lab) in enumerate(vals, 1):
        if lab == 1: rsum += idx
    n1 = len(pos); n0 = len(neg)
    return (rsum - n1*(n1+1)/2) / (n1*n0)

sc = [line[d] for d in DAYS if d in line]
lb = [1 if in_recession(d) else 0 for d in DAYS if d in line]
print(f"Daily index built: {DAYS[0]} .. {DAYS[-1]}, {len(line)} days")
print(f"AUROC vs NBER (USRECD): {auroc(sc, lb):.4f}")

RECS = {"1980":(dt.date(1980,1,1),dt.date(1980,7,1)),"1981-82":(dt.date(1981,7,1),dt.date(1982,11,1)),
 "1990-91":(dt.date(1990,7,1),dt.date(1991,3,1)),"2001":(dt.date(2001,3,1),dt.date(2001,11,1)),
 "2007-09":(dt.date(2007,12,1),dt.date(2009,6,1)),"2020":(dt.date(2020,2,1),dt.date(2020,4,1)),
 "2022-24*":(dt.date(2024,4,1),dt.date(2024,8,1))}
exp_vals = [line[d] for d in line if is_baseline(d)]
exp_mu = sum(exp_vals)/len(exp_vals); exp_sd=(sum((x-exp_mu)**2 for x in exp_vals)/len(exp_vals))**.5
print(f"\nexpansion baseline: mean {exp_mu:+.2f}, sd {exp_sd:.2f}")

# ---- NOW inject the live-edge nowcast (baseline is frozen above) and recompute
# ONLY the edge of the line (days >= nowcast_from). Days < nowcast_from are untouched.
if _fills:
    for _name, _evs in _fills.items():
        _series, _keys = Z[_name]
        for _obs, _z in _evs:      # every _obs is strictly AFTER the last real obs
            _series[_obs] = _z     # append-only; never overwrites a published key
        Z[_name] = (_series, sorted(_series))
    for d in DAYS:
        if d >= nowcast_from:
            v = headline(d)
            if v is not None: line[d] = v
print(f"{'episode':10} {'peak index':>11} {'sigma above expansion':>22}")
for nm,(a,b) in RECS.items():
    w = [line[d] for d in line if a <= d <= b]
    if w:
        pk = max(w); print(f"{nm:10} {pk:>11.2f} {(pk-exp_mu)/exp_sd:>20.1f}σ")

# latest per-channel readings (as of the last day), with member detail
channels_latest = {}
for name, (w, members) in CHANNELS.items():
    vals = [(m, zval(m, END)) for m in members]
    vals = [(m, v) for m, v in vals if v is not None]
    channels_latest[name] = {
        "v": round(sum(v for _, v in vals)/len(vals), 2) if vals else None,
        "members": {m: round(v, 2) for m, v in vals}}

# save the line + curve gauge for charting
import json
_out = _os.environ.get("INDEX_OUT", "index_v1_out.json")
json.dump({"line": {d.isoformat(): v for d, v in line.items()},
           "channels_latest": channels_latest,
           "curve": {d.isoformat(): asof(CURVE, d) for d in DAYS[::7]},
           "recessions": {k: [a.isoformat(), b.isoformat()] for k,(a,b) in RECS.items()},
           "exp_mu": exp_mu, "exp_sd": exp_sd,
           "nowcast_from": nowcast_from.isoformat() if nowcast_from else None},
          open(_out, "w"))
print(f"\nsaved {_out}  (nowcast_from={nowcast_from})")
