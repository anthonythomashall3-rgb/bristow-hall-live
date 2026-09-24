#!/usr/bin/env python3
"""Nowcast evaluation harness for the Bristow-Hall Recession Monitor.

Implements research/NOWCAST_RESEARCH.md section 3 on the daily grid (G2).

Ground truth: reading_final(t) = the Monitor's daily reading from today's full
data. The live site stores this in geo/series.json nat.sm (sigma units x100).
We RECONSTRUCT the identical pipeline (index_v1 headline -> standardize by frozen
exp_mu/exp_sd -> 21-day trailing mean -> compress) so that final and as-of
readings share one arithmetic and the per-member gap is exact; the reconstruction
is validated against nat.raw/nat.sm.

Backtest world: reading_asof(t) uses only inputs publishable by t. Staleness is
modelled with the publication-lag grid taken from leading_daily.py
(daily t+1, weekly t+6, monthly-labor t+38, monthly-other t+45..55). Revision is
modelled for the four series the revision-bias lens targets (INDPRO, CMRMTSPL,
W875RX1, NFCI) by injecting the real first-print vs final gap measured from the
repo's own ALFRED vintage archive (raw/vintages/). All other members carry the
final value (staleness only), matching the task's explicit pub-lag instruction.

Candidates (all fills trained ONLY on data <= 2011-12-31, evaluated 2012+):
  (0) D0  carry-forward baseline (incumbent: last published value held).
  (a) BRIDGES  per-input bridge fills (nc_data_*.md validated maps).
  (b) REVISION D3 maturity-lagged expanding-mean bias correction (nc_method_revision-bias.md).
  D4  STACK = BRIDGES + REVISION with the no-double-count composition rule.

Outputs (scratchpad): nowcast_results.json, nowcast_findings.md.
Repo idiom: stdlib dict+bisect for point-in-time series, numpy on the daily grid.
"""
import csv, os, json, bisect, glob
import datetime as dt
import numpy as np

R = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(R, "raw")
VIN = os.path.join(RAW, "vintages")
SCRATCH = "/private/tmp/claude-501/-Users-anthonyhall-Desktop/865e4f47-aeb5-4222-9e65-c1bc8e866b3f/scratchpad"

# ----------------------------------------------------------------------------
# 1. load final data (current vintage) -- same reader as index_v1.py
# ----------------------------------------------------------------------------
def load(sid, root=RAW):
    out = {}
    p = os.path.join(root, sid + ".csv")
    for r in csv.reader(open(p)):
        if r and r[0][:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            out[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
    return out

SERIES_IDS = ["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU",
    "GACDFSA066MSFRBPHI","NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST",
    "PERMIT","UMCSENT","W875RX1","GS10","GS1","USRECD",
    # bridge inputs
    "RRSFS","MORTGAGE30US","PAYEMS","CCSA","DBAA","DAAA"]
S = {s: load(s) for s in SERIES_IDS}
S["BAAAAA"] = {d: S["BAA"][d] - S["AAA"][d] for d in S["BAA"] if d in S["AAA"]}

# ----------------------------------------------------------------------------
# 2. transforms (verbatim logic from index_v1.py)
# ----------------------------------------------------------------------------
def yoy(series):
    out = {}; ks = sorted(series)
    for k in ks:
        prior = k - dt.timedelta(days=365)
        i = bisect.bisect_left(ks, prior)
        cand = [x for x in ks[max(0, i-1):i+2] if abs((x - prior).days) <= 20]
        if cand:
            p = min(cand, key=lambda x: abs((x - prior).days))
            if series[p] != 0:
                out[k] = (series[k] / series[p] - 1) * 100
    return out

def _window_extreme(series, look, fn):
    from collections import deque
    ks = sorted(series); vals = [series[k] for k in ks]
    lo = 0; dq = deque(); out = {}; ismax = (fn is max)
    for i, k in enumerate(ks):
        while lo < i and (k - ks[lo]).days > look: lo += 1
        while dq and dq[0] < lo: dq.popleft()
        while dq and ((vals[dq[-1]] <= vals[i]) if ismax else (vals[dq[-1]] >= vals[i])): dq.pop()
        dq.append(i); out[k] = vals[dq[0]]
    return out

def drawdown(series):
    mx = _window_extreme(series, 370, max)
    return {k: (series[k]/mx[k]-1)*100 if mx[k] else 0 for k in sorted(series)}

def rise_floor(series, look=370):
    mn = _window_extreme(series, look, min)
    return {k: series[k]-mn[k] for k in sorted(series)}

def neg(d): return {k: -v for k, v in d.items()}

def sahm_from_unrate(un):
    """3-month-avg minus trailing-12mo min of the 3-mo avg (Sahm real-time proxy)."""
    ks = sorted(un)
    avg = {}
    for i, k in enumerate(ks):
        w = [un[ks[j]] for j in range(max(0, i-2), i+1)]
        avg[k] = sum(w)/len(w)
    return rise_floor(avg, 370)

# member -> transformed final series {obs_date: value}
def build_final_transforms(SS):
    T = {}
    T["ICSA"]   = yoy(SS["ICSA"])
    T["IURSA"]  = rise_floor(SS["IURSA"])
    T["SAHM"]   = dict(SS["SAHMREALTIME"])
    T["UNRATEv"]= rise_floor(SS["UNRATE"], 120)
    T["INDPRO"] = neg(yoy(SS["INDPRO"]))
    T["CMRMT"]  = neg(yoy(SS["CMRMTSPL"]))
    T["TCU"]    = neg(yoy(SS["TCU"]))
    T["PHILLY"] = neg(SS["GACDFSA066MSFRBPHI"])
    T["NASDAQ"] = neg(drawdown(SS["NASDAQCOM"]))
    T["BAAAAA"] = dict(SS["BAAAAA"])
    T["BAA10Y"] = dict(SS["BAA10Y"])
    T["NFCI"]   = dict(SS["NFCI"])
    T["VIX"]    = dict(SS["VIXCLS"])
    T["PERMIT"] = neg(yoy(SS["PERMIT"]))
    T["HOUST"]  = neg(yoy(SS["HOUST"]))
    T["UMCSENT"]= neg(drawdown(SS["UMCSENT"]))
    T["W875"]   = neg(yoy(SS["W875RX1"]))
    return T

T = build_final_transforms(S)

# ----------------------------------------------------------------------------
# 3. frozen baselines (final vintage), exactly index_v1.py's is_baseline
# ----------------------------------------------------------------------------
_REC = sorted(S["USRECD"])
def in_recession(d):
    i = bisect.bisect_right(_REC, d) - 1
    return i >= 0 and S["USRECD"][_REC[i]] == 1
EXCL = [(dt.date(2020,1,1), dt.date(2021,12,31)), (dt.date(2023,1,1), dt.date(2025,6,30))]
def is_baseline(d):
    if in_recession(d): return False
    return not any(a <= d <= b for a, b in EXCL)

MU, SD = {}, {}
for name, ser in T.items():
    base = [ser[k] for k in ser if is_baseline(k)]
    mu = sum(base)/len(base)
    sd = (sum((x-mu)**2 for x in base)/len(base))**0.5 or 1.0
    MU[name], SD[name] = mu, sd

CHANNELS = {
 "labor":        (0.30, ["ICSA","IURSA","SAHM","UNRATEv"]),
 "realactivity": (0.25, ["INDPRO","CMRMT","TCU","PHILLY"]),
 "creditequity": (0.20, ["NASDAQ","BAAAAA","BAA10Y","VIX"]),
 "finconditions":(0.10, ["NFCI"]),
 "housingincome":(0.15, ["PERMIT","HOUST","UMCSENT","W875"]),
}
MEMBERS = [m for _, (_, ms) in CHANNELS.items() for m in ms]
# marginal headline weight per member (all channels present)
WM = {}
for ch, (w, ms) in CHANNELS.items():
    for m in ms: WM[m] = w/len(ms)

# ----------------------------------------------------------------------------
# 4. daily grid
# ----------------------------------------------------------------------------
BASE = dt.date(1970,1,1)
def dn(d): return (d - BASE).days
GRID_START = dt.date(2000,1,1)
END = max(max(S[k]) for k in ("ICSA","NASDAQCOM","VIXCLS","NFCI","BAA10Y"))
NG = (END - GRID_START).days + 1
GDAYS = [GRID_START + dt.timedelta(days=i) for i in range(NG)]
GDN = np.array([dn(d) for d in GDAYS])          # grid daynums

def carry_grid(events):
    """events: list of (avail_daynum, value); value at grid day g = latest event <= g."""
    if not events:
        return np.full(NG, np.nan)
    ev = sorted(events)
    ed = np.array([e[0] for e in ev]); ev_v = np.array([e[1] for e in ev], dtype=float)
    idx = np.searchsorted(ed, GDN, side="right") - 1
    out = np.where(idx >= 0, ev_v[np.clip(idx, 0, len(ev_v)-1)], np.nan)
    return out

def carry_grid_src(real_events, bridge_events):
    """Carry the union of real prints and bridge events with EXACTLY the original
    carry_grid(real+bridge) latest-wins rule (sort by (daynum,value); last <= g wins),
    and additionally report, per grid day, whether the controlling event is a bridge
    (src==1) or a real print (src==0). Reproducing the original tiebreak matters: on
    days where a real and a bridge event share an availability daynum the original picks
    the larger value, so a naive 'which stream is fresher' split is NOT behaviour-
    preserving. Returns (values, bridge_ctrl_mask, valid_mask)."""
    ev = sorted([(a, v, 0) for a, v in real_events] +
                [(a, v, 1) for a, v in bridge_events])
    if not ev:
        z = np.full(NG, np.nan); f = np.zeros(NG, bool)
        return z, f, f
    ed = np.array([e[0] for e in ev]); vv = np.array([e[1] for e in ev], dtype=float)
    src = np.array([e[2] for e in ev])
    idx = np.searchsorted(ed, GDN, side="right") - 1
    valid = idx >= 0
    ci = np.clip(idx, 0, len(vv)-1)
    out = np.where(valid, vv[ci], np.nan)
    bridge_ctrl = valid & (src[ci] == 1)
    return out, bridge_ctrl, valid

def z_events(member, transform, lag):
    """(obs_date+lag, z) events from a transform dict, frozen baseline."""
    mu, sd = MU[member], SD[member]
    return [(dn(k)+lag, (v-mu)/sd) for k, v in transform.items()]

# publication lag per member (days after obs date). obs date = period start.
LAG = {
 "ICSA":6, "IURSA":6, "SAHM":38, "UNRATEv":38,
 "INDPRO":45, "CMRMT":75, "TCU":45, "PHILLY":16,
 "NASDAQ":1, "BAAAAA":33, "BAA10Y":1, "VIX":1,
 "NFCI":6, "PERMIT":48, "HOUST":48, "UMCSENT":50, "W875":55,
}

# ---- FINAL member z on grid (carry by obs date, no lag) -> reading_final ----
FINAL_Z = {m: carry_grid([(dn(k), (v-MU[m])/SD[m]) for k, v in T[m].items()]) for m in MEMBERS}
# ---- ASOF (D0) member z on grid (carry by pub date, final value) -----------
ASOF_Z  = {m: carry_grid(z_events(m, T[m], LAG[m])) for m in MEMBERS}

# ----------------------------------------------------------------------------
# 5. revision injection + D3 bias, from the ALFRED vintage archive
#    (real-time first-print vs final, transform space, z units)
# ----------------------------------------------------------------------------
def parse_vintage(path):
    out = {}
    for r in csv.reader(open(path)):
        if r and r[0][:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            try:
                out[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
            except ValueError:
                # A vintage export may carry a malformed non-observation row.
                # Its date/value pair is unusable, so skip that row explicitly.
                continue
    return out

# transform closures on a vintage dict, returning the value at its tail obs
def vintage_tail_transform(member, vdict):
    if not vdict: return None, None
    if member == "INDPRO":  tf = neg(yoy(vdict))
    elif member == "CMRMT": tf = neg(yoy(vdict))
    elif member == "W875":  tf = neg(yoy(vdict))
    elif member == "NFCI":  tf = dict(vdict)
    else: return None, None
    if not tf: return None, None
    k = max(tf); return k, tf[k]

VIN_SID = {"INDPRO":"INDPRO", "CMRMT":"CMRMTSPL", "W875":"W875RX1", "NFCI":"NFCI"}
D3_MEMBERS = ["INDPRO", "CMRMT", "W875", "NFCI"]

def build_revision(member):
    """Return (rev_events, firstprint) where
       rev_events = [(vintage_daynum, (rt_z - final_z) at that vintage's tail obs)]
       firstprint = {obs_date: first_print_z}  (earliest vintage containing obs)."""
    sid = VIN_SID[member]
    files = sorted(glob.glob(os.path.join(VIN, sid + "_*.csv")))
    rev_events = []; firstprint = {}
    finalT = T[member]; fk = sorted(finalT); mu, sd = MU[member], SD[member]
    def final_z_at(k):
        i = bisect.bisect_right(fk, k) - 1
        return (finalT[fk[i]]-mu)/sd if i >= 0 else None
    for p in files:
        vd = dt.date.fromisoformat(os.path.basename(p).split("_")[1][:10])
        vdict = parse_vintage(p)
        k, rt = vintage_tail_transform(member, vdict)
        if k is None: continue
        rt_z = (rt - mu)/sd
        fz = final_z_at(k)
        if fz is not None:
            rev_events.append((dn(vd), rt_z - fz))
        # first-print of every obs newly present (transform computed in THIS vintage)
        if member == "NFCI":
            tf = dict(vdict)
        else:
            tf = neg(yoy(vdict))
        for ok, ov in tf.items():
            if ok not in firstprint:
                firstprint[ok] = (ov - mu)/sd
    return rev_events, firstprint

REV = {m: build_revision(m) for m in D3_MEMBERS}

# real revision path on the grid (rt - final) z, carried by vintage date
REV_PATH = {m: carry_grid(REV[m][0]) for m in D3_MEMBERS}
for m in D3_MEMBERS:
    REV_PATH[m] = np.nan_to_num(REV_PATH[m], nan=0.0)

# maturity-lagged expanding-mean bias b_hat(t) = mean over obs 24-120mo old of
# (final_z - firstprint_z), clipped +/-0.5. Knowable at t (uses matured obs only).
def build_bhat(member):
    _, fp = REV[member]
    finalT = T[member]; fk = sorted(finalT); mu, sd = MU[member], SD[member]
    def final_z_at(k):
        i = bisect.bisect_right(fk, k) - 1
        return (finalT[fk[i]]-mu)/sd if i >= 0 else None
    # per obs realized revision (final - firstprint)
    obs = sorted(fp)
    rev = [(k, final_z_at(k) - fp[k]) for k in obs if final_z_at(k) is not None]
    rd = np.array([dn(k) for k, _ in rev]); rv = np.array([r for _, r in rev])
    LO, HI = 730, 3650
    out = np.zeros(NG)
    for i, g in enumerate(GDN):
        m = (g - rd >= LO) & (g - rd <= HI)
        out[i] = np.clip(rv[m].mean(), -0.5, 0.5) if m.any() else 0.0
    return out

BHAT = {m: build_bhat(m) for m in D3_MEMBERS}

# ----------------------------------------------------------------------------
# 6. bridge fills (fit on months <= 2011-12, applied 2012+; final-vintage LHS)
# ----------------------------------------------------------------------------
FIT_END = dt.date(2011,12,31)
def months(a=dt.date(1990,1,1), b=END):
    d = dt.date(a.year, a.month, 1); out = []
    while d <= b:
        out.append(d)
        d = dt.date(d.year+ (d.month==12), (d.month % 12)+1, 1)
    return out
MO = months()

def mval(series, d):
    """monthly value at month-start d (exact key or nearest prior within 20d)."""
    if d in series: return series[d]
    ks = sorted(series); i = bisect.bisect_right(ks, d)-1
    if i >= 0 and (d-ks[i]).days <= 20: return series[ks[i]]
    return None

def myoy(series, d, lag=12):
    prev = dt.date(d.year-1, d.month, 1) if lag==12 else None
    a = mval(series, d); b = mval(series, prev)
    if a is None or b is None or b == 0: return None
    return (a/b-1)*100

def ols(Xrows, yrows, lam=1.0):
    """Ridge (L2 on non-intercept cols) in standardized space -> stable coefs under
    the multicollinearity the raw bridge regressors carry (e.g. RRSFS vs INDPRO)."""
    X = np.array(Xrows, float); y = np.array(yrows, float)
    if len(X) < 5:
        b, *_ = np.linalg.lstsq(X, y, rcond=None); return b
    mu = X.mean(0); sd = X.std(0); sd[sd == 0] = 1.0
    Xs = (X - mu)/sd; Xs[:, 0] = 1.0                      # keep intercept column
    A = Xs.T @ Xs + lam*np.diag([0.0]+[1.0]*(X.shape[1]-1))
    bs = np.linalg.solve(A, Xs.T @ y)
    # de-standardize back to raw-feature coefficients
    b = np.zeros(X.shape[1]); b[0] = bs[0]
    for j in range(1, X.shape[1]):
        b[j] = bs[j]/sd[j]; b[0] -= bs[j]*mu[j]/sd[j]
    return b

Z_CLIP = 8.0   # member-z sanity clip on any bridge fill
def zclip(z): return max(-Z_CLIP, min(Z_CLIP, z))

def month_pub(d, lag):  # daynum a monthly nowcast for month d becomes usable
    return dn(d) + lag

# --- CMRMT delta-form bridge: dyoy(CMRMT) ~ a + b*dyoy(RRSFS) + c*dyoy(INDPRO) ---
def fit_cmrmt():
    X, Y = [], []
    for d in MO:
        if d > FIT_END: break
        pm = dt.date(d.year-(d.month==1), (d.month-2)%12+1, 1)
        yc, ycp = myoy(S["CMRMTSPL"], d), myoy(S["CMRMTSPL"], pm)   # yoy from LEVELS
        yr, yrp = myoy(S["RRSFS"], d), myoy(S["RRSFS"], pm)
        yi, yip = myoy(S["INDPRO"], d), myoy(S["INDPRO"], pm)
        if None in (yc,ycp,yr,yrp,yi,yip): continue
        X.append([1.0, yr-yrp, yi-yip]); Y.append(yc-ycp)      # delta-yoy bridge
    return ols(X, Y)

# native (unsigned) yoy dicts for bridge maths
T_native = {"CMRMT": yoy(S["CMRMTSPL"]), "INDPRO": yoy(S["INDPRO"]),
            "TCU": yoy(S["TCU"]), "HOUST": yoy(S["HOUST"]),
            "PERMIT": yoy(S["PERMIT"]), "W875": yoy(S["W875RX1"])}

B_CMRMT = fit_cmrmt()

def bridge_cmrmt_events():
    """For each month, chain published CMRMT (>=3mo old) forward via bridged deltas
    using RRSFS/INDPRO (published ~t+46). Emits member-z events (available date)."""
    ev = []
    for d in MO:
        if d < dt.date(2001,1,1): continue
        # latest published CMRMT month at the RRSFS/INDPRO availability edge:
        # CMRMT ~t+75 (3 mo stale); RRSFS/INDPRO ~t+46 (1 mo stale)
        base = dt.date(d.year-(d.month<=3), (d.month-4)%12+1, 1)  # ~3mo prior known
        ycb = myoy(S["CMRMTSPL"], base)
        if ycb is None: continue
        yc = ycb; cur = base
        ok = True
        for _ in range(3):  # chain up to 3 months toward d
            nxt = dt.date(cur.year+(cur.month==12), cur.month%12+1, 1)
            if nxt > d: break
            pm = cur
            yr, yrp = myoy(S["RRSFS"], nxt), myoy(S["RRSFS"], pm)
            yi, yip = myoy(S["INDPRO"], nxt), myoy(S["INDPRO"], pm)
            if None in (yr,yrp,yi,yip):
                dyc = 0.0  # last unbridged month: hold
            else:
                dyc = B_CMRMT[0] + B_CMRMT[1]*(yr-yrp) + B_CMRMT[2]*(yi-yip)
            yc += dyc; cur = nxt
        # member value = -yoy, z; available when INDPRO/RRSFS for month d-1 are out
        z = (-yc - MU["CMRMT"])/SD["CMRMT"]
        ev.append((month_pub(d, 47), zclip(z)))
    return ev

# --- INDPRO early-month 2-gap: yoy_m ~ a + b*yoy_{m-2} + c*PHIL_m + d*PHIL_{m-1} ---
def fit_indpro():
    X, Y = [], []
    for d in MO:
        if d > FIT_END: break
        m2 = dt.date(d.year-(d.month<=2), (d.month-3)%12+1, 1)
        ph = mval(S["GACDFSA066MSFRBPHI"], d)
        ph1 = mval(S["GACDFSA066MSFRBPHI"], dt.date(d.year-(d.month==1),(d.month-2)%12+1,1))
        y, y2 = myoy(S["INDPRO"], d), myoy(S["INDPRO"], m2)
        if None in (ph,ph1,y,y2): continue
        X.append([1.0, y2, ph, ph1]); Y.append(y)
    return ols(X, Y)
B_INDPRO = fit_indpro()

def bridge_indpro_tcu_events():
    """Early-month 2-gap INDPRO fill from Philly; apply same delta to TCU (corr .996)."""
    ev_i, ev_t = [], []
    for d in MO:
        if d < dt.date(2001,1,1): continue
        m2 = dt.date(d.year-(d.month<=2), (d.month-3)%12+1, 1)
        ph = mval(S["GACDFSA066MSFRBPHI"], d)
        ph1 = mval(S["GACDFSA066MSFRBPHI"], dt.date(d.year-(d.month==1),(d.month-2)%12+1,1))
        y2 = myoy(S["INDPRO"], m2)
        if None in (ph,ph1,y2): continue
        yhat = B_INDPRO[0]+B_INDPRO[1]*y2+B_INDPRO[2]*ph+B_INDPRO[3]*ph1
        z = (-yhat - MU["INDPRO"])/SD["INDPRO"]
        ev_i.append((month_pub(d, 16), zclip(z)))       # Philly for month d is in-month (~16)
        # TCU: carried TCU yoy (m-2) + (INDPRO yoy_hat - INDPRO yoy_{m-2}) delta
        tcu2 = myoy(S["TCU"], m2); ind2 = myoy(S["INDPRO"], m2)
        if None not in (tcu2, ind2):
            tcu_hat = tcu2 + (yhat - ind2)
            ev_t.append((month_pub(d, 16), zclip((-tcu_hat - MU["TCU"])/SD["TCU"])))
    return ev_i, ev_t

# --- PHILLY AR shrink days 1-15: PHIL_m ~ a + b*PHIL_{m-1} + c*PHIL_{m-2} ---
def fit_philly():
    X, Y = [], []
    for d in MO:
        if d > FIT_END: break
        p1 = mval(S["GACDFSA066MSFRBPHI"], dt.date(d.year-(d.month==1),(d.month-2)%12+1,1))
        p2 = mval(S["GACDFSA066MSFRBPHI"], dt.date(d.year-(d.month<=2),(d.month-3)%12+1,1))
        p0 = mval(S["GACDFSA066MSFRBPHI"], d)
        if None in (p0,p1,p2): continue
        X.append([1.0,p1,p2]); Y.append(p0)
    return ols(X, Y)
B_PHILLY = fit_philly()

def bridge_philly_events():
    """Fill Philly on days 1-15 (before the 3rd-Thursday print) via AR shrink."""
    ev = []
    for d in MO:
        if d < dt.date(2001,1,1): continue
        p1 = mval(S["GACDFSA066MSFRBPHI"], dt.date(d.year-(d.month==1),(d.month-2)%12+1,1))
        p2 = mval(S["GACDFSA066MSFRBPHI"], dt.date(d.year-(d.month<=2),(d.month-3)%12+1,1))
        if None in (p1,p2): continue
        phat = B_PHILLY[0]+B_PHILLY[1]*p1+B_PHILLY[2]*p2
        # available day 1 of month d (prior-month Philly already out), until real print ~16
        ev.append((dn(d)+1, zclip((-phat - MU["PHILLY"])/SD["PHILLY"])))
    return ev

# --- HOUST: yoy_m ~ a + b*PERMITyoy_{m-1} + c*mortD12_m + d*nasdaq_dd_m ---
def mort_d12(d):
    a = mval(S["MORTGAGE30US"], d)  # weekly; nearest prior within 20d ok
    b = mval(S["MORTGAGE30US"], dt.date(d.year-1, d.month, 1))
    return (a-b) if (a is not None and b is not None) else None
def nas_dd_m(d):
    dd = drawdown(S["NASDAQCOM"])
    v = mval(dd, d)
    return v
_NASDD = drawdown(S["NASDAQCOM"])
def nas_dd_month(d):
    ks = sorted(_NASDD); target = dt.date(d.year, d.month, 15)
    i = bisect.bisect_right(ks, target)-1
    return _NASDD[ks[i]] if i >= 0 else None
def fit_houst():
    X, Y = [], []
    for d in MO:
        if d > FIT_END: break
        pm = dt.date(d.year-(d.month==1),(d.month-2)%12+1,1)
        pp = myoy(S["PERMIT"], pm); md = mort_d12(d); nd = nas_dd_month(d)
        y = myoy(S["HOUST"], d)
        if None in (pp,md,nd,y): continue
        X.append([1.0,pp,md,nd]); Y.append(y)
    return ols(X, Y)
B_HOUST = fit_houst()
def bridge_houst_events():
    ev = []
    for d in MO:
        if d < dt.date(2001,1,1): continue
        pm = dt.date(d.year-(d.month==1),(d.month-2)%12+1,1)
        pp = myoy(S["PERMIT"], pm); md = mort_d12(d); nd = nas_dd_month(d)
        if None in (pp,md,nd): continue
        yhat = B_HOUST[0]+B_HOUST[1]*pp+B_HOUST[2]*md+B_HOUST[3]*nd
        ev.append((month_pub(d, 17), zclip((-yhat - MU["HOUST"])/SD["HOUST"])))
    return ev

# --- W875: yoy_m ~ a + b*PAYyoy_m + c*dPAYyoy_m + carry(m-1) ---
def fit_w875():
    X, Y = [], []
    for d in MO:
        if d > FIT_END: break
        pm = dt.date(d.year-(d.month==1),(d.month-2)%12+1,1)
        py, pyp = myoy(S["PAYEMS"], d), myoy(S["PAYEMS"], pm)
        c = myoy(S["W875RX1"], pm); y = myoy(S["W875RX1"], d)
        if None in (py,pyp,c,y): continue
        X.append([1.0,py,py-pyp,c]); Y.append(y)
    return ols(X, Y)
B_W875 = fit_w875()
def bridge_w875_events():
    ev = []
    for d in MO:
        if d < dt.date(2001,1,1): continue
        pm = dt.date(d.year-(d.month==1),(d.month-2)%12+1,1)
        py, pyp = myoy(S["PAYEMS"], d), myoy(S["PAYEMS"], pm)
        c = myoy(S["W875RX1"], pm)
        if None in (py,pyp,c): continue
        yhat = B_W875[0]+B_W875[1]*py+B_W875[2]*(py-pyp)+B_W875[3]*c
        # PAYEMS for month d out ~m_end+8 (=day~38); W875 real print ~day 55
        ev.append((month_pub(d, 38), zclip((-yhat - MU["W875"])/SD["W875"])))
    return ev

# --- UNRATE model C -> ΔU -> SAHM + UNRATEv fills ---
def mmean(series, d):  # month-mean of a weekly series over month d
    ks = [k for k in series if k.year==d.year and k.month==d.month]
    return (sum(series[k] for k in ks)/len(ks)) if ks else None
def fit_unrate():
    X, Y = [], []
    for d in MO:
        if d > FIT_END: break
        pm = dt.date(d.year-(d.month==1),(d.month-2)%12+1,1)
        cc, ccp = mmean(S["CCSA"], d), mmean(S["CCSA"], pm)
        ic, icp = mmean(S["ICSA"], d), mmean(S["ICSA"], pm)
        iu, iup = mmean(S["IURSA"], d), mmean(S["IURSA"], pm)
        u, up = mval(S["UNRATE"], d), mval(S["UNRATE"], pm)
        upp = mval(S["UNRATE"], dt.date(pm.year-(pm.month==1),(pm.month-2)%12+1,1))
        if None in (cc,ccp,ic,icp,iu,iup,u,up,upp) or ccp<=0 or icp<=0: continue
        import math
        X.append([1.0, math.log(cc/ccp), math.log(ic/icp), iu-iup, up-upp])
        Y.append(u-up)
    return ols(X, Y)
B_UNRATE = fit_unrate()
def bridge_unrate_events():
    """Predict current-month ΔU from claims (avail ~day25 of ref month), extend the
    UNRATE path, recompute SAHM and UNRATEv; emit member-z events for both."""
    import math
    ev_s, ev_u = [], []
    ukeys = sorted(S["UNRATE"])
    for d in MO:
        if d < dt.date(2001,1,1): continue
        pm = dt.date(d.year-(d.month==1),(d.month-2)%12+1,1)
        cc, ccp = mmean(S["CCSA"], d), mmean(S["CCSA"], pm)
        ic, icp = mmean(S["ICSA"], d), mmean(S["ICSA"], pm)
        iu, iup = mmean(S["IURSA"], d), mmean(S["IURSA"], pm)
        up = mval(S["UNRATE"], pm)
        upp = mval(S["UNRATE"], dt.date(pm.year-(pm.month==1),(pm.month-2)%12+1,1))
        if None in (cc,ccp,ic,icp,iu,iup,up,upp) or ccp<=0 or icp<=0: continue
        dU = (B_UNRATE[0]+B_UNRATE[1]*math.log(cc/ccp)+B_UNRATE[2]*math.log(ic/icp)
              +B_UNRATE[3]*(iu-iup)+B_UNRATE[4]*(up-upp))
        u_hat = up + dU
        # build predicted UNRATE path (history up to pm, then u_hat for d)
        path = {k: S["UNRATE"][k] for k in ukeys if k <= pm}
        path[d] = u_hat
        sh = sahm_from_unrate(path); rv = rise_floor(path, 120)
        avail = dn(d) + 25       # claims give the read ~day 25 of the ref month
        if d in sh: ev_s.append((avail, zclip((sh[d]-MU["SAHM"])/SD["SAHM"])))
        if d in rv: ev_u.append((avail, zclip((rv[d]-MU["UNRATEv"])/SD["UNRATEv"])))
    return ev_s, ev_u

# --- D1 mechanical BAAAAA month-to-date daily mean of DBAA-DAAA ---
def bridge_baaaaa_events():
    """MTD mean of daily DBAA-DAAA; emit an event each day (>=5 obs) of the month."""
    daily = {k: S["DBAA"][k]-S["DAAA"][k] for k in S["DBAA"] if k in S["DAAA"]}
    ks = sorted(daily)
    ev = []
    # group by month, cumulative mean, available next business day (+1)
    from collections import defaultdict
    bym = defaultdict(list)
    for k in ks: bym[(k.year,k.month)].append(k)
    for (y,m), days in bym.items():
        run = []
        for k in days:
            run.append(daily[k])
            if len(run) >= 5:
                mtd = sum(run)/len(run)
                ev.append((dn(k)+1, zclip((mtd-MU["BAAAAA"])/SD["BAAAAA"])))
    return ev

# ----------------------------------------------------------------------------
# 7. assemble candidate member-z grids and readings
# ----------------------------------------------------------------------------
def apply_events(base_z, events):
    """override base carried grid with fresher bridge events where available."""
    add = carry_grid(events)
    # combine: at each grid day use whichever source has the later availability.
    # base_z already carried from asof (real prints). Bridge events carry their own.
    # Use bridge value only where a bridge event exists at/before g AND the bridge is
    # fresher than the last real print. We approximate 'fresher' by: bridge overrides
    # whenever it has a value (bridges are constructed to lead the real print and are
    # superseded by the next month's real print through the max-availability rule).
    out = base_z.copy()
    mask = ~np.isnan(add)
    out[mask] = add[mask]
    return out

# precompute bridge event lists
BR = {}
BR["CMRMT"] = bridge_cmrmt_events()
ind_ev, tcu_ev = bridge_indpro_tcu_events()
BR["INDPRO"] = ind_ev; BR["TCU"] = tcu_ev
BR["PHILLY"] = bridge_philly_events()
BR["HOUST"] = bridge_houst_events()
BR["W875"] = bridge_w875_events()
s_ev, u_ev = bridge_unrate_events()
BR["SAHM"] = s_ev; BR["UNRATEv"] = u_ev
BR["BAAAAA"] = bridge_baaaaa_events()

def merge_real_and_bridge(member, bridge_events):
    """Interleave real asof prints and bridge events by availability; latest wins.

    LOOKAHEAD FIX: z_events uses T[member], the FINAL (fully revised) vintage. For the
    revising D3 members (INDPRO/CMRMT/W875) that final value is NOT publishable at t on
    carry-forward days. The D0 baseline (inject_revision) carries first-print-realistic
    values by adding REV_PATH (rt - final). Here we add REV_PATH to the carried real base
    for D3 members BEFORE overlaying bridges, so a carry day equals D0 exactly and only a
    genuinely bridge-fresh day differs from D0. Without this, carry days silently read the
    final value and most of the apparent bridge gain is revision removal, not timeliness."""
    real = z_events(member, T[member], LAG[member])
    out, bridge_ctrl, valid = carry_grid_src(real, list(bridge_events))
    if member in D3_MEMBERS:
        # real-controlled (carry-forward) days: convert the FINAL-vintage carried print
        # to first-print realism by adding REV_PATH, so these days equal D0 exactly and
        # only genuinely bridge-controlled days differ from D0. Bridge-controlled days
        # keep the out-of-sample nowcast value untouched.
        real_ctrl = valid & ~bridge_ctrl
        out[real_ctrl] = out[real_ctrl] + REV_PATH[member][real_ctrl]
    return out

# reading pipeline ------------------------------------------------------------
EXP_MU_FINAL = None; EXP_SD_FINAL = None
def headline_grid(memberZ):
    tot = np.zeros(NG); wsum = np.zeros(NG)
    for ch,(w,ms) in CHANNELS.items():
        cs = np.zeros(NG); cnt = np.zeros(NG)
        for m in ms:
            z = memberZ[m]; ok = ~np.isnan(z)
            cs[ok] += z[ok]; cnt[ok] += 1
        good = cnt > 0
        tot[good] += w*(cs[good]/cnt[good]); wsum[good] += w
    out = np.full(NG, np.nan); good = wsum > 0
    out[good] = tot[good]/wsum[good]
    return out

def trailing_mean(x, w=21):
    out = np.full(NG, np.nan)
    for i in range(NG):
        lo = max(0, i-w+1); seg = x[lo:i+1]; seg = seg[~np.isnan(seg)]
        if len(seg): out[i] = seg.mean()
    return out

def compress(v, C=4.0):
    v = np.asarray(v, float); out = v.copy()
    hi = v > C; out[hi] = C + (v[hi]-C)**0.25
    return out

def reading_from(memberZ, exp_mu, exp_sd):
    h = headline_grid(memberZ)
    sig = (h - exp_mu)/exp_sd
    sm = trailing_mean(sig, 21)
    return compress(sm), sig

# ----------------------------------------------------------------------------
# 8. build readings for final + each candidate
# ----------------------------------------------------------------------------
# exp_mu / exp_sd from the FINAL reconstructed line on baseline days (frozen)
h_final = headline_grid(FINAL_Z)
base_mask = np.array([is_baseline(d) for d in GDAYS]) & ~np.isnan(h_final)
EXP_MU_FINAL = h_final[base_mask].mean()
EXP_SD_FINAL = h_final[base_mask].std()
reading_final, sig_final = reading_from(FINAL_Z, EXP_MU_FINAL, EXP_SD_FINAL)

def d0_memberZ():
    return {m: ASOF_Z[m].copy() for m in MEMBERS}

def inject_revision(mz):
    """make the as-of world real-time for the 4 revising members (add rt-final)."""
    for m in D3_MEMBERS:
        mz[m] = mz[m] + REV_PATH[m]
    return mz

# (0) D0 carry-forward (incumbent): real prints, real revision present
mz0 = inject_revision(d0_memberZ())

# (a) BRIDGES: replace stale monthly members with bridge fills
def bridges_memberZ():
    mz = inject_revision(d0_memberZ())
    for m in ["CMRMT","INDPRO","TCU","PHILLY","HOUST","W875","SAHM","UNRATEv","BAAAAA"]:
        # merge_real_and_bridge now re-adds REV_PATH to the real base for D3 members, so
        # carry days retain first-print realism (== D0) and only bridge-fresh days differ.
        mz[m] = merge_real_and_bridge(m, BR[m])
    return mz
mzB = bridges_memberZ()

# (b) REVISION (D3): D0 + b_hat on the 4 members
def revision_memberZ():
    mz = inject_revision(d0_memberZ())
    for m in D3_MEMBERS:
        mz[m] = mz[m] + BHAT[m]
    return mz
mzR = revision_memberZ()

# (D4) STACK: bridges + D3, no double count (D3 only on NFCI always; INDPRO/CMRMT/W875
# only where bridge is inactive i.e. the member still on its real carried print)
def stack_memberZ():
    mz = inject_revision(d0_memberZ())
    bridged = {"CMRMT","INDPRO","TCU","PHILLY","HOUST","W875","SAHM","UNRATEv","BAAAAA"}
    for m in ["CMRMT","INDPRO","TCU","PHILLY","HOUST","W875","SAHM","UNRATEv","BAAAAA"]:
        mz[m] = merge_real_and_bridge(m, BR[m])
    # NFCI always corrected
    mz["NFCI"] = mz["NFCI"] + BHAT["NFCI"]
    # INDPRO/CMRMT/W875: add b_hat only where bridge event is NOT overriding. After the
    # merge fix the carry-day base is the FIRST-PRINT value (real + REV_PATH), so adding
    # BHAT (= final - firstprint estimate) is the correct SINGLE revision correction there,
    # not a double-count on an already-final value.
    for m in ["INDPRO","CMRMT","W875"]:
        _, bridge_ctrl, _ = carry_grid_src(z_events(m, T[m], LAG[m]), list(BR[m]))
        add = BHAT[m].copy(); add[bridge_ctrl] = 0.0   # BHAT only on real-controlled carry days
        mz[m] = mz[m] + add
    return mz
mzS = stack_memberZ()

CANDS = {
    "carry_forward_D0": mz0,
    "bridges_a":        mzB,
    "revision_b_D3":    mzR,
    "stack_D4":         mzS,
}
READINGS = {}
for name, mz in CANDS.items():
    READINGS[name], _ = reading_from(mz, EXP_MU_FINAL, EXP_SD_FINAL)

# ----------------------------------------------------------------------------
# 9. scoring (2012+, COVID handled per research)
# ----------------------------------------------------------------------------
EVAL_START = dt.date(2012,1,1)
eval_mask = np.array([d >= EVAL_START for d in GDAYS])
covid = np.array([dt.date(2020,3,1) <= d <= dt.date(2021,6,30) for d in GDAYS])
finite = ~np.isnan(reading_final)

def cut_stats(pred, cut):
    m = cut & finite & ~np.isnan(pred)
    err = pred[m] - reading_final[m]
    if m.sum() == 0: return None
    return {"n": int(m.sum()),
            "mae": float(np.abs(err).mean()),
            "rmse": float(np.sqrt((err**2).mean()))}

def sign_agree(pred, cut):
    m = cut & finite & ~np.isnan(pred)
    sp = np.sign(pred[m]); sf = np.sign(reading_final[m])
    return float((sp == sf).mean())

# crossing dates: first day of >=5 consecutive days with reading >= theta
def crossings(reading, theta):
    ok = reading >= theta
    out = []
    i = 0
    while i < NG:
        if ok[i] and eval_mask[i]:
            j = i
            while j < NG and ok[j]: j += 1
            if j - i >= 5:
                out.append(GDN[i])
                i = j; continue
        i += 1
    return out

def crossing_metrics(pred):
    res = {}
    for theta in (0.5, 1.0):
        fc = crossings(reading_final, theta)
        pc = crossings(pred, theta)
        # match each final crossing to nearest pred crossing within +/-45d
        day_errs = []; matched_p = set(); missed = 0
        for f in fc:
            cand = [(abs(p-f), p) for p in pc if abs(p-f) <= 45]
            if cand:
                cand.sort(); day_errs.append(int(cand[0][1]-f)); matched_p.add(cand[0][1])
            else:
                missed += 1
        false = sum(1 for p in pc if p not in matched_p and not any(abs(p-f)<=45 for f in fc))
        res[f"{theta:.1f}sigma"] = {
            "n_final_cross": len(fc), "n_pred_cross": len(pc),
            "median_abs_day_err": (float(np.median(np.abs(day_errs))) if day_errs else None),
            "signed_day_errs": day_errs, "false": int(false), "missed": int(missed)}
    return res

RESULTS = {"meta": {
    "grid": [GRID_START.isoformat(), END.isoformat()],
    "eval_start": EVAL_START.isoformat(),
    "exp_mu_final": float(EXP_MU_FINAL), "exp_sd_final": float(EXP_SD_FINAL),
    "n_eval_days": int((eval_mask & finite).sum()),
    "ground_truth": "series.json nat.sm reconstructed (sigma units)",
    "candidates": list(CANDS.keys())},
    "candidates": {}}

for name, pred in READINGS.items():
    RESULTS["candidates"][name] = {
        "full_2012plus":  cut_stats(pred, eval_mask & ~covid),
        "incl_covid":     cut_stats(pred, eval_mask),
        "covid_only":     cut_stats(pred, eval_mask & covid),
        "sign_agree_2012plus_exCOVID": sign_agree(pred, eval_mask & ~covid),
        "crossings": crossing_metrics(pred),
    }

# relative-to-D0 summary
d0 = RESULTS["candidates"]["carry_forward_D0"]
for name in CANDS:
    c = RESULTS["candidates"][name]
    fc = c["full_2012plus"]; f0 = d0["full_2012plus"]
    c["vs_D0"] = {
        "mae_ratio": round(fc["mae"]/f0["mae"], 4) if f0["mae"] else None,
        "rmse_ratio": round(fc["rmse"]/f0["rmse"], 4) if f0["rmse"] else None,
        "mae_delta_index_units": round((fc["mae"]-f0["mae"])*EXP_SD_FINAL, 5),
    }

# ---- per-member attribution (swap one member's fill at a time vs D0) --------
# closes the UNRESOLVED per-member cells of NOWCAST_RESEARCH sec 1; adoption evidence.
def mae_on(pred, cut):
    m = cut & finite & ~np.isnan(pred)
    return float(np.abs(pred[m]-reading_final[m]).mean())
attr = {}
cut_full = eval_mask & ~covid; cut_cov = eval_mask & covid
r_d0 = READINGS["carry_forward_D0"]
mae0_full = mae_on(r_d0, cut_full); mae0_cov = mae_on(r_d0, cut_cov)
BRIDGED_MEMBERS = ["BAAAAA","CMRMT","INDPRO","TCU","PHILLY","HOUST","W875","SAHM","UNRATEv"]
for m in BRIDGED_MEMBERS:
    mz = {k: v.copy() for k, v in mz0.items()}
    mz[m] = merge_real_and_bridge(m, BR[m])
    r, _ = reading_from(mz, EXP_MU_FINAL, EXP_SD_FINAL)
    attr[m] = {"mae_delta_2012plus": round(mae_on(r, cut_full)-mae0_full, 5),
               "mae_delta_covid":    round(mae_on(r, cut_cov)-mae0_cov, 5),
               "n_bridge_events": len(BR[m])}
for m in D3_MEMBERS:  # revision-layer single-member attribution
    mz = {k: v.copy() for k, v in mz0.items()}
    mz[m] = mz[m] + BHAT[m]
    r, _ = reading_from(mz, EXP_MU_FINAL, EXP_SD_FINAL)
    attr.setdefault(m, {})
    attr[m]["rev_mae_delta_2012plus"] = round(mae_on(r, cut_full)-mae0_full, 5)
    attr[m]["rev_mae_delta_covid"]    = round(mae_on(r, cut_cov)-mae0_cov, 5)
RESULTS["per_member_attribution"] = attr

# ---- GFC stress leg: refit all bridges on <=2007-06, evaluate 2007-07..2011-12 ----
# (NOWCAST_RESEARCH sec 3.5.2; 2012+ contains no classic recession before COVID, so the
#  turning-point value of the fills can only be scored out-of-sample on the GFC.)
def run_gfc_leg():
    global FIT_END, B_CMRMT, B_INDPRO, B_PHILLY, B_HOUST, B_W875, B_UNRATE, BR
    save = (FIT_END, B_CMRMT, B_INDPRO, B_PHILLY, B_HOUST, B_W875, B_UNRATE, BR)
    FIT_END = dt.date(2007,6,30)
    B_CMRMT = fit_cmrmt(); B_INDPRO = fit_indpro(); B_PHILLY = fit_philly()
    B_HOUST = fit_houst(); B_W875 = fit_w875(); B_UNRATE = fit_unrate()
    BR = {}
    BR["CMRMT"] = bridge_cmrmt_events()
    ie, te = bridge_indpro_tcu_events(); BR["INDPRO"], BR["TCU"] = ie, te
    BR["PHILLY"] = bridge_philly_events(); BR["HOUST"] = bridge_houst_events()
    BR["W875"] = bridge_w875_events()
    se, ue = bridge_unrate_events(); BR["SAHM"], BR["UNRATEv"] = se, ue
    BR["BAAAAA"] = bridge_baaaaa_events()
    cands = {"carry_forward_D0": inject_revision(d0_memberZ()),
             "bridges_a": bridges_memberZ(),
             "revision_b_D3": revision_memberZ(),
             "stack_D4": stack_memberZ()}
    gmask = np.array([dt.date(2007,7,1) <= d <= dt.date(2011,12,31) for d in GDAYS])
    out = {}
    r0 = None
    for name, mz in cands.items():
        r, _ = reading_from(mz, EXP_MU_FINAL, EXP_SD_FINAL)
        st = cut_stats(r, gmask)
        out[name] = st
        if name == "carry_forward_D0": r0 = st
    for name in out:
        out[name]["mae_ratio_vs_D0"] = round(out[name]["mae"]/r0["mae"], 4)
        out[name]["rmse_ratio_vs_D0"] = round(out[name]["rmse"]/r0["rmse"], 4)
    (FIT_END, B_CMRMT, B_INDPRO, B_PHILLY, B_HOUST, B_W875, B_UNRATE, BR) = save
    return out
RESULTS["stress_leg_GFC_2007H2_2011"] = run_gfc_leg()

# ---- validation vs the live nat line ----
def validate_final():
    ser = json.load(open(os.path.join(R,"geo","series.json")))
    nat = ser["nat"]; d = nat["d"]; raw = nat["raw"]; sm = nat["sm"]
    natraw = {d[i]: raw[i]/100.0 for i in range(len(d))}
    natsm = {d[i]: sm[i]/100.0 for i in range(len(d))}
    er_raw, er_sm = [], []
    for i, g in enumerate(GDN):
        if int(g) in natraw and not np.isnan(sig_final[i]):
            er_raw.append(abs(sig_final[i]-natraw[int(g)]))
        if int(g) in natsm and not np.isnan(reading_final[i]):
            er_sm.append(abs(reading_final[i]-natsm[int(g)]))
    return {"raw_line_MAE_vs_nat": float(np.mean(er_raw)),
            "raw_line_max_abs": float(np.max(er_raw)),
            "smoothed_reading_MAE_vs_natsm": float(np.mean(er_sm)),
            "n_compared": len(er_raw)}
RESULTS["validation"] = validate_final()

os.makedirs(SCRATCH, exist_ok=True)
json.dump(RESULTS, open(os.path.join(SCRATCH, "nowcast_results.json"), "w"), indent=2)
print("VALIDATION", RESULTS["validation"])
for name in CANDS:
    c = RESULTS["candidates"][name]
    print(name, "MAE", round(c["full_2012plus"]["mae"],4),
          "RMSE", round(c["full_2012plus"]["rmse"],4),
          "vsD0", c["vs_D0"]["mae_ratio"], c["vs_D0"]["rmse_ratio"],
          "sign", round(c["sign_agree_2012plus_exCOVID"],3))
print("wrote", os.path.join(SCRATCH, "nowcast_results.json"))
