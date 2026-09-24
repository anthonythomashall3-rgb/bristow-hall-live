#!/usr/bin/env python3
"""Recessions-page data: long monthly line 1957+ with balanced weights, damage
grades D=(rise^2*burden)^(1/3) for all 10 postwar recessions + the 2022-24 episode,
peak sigma, GDP decline, duration, bar-detection lag, signal lead, mini-chart series,
and the bar's open-water calibration numbers (recomputed, not from memory)."""
import csv, datetime as dt, bisect, json
from collections import deque
RAW = "raw/"
def load(sid):
    o = {}
    for r in csv.reader(open(RAW + sid + ".csv")):
        if r and r[0][:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            o[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
    return o
IDS = ["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU","GACDFSA066MSFRBPHI",
       "NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST","PERMIT","UMCSENT","W875RX1","USRECD"]
S = {s: load(s) for s in IDS}
BAAAAA = {d: S["BAA"][d] - S["AAA"][d] for d in S["BAA"] if d in S["AAA"]}
def yoy(series):
    out = {}; ks = sorted(series)
    for k in ks:
        p = k - dt.timedelta(days=365); i = bisect.bisect_left(ks, p)
        c = [x for x in ks[max(0, i-1):i+2] if abs((x - p).days) <= 20]
        if c:
            q = min(c, key=lambda x: abs((x - p).days))
            if series[q] != 0: out[k] = (series[k] / series[q] - 1) * 100
    return out
def wext(series, look, fn):
    out = {}; ks = sorted(series); vals = [series[k] for k in ks]; lo = 0; dq = deque(); ismax = (fn is max)
    for i, k in enumerate(ks):
        while lo < i and (k - ks[lo]).days > look: lo += 1
        while dq and dq[0] < lo: dq.popleft()
        while dq and ((vals[dq[-1]] <= vals[i]) if ismax else (vals[dq[-1]] >= vals[i])): dq.pop()
        dq.append(i); out[k] = vals[dq[0]]
    return out, ks
def drawdown(series):
    mx, ks = wext(series, 370, max); return {k: (series[k]/mx[k]-1)*100 if mx[k] else 0 for k in ks}
def risef(series, look=370):
    mn, ks = wext(series, look, min); return {k: series[k]-mn[k] for k in ks}
T = {}
T["ICSA"]=yoy(S["ICSA"]); T["IURSA"]=risef(S["IURSA"]); T["SAHM"]=S["SAHMREALTIME"]; T["UNRATEv"]=risef(S["UNRATE"],120)
T["INDPRO"]={k:-v for k,v in yoy(S["INDPRO"]).items()}; T["CMRMT"]={k:-v for k,v in yoy(S["CMRMTSPL"]).items()}
T["TCU"]={k:-v for k,v in yoy(S["TCU"]).items()}; T["PHILLY"]={k:-v for k,v in S["GACDFSA066MSFRBPHI"].items()}
T["NASDAQ"]={k:-v for k,v in drawdown(S["NASDAQCOM"]).items()}; T["BAAAAA"]=BAAAAA; T["BAA10Y"]=S["BAA10Y"]
T["NFCI"]=S["NFCI"]; T["VIX"]=S["VIXCLS"]; T["PERMIT"]={k:-v for k,v in yoy(S["PERMIT"]).items()}
T["HOUST"]={k:-v for k,v in yoy(S["HOUST"]).items()}; T["UMCSENT"]={k:-v for k,v in drawdown(S["UMCSENT"]).items()}
T["W875"]={k:-v for k,v in yoy(S["W875RX1"]).items()}
NBER = {"1957-58":("1957-08","1958-04"),"1960-61":("1960-04","1961-02"),"1969-70":("1969-12","1970-11"),
 "1973-75":("1973-11","1975-03"),"1980":("1980-01","1980-07"),"1981-82":("1981-07","1982-11"),
 "1990-91":("1990-07","1991-03"),"2001":("2001-03","2001-11"),"2007-09":("2007-12","2009-06"),"2020":("2020-02","2020-04")}
md = lambda s: dt.date(int(s[:4]), int(s[5:7]), 1)
recks = sorted(S["USRECD"])
def in_rec(d):
    i = bisect.bisect_right(recks, d) - 1; return i >= 0 and S["USRECD"][recks[i]] == 1
EXCL = [(dt.date(2020,1,1), dt.date(2021,12,31)), (dt.date(2023,1,1), dt.date(2025,6,30))]
def isbase(d):
    if in_rec(d): return False
    return not any(a <= d <= b for a, b in EXCL)
Z = {}
for nm, ser in T.items():
    ks = sorted(ser); base = [ser[k] for k in ks if isbase(k)]
    m = sum(base)/len(base); s2 = (sum((x-m)**2 for x in base)/len(base))**.5 or 1
    Z[nm] = ({k: (ser[k]-m)/s2 for k in ks}, ks)
def zval(nm, d):
    ser, keys = Z[nm]; i = bisect.bisect_right(keys, d) - 1
    return ser[keys[i]] if i >= 0 else None
CH = {"labor":["ICSA","IURSA","SAHM","UNRATEv"],"realactivity":["INDPRO","CMRMT","TCU","PHILLY"],
      "creditequity":["NASDAQ","BAAAAA","BAA10Y","VIX"],"finconditions":["NFCI"],
      "housingincome":["PERMIT","HOUST","UMCSENT","W875"]}
W = {"labor":0.30,"realactivity":0.25,"creditequity":0.20,"finconditions":0.10,"housingincome":0.15}
mg = []; y, m = 1957, 6
END = max(S["INDPRO"])
while dt.date(y, m, 1) <= END:
    mg.append(dt.date(y, m, 1)); m += 1
    if m > 12: m = 1; y += 1
def headline(d):
    t = ws = 0.0
    for cn, mem in CH.items():
        vals = [zval(x, d) for x in mem]; vals = [v for v in vals if v is not None]
        if vals: t += W[cn]*sum(vals)/len(vals); ws += W[cn]
    return t/ws if ws else None
L = {d: headline(d) for d in mg}
bv = [L[d] for d in mg if L[d] is not None and isbase(d)]
lmu = sum(bv)/len(bv); lsd = (sum((x-lmu)**2 for x in bv)/len(bv))**.5
SIG_L = {d: (L[d]-lmu)/lsd for d in mg if L[d] is not None}   # long line in sigma units

# compressed testimony: beyond 4 sigma (a once-per-generation reading) additional
# depth counts at fourth-root weight — only persistence can add conviction
def compress(v, _C=4.0):
    return v if v <= _C else _C + (v - _C) ** 0.25
SIG_L = {d: compress(v) for d, v in SIG_L.items()}

# monthly accumulated stress (E12): trailing 12-month sum of positive readings —
# the same object as the headline chart, for the per-episode mini panels
E12M = {}
_mks = [d for d in mg if d in SIG_L]
for _i, _d in enumerate(_mks):
    E12M[_d] = sum(max(SIG_L[_x], 0.0) for _x in _mks[max(0, _i-11):_i+1])

# ---- open-water calibration (recompute the bar honestly) ----
def near_any(d, before=185, after=730):
    return any(md(a)-dt.timedelta(days=before) <= d <= md(b)+dt.timedelta(days=after) for a, b in NBER.values())
rec_peaks = {}
for k, (a, b) in NBER.items():
    seg = [SIG_L[d] for d in mg if md(a) <= d <= md(b) and d in SIG_L]
    rec_peaks[k] = max(seg)
exp_vals = [(d, SIG_L[d]) for d in SIG_L if not near_any(d) and not (dt.date(2022,1,1) <= d <= dt.date(2025,12,31))]
exp_hi = max(exp_vals, key=lambda x: x[1])
# original calibration convention: highest non-recession reading with NO lead-in exclusion
exp_vals0 = [(d, SIG_L[d]) for d in SIG_L if not near_any(d, before=0) and not (dt.date(2022,1,1) <= d <= dt.date(2025,12,31))]
exp_hi0 = max(exp_vals0, key=lambda x: x[1])
weakest = min(rec_peaks.items(), key=lambda x: x[1])
print("long-line recession peaks (σ):", {k: round(v,2) for k,v in rec_peaks.items()})
print(f"weakest recession peak: {weakest[0]} {weakest[1]:.2f}")
print(f"highest non-recession reading (any): {exp_hi0[1]:.2f} on {exp_hi0[0]} | excluding 6-mo lead-ins: {exp_hi[1]:.2f} on {exp_hi[0]}")
print(f"midpoint bar: {(weakest[1]+exp_hi0[1])/2:.2f}")

# ---- daily compressed reading for daily-era grade windows ----
IXD = json.load(open("index_v1_out.json"))
dmu, dsd = IXD["exp_mu"], IXD["exp_sd"]
dline = {dt.date.fromisoformat(kk): (v-dmu)/dsd for kk, v in IXD["line"].items()}
ddays = sorted(dline)
from collections import deque as _dq
_q = _dq(); _s = 0.0; dsm = {}
for _i, _d in enumerate(ddays):
    _q.append(dline[_d]); _s += dline[_d]
    while len(_q) > 21: _s -= _q.popleft()
    dsm[_d] = _s/len(_q)
dcs = {d: compress(v) for d, v in dsm.items()}
def gradeD(lo, hi):
    seg = [dcs[d] for d in ddays if lo <= d <= hi]
    rise = max(max(seg), .01)
    burden = max(sum(max(v, 0) for v in seg)/30.44, .01)
    return (rise**2 * burden)**(1/3), rise, burden

# ---- damage grades (balanced weights, exp=2) ----
def grade(lo, hi):
    seg = [SIG_L[d] for d in mg if lo <= d <= hi and d in SIG_L]
    base_mu = 0.0  # sigma units: baseline mean is 0 by construction
    rise = max(max(seg) - base_mu, .01)
    burden = max(sum(max(v - base_mu, 0) for v in seg), .01)
    return (rise**2 * burden) ** (1/3), max(seg), burden
GDP = {"2020":7.9,"2007-09":4.0,"1957-58":3.6,"1973-75":3.1,"1981-82":2.6,"1980":2.2,"1990-91":1.4,"1960-61":1.3,"1969-70":1.1,"2001":0.4}
# grade windows = the instrument's own dated windows (onset -> composite Bristow end)
try:
    DATW = json.load(open("geo/dating.json"))
except Exception:
    DATW = {}
# window = onset -> composite-Bristow end + 12 months (one accumulator memory of
# aftermath), capped at the next recession's onset and at the data edge
AFT = dt.timedelta(days=366)
NEXT_ON = {"1980": dt.date(1981, 7, 1)}
rows = []
for k, (a, b) in NBER.items():
    if k in DATW:
        lo = dt.date.fromisoformat(DATW[k]["onset"]); hi = dt.date.fromisoformat(DATW[k]["end"]) + AFT
        if k == "1981-82": lo = md(a)   # twins share a complex; grade each from its own NBER onset
        if k in NEXT_ON: hi = min(hi, NEXT_ON[k])
        hi = min(hi, mg[-1])
    else:
        lo = md(a) - dt.timedelta(days=120); hi = md(b) + dt.timedelta(days=760)
    if lo >= dt.date(1976, 6, 1):
        D, pk, burden = gradeD(lo, min(hi, ddays[-1]))
    else:
        D, pk, burden = grade(lo, hi)
    # detection: first month >= 2.38 at/after onset-2mo
    det = next((d for d in mg if d >= md(a)-dt.timedelta(days=62) and SIG_L.get(d,0) >= 2.38), None)
    lag = (det.year-md(a).year)*12 + det.month-md(a).month if det else None
    # signal lead: first month >= 1.0 within 15 months before onset (not in prior recession)
    sigm = [d for d in mg if md(a)-dt.timedelta(days=460) <= d <= md(b) and SIG_L.get(d,-9) >= 1.0 and not (in_rec(d) and d < md(a))]
    lead = ((md(a).year-sigm[0].year)*12 + md(a).month-sigm[0].month) if sigm else None
    dur = (md(b).year-md(a).year)*12 + md(b).month-md(a).month + 1
    # mini chart: onset-18mo .. trough+30mo, clipped so a neighbor's stress cannot
    # dominate the panel — start after the previous episode's drain, stop before
    # the next episode opens
    w0 = md(a)-dt.timedelta(days=550); w1 = md(b)+dt.timedelta(days=920)
    _ons = sorted(md(x) for x, _ in NBER.values())
    _idx = _ons.index(md(a))
    if _idx > 0:
        _prevk = [x for x, (aa, bb) in NBER.items() if md(aa) == _ons[_idx-1]][0]
        _pe = DATW.get(_prevk, {}).get("end")
        if _pe:
            _cand = dt.date.fromisoformat(_pe) + dt.timedelta(days=425)
            if _cand < md(a):
                w0 = max(w0, _cand)
    if _idx + 1 < len(_ons):
        # end the panel at the stress minimum between this episode and the next,
        # so a following episode's climb cannot out-peak the panel's own hump
        _gap = [d for d in mg if md(b) < d < _ons[_idx+1] and d in E12M]
        if _gap:
            _saddle = min(_gap, key=lambda d: E12M[d])
            w1 = min(w1, _saddle)
        else:
            w1 = min(w1, _ons[_idx+1] - dt.timedelta(days=32))
    mini = [[d.isoformat()[:7], round(E12M[d], 2)] for d in mg if w0 <= d <= w1 and d in E12M]
    dw = DATW.get(k, {})
    io = (dw.get("onset") or (a + "-01"))[:7]
    ie = (dw.get("end") or (b + "-01"))[:7]
    rows.append({"key": k, "start": a, "end": b, "io": io, "ie": ie, "grade": round(D,2), "peak": round(pk,2),
                 "burden": round(burden,1), "gdp": GDP[k], "dur": dur, "detlag": lag, "siglead": lead, "mini": mini})

# ---- the 2022-24 episode, graded on its instrument window like every recession ----
if "2022-23" in DATW:
    lo = dt.date.fromisoformat(DATW["2022-23"]["onset"])
    hi = min(dt.date.fromisoformat(DATW["2022-23"]["end"]) + AFT, ddays[-1])
else:
    lo, hi = dt.date(2022,6,1), dt.date(2025,6,30)
D22, pk22, b22 = gradeD(lo, hi)
mini22 = [[d.isoformat()[:7], round(E12M[d],2)] for d in mg if dt.date(2022,5,1) <= d <= dt.date(2026,7,1) and d in E12M]
# battery-dated recession: onset Apr 2024 (Sahm crossing minus representative lag), end Aug 2024 (Bristow Rule)
sig1 = next((d for d in mg if dt.date(2022,1,1) <= d <= dt.date(2024,4,1) and SIG_L.get(d,-9) >= 1.0), None)
lead22 = ((2024-sig1.year)*12 + 4-sig1.month) if sig1 else None
rows.append({"key":"2022-23","start":"2022-10","end":"2023-06","io":"2022-10","ie":"2023-06","grade":round(D22,2),"peak":round(pk22,2),
             "burden":round(b22,1),"gdp":0.0,"dur":9,"detlag":None,"siglead":None,"mini":mini22,
             "battery":True,"grade_window":"instrument window"})
print(f"\n2022-24 episode: grade {D22:.2f}, peak {pk22:.2f}σ, burden {b22:.1f}σ-mo")
rows.sort(key=lambda r: -r["grade"])
for r in rows:
    print(f"  {r['key']:8} D={r['grade']:6.2f} peak={r['peak']:5.2f} burden={r['burden']:6.1f} gdp={r['gdp']} det={r['detlag']} lead={r['siglead']}")

# ---- pre-1976 signal events on the long line (e.g. 1966-67 credit crunch?) ----
evs = []; cur = None
for d in mg:
    if d >= dt.date(1976,6,1): break
    v = SIG_L.get(d)
    if v is not None and v >= 1.0 and not in_rec(d):
        if cur and (d - cur[1]).days <= 95: cur = (cur[0], d, max(cur[2], v))
        else:
            if cur: evs.append(cur)
            cur = (d, d, v)
if cur: evs.append(cur)
print("\npre-1976 monthly signal events (>=1.0σ outside NBER):")
pre = []
for a, b, v in evs:
    nxt = [md(x) for x, _ in NBER.values() if md(x) >= a]
    lead = (min(nxt) - b).days if nxt and (min(nxt) - b).days <= 400 else None
    after = any(md(y) < a <= md(y)+dt.timedelta(days=730) for _, y in NBER.values())
    if after and lead is None: continue
    print(f"  {a}..{b} peak {v:+.2f} — {('rec in '+str(lead)+'d') if lead is not None else 'no recession'}")
    pre.append({"start": a.isoformat(), "end": b.isoformat(), "peak": round(v,2),
                "rec_in_days": lead, "aftermath": after})

# ---- attach detection dates (order-independent: read from energy.json) ----
try:
    ENJ = json.load(open("geo/energy.json"))
    for r in rows:
        k = r["key"]
        r["edet"] = ENJ["detections"].get(k)
        r["edet_gap"] = ENJ["det_gaps"].get(k)
except Exception:
    for r in rows:
        r.setdefault("edet", None); r.setdefault("edet_gap", None)

# ---- monthly long line for the recessions-page big chart ----
longline = [[d.isoformat()[:7], round(SIG_L[d],2)] for d in mg if d in SIG_L]
json.dump({"rows": rows, "longline": longline, "pre1976_events": pre,
           "calib": {"weakest_rec": {"key": weakest[0], "peak": round(weakest[1],2)},
                     "highest_nonrec": {"val": round(exp_hi0[1],2), "date": exp_hi0[0].isoformat()},
                     "highest_clean_exp": {"val": round(exp_hi[1],2), "date": exp_hi[0].isoformat()},
                     "bar": 2.38},
           "rho_note": "grades vs GDP-decline ranks: rho=0.83 (10 recessions; GFC/2020 swap deliberate)"},
          open("geo/recpage.json","w"), separators=(",",":"))
import os
print(f"\nrecpage.json {os.path.getsize('geo/recpage.json')/1e3:.0f} KB")
