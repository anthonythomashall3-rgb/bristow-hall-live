#!/usr/bin/env python3
"""Live-edge nowcast for the Bristow-Hall Recession Monitor national headline.

Replaces the incumbent carry-forward ("D0") at the LIVE EDGE ONLY (the unpublished
months of the stale monthly members) with the validated STACK: per-input bridge
fills + the revision-bias correction, composed under the no-double-count rule.

The stack was validated out-of-sample (2012+, leakage-audited) by nowcast_harness.py
and research/artifacts/nowcast_results.json: MAE 12% below carry-forward and the 0.5-sigma
crossing-date error halved (24d -> 12d). This module is the PRODUCTION port of exactly
those maps.

Design contract (why this is safe to run live):
  * The pre-2012-fit OLS coefficients are FROZEN here as constants (B_* below). We do
    NOT refit anything at run time. They are the identical vectors nowcast_harness.py
    produces from its fit_*() calls on data <= 2011-12-31.
  * The revision-bias b_hat(END) values are frozen per member (BHAT_END). b_hat is a
    maturity-lagged expanding mean over observations 24-120 months old, so it moves
    < 0.01/month; freezing END's value keeps compute light (no 4368-file vintage sweep
    per index build) while staying the validated correction.
  * We ONLY ever emit fills for obs months STRICTLY AFTER a member's last real published
    obs. Published/historical member values are never modified. Therefore every reading
    day at or before the earliest fill month is byte-identical to carry-forward, and only
    the live edge (days > nowcast_from) moves.
  * No-double-count: bridged missing months carry the pure bridge z (no b_hat). NFCI is
    not bridged, so its unpublished tail carries the b_hat revision correction. The three
    revising bridged members (INDPRO/CMRMT/W875) would only take b_hat on real-controlled
    days, i.e. their published prints -- which are off-limits here -- so at the live edge
    their correction is (correctly) zero, matching the stack rule.

Pure stdlib (dict + bisect), matching index_v1.py's idiom. No numpy, no daily grid.
"""
import bisect, datetime as dt, math
from collections import deque

# ----------------------------------------------------------------------------
# Frozen coefficients (fit on months <= 2011-12-31 in nowcast_harness.py; do NOT
# refit live). Verified equal to nowcast_harness.py's B_* at import time by
# nowcast_live_selftest / the edge guard.
# ----------------------------------------------------------------------------
B_CMRMT  = [-0.0034948744515988827, 0.350095248297356, 0.49499790152265055]
B_INDPRO = [0.004540761190320514, 0.8546111070512722, 0.02845436899068882,
            0.02392065088911368]
B_PHILLY = [0.9832537235195528, 0.7060480437999607, 0.13336432624686664]
B_HOUST  = [-0.00021856098674677416, 0.9000445212298558, -0.8939301894356768,
            0.04881388416443764]
B_W875   = [0.19854537220468482, 0.2005677967713719, 1.100121719780693,
            0.8393274724449518]
B_UNRATE = [0.009113673238788547, 1.0073873897560488, 0.048573182160026845,
            0.6598294245135599, -0.048517310284542814]

# Frozen revision-bias b_hat(END) per revising member (final_z - firstprint_z,
# expanding mean over obs 24-120mo old, clipped +/-0.5). Only NFCI's is applied at
# the live edge (see no-double-count note above); the others are frozen for
# provenance and for nowcast_stack callers that operate on published prints.
BHAT_END = {"INDPRO": 0.1114766974391851, "CMRMT": 0.18909924928027008,
            "W875": -0.46145233826884474, "NFCI": 0.21402777212460586}

Z_CLIP = 8.0
def zclip(z): return max(-Z_CLIP, min(Z_CLIP, z))

# ----------------------------------------------------------------------------
# transform helpers (verbatim logic from index_v1.py / nowcast_harness.py)
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

def sahm_from_unrate(un):
    ks = sorted(un); avg = {}
    for i, k in enumerate(ks):
        w = [un[ks[j]] for j in range(max(0, i-2), i+1)]
        avg[k] = sum(w)/len(w)
    return rise_floor(avg, 370)

# ---- monthly point-in-time helpers ----
def mval(series, d):
    if d in series: return series[d]
    ks = sorted(series); i = bisect.bisect_right(ks, d)-1
    if i >= 0 and (d-ks[i]).days <= 20: return series[ks[i]]
    return None

def myoy(series, d):
    prev = dt.date(d.year-1, d.month, 1)
    a = mval(series, d); b = mval(series, prev)
    if a is None or b is None or b == 0: return None
    return (a/b-1)*100

def mmean(series, d):
    ks = [k for k in series if k.year == d.year and k.month == d.month]
    return (sum(series[k] for k in ks)/len(ks)) if ks else None

def _prevm(d):
    return dt.date(d.year-(d.month == 1), (d.month-2) % 12+1, 1)

def _monthstart(d):
    return dt.date(d.year, d.month, 1)

def _next_month(d):
    return dt.date(d.year+(d.month == 12), d.month % 12+1, 1)

# ----------------------------------------------------------------------------
# per-member bridge estimators (frozen-coefficient ports; return member-z or None)
# ----------------------------------------------------------------------------
def cmrmt_z(S, MU, SD, d):
    """Chain published CMRMT (~3mo stale) forward via bridged RRSFS/INDPRO deltas."""
    base = dt.date(d.year-(d.month <= 3), (d.month-4) % 12+1, 1)
    ycb = myoy(S["CMRMTSPL"], base)
    if ycb is None: return None
    yc = ycb; cur = base
    for _ in range(3):
        nxt = _next_month(cur)
        if nxt > d: break
        pm = cur
        yr, yrp = myoy(S["RRSFS"], nxt), myoy(S["RRSFS"], pm)
        yi, yip = myoy(S["INDPRO"], nxt), myoy(S["INDPRO"], pm)
        if None in (yr, yrp, yi, yip):
            dyc = 0.0
        else:
            dyc = B_CMRMT[0] + B_CMRMT[1]*(yr-yrp) + B_CMRMT[2]*(yi-yip)
        yc += dyc; cur = nxt
    return zclip((-yc - MU["CMRMT"])/SD["CMRMT"])

def indpro_tcu_z(S, MU, SD, d):
    """Early-month 2-gap INDPRO fill from Philly; same delta rides TCU (corr .996)."""
    m2 = dt.date(d.year-(d.month <= 2), (d.month-3) % 12+1, 1)
    ph = mval(S["GACDFSA066MSFRBPHI"], d)
    ph1 = mval(S["GACDFSA066MSFRBPHI"], _prevm(d))
    y2 = myoy(S["INDPRO"], m2)
    if None in (ph, ph1, y2): return None, None
    yhat = B_INDPRO[0]+B_INDPRO[1]*y2+B_INDPRO[2]*ph+B_INDPRO[3]*ph1
    zi = zclip((-yhat - MU["INDPRO"])/SD["INDPRO"])
    zt = None
    tcu2 = myoy(S["TCU"], m2); ind2 = myoy(S["INDPRO"], m2)
    if None not in (tcu2, ind2):
        tcu_hat = tcu2 + (yhat - ind2)
        zt = zclip((-tcu_hat - MU["TCU"])/SD["TCU"])
    return zi, zt

_NASDD_CACHE = {}
def _nas_dd_month(S, d):
    key = id(S["NASDAQCOM"])
    dd = _NASDD_CACHE.get(key)
    if dd is None:
        dd = drawdown(S["NASDAQCOM"]); _NASDD_CACHE[key] = dd
    ks = sorted(dd); target = dt.date(d.year, d.month, 15)
    i = bisect.bisect_right(ks, target)-1
    return dd[ks[i]] if i >= 0 else None

def _mort_d12(S, d):
    a = mval(S["MORTGAGE30US"], d)
    b = mval(S["MORTGAGE30US"], dt.date(d.year-1, d.month, 1))
    return (a-b) if (a is not None and b is not None) else None

def houst_z(S, MU, SD, d):
    pm = _prevm(d)
    pp = myoy(S["PERMIT"], pm); md = _mort_d12(S, d); nd = _nas_dd_month(S, d)
    if None in (pp, md, nd): return None
    yhat = B_HOUST[0]+B_HOUST[1]*pp+B_HOUST[2]*md+B_HOUST[3]*nd
    return zclip((-yhat - MU["HOUST"])/SD["HOUST"])

def w875_z(S, MU, SD, d):
    pm = _prevm(d)
    py, pyp = myoy(S["PAYEMS"], d), myoy(S["PAYEMS"], pm)
    c = myoy(S["W875RX1"], pm)
    if None in (py, pyp, c): return None
    yhat = B_W875[0]+B_W875[1]*py+B_W875[2]*(py-pyp)+B_W875[3]*c
    return zclip((-yhat - MU["W875"])/SD["W875"])

def unrate_z(S, MU, SD, d):
    """Predict current-month dU from claims; extend UNRATE path; recompute SAHM/UNRATEv."""
    pm = _prevm(d)
    cc, ccp = mmean(S["CCSA"], d), mmean(S["CCSA"], pm)
    ic, icp = mmean(S["ICSA"], d), mmean(S["ICSA"], pm)
    iu, iup = mmean(S["IURSA"], d), mmean(S["IURSA"], pm)
    up = mval(S["UNRATE"], pm)
    upp = mval(S["UNRATE"], _prevm(pm))
    if None in (cc, ccp, ic, icp, iu, iup, up, upp) or ccp <= 0 or icp <= 0:
        return None, None
    dU = (B_UNRATE[0]+B_UNRATE[1]*math.log(cc/ccp)+B_UNRATE[2]*math.log(ic/icp)
          + B_UNRATE[3]*(iu-iup)+B_UNRATE[4]*(up-upp))
    u_hat = up + dU
    ukeys = sorted(S["UNRATE"])
    path = {k: S["UNRATE"][k] for k in ukeys if k <= pm}
    path[d] = u_hat
    sh = sahm_from_unrate(path); rv = rise_floor(path, 120)
    z_s = zclip((sh[d]-MU["SAHM"])/SD["SAHM"]) if d in sh else None
    z_u = zclip((rv[d]-MU["UNRATEv"])/SD["UNRATEv"]) if d in rv else None
    return z_s, z_u

def baaaaa_z(S, MU, SD, d):
    """Month-to-date daily mean of DBAA-DAAA for month d (>=5 obs)."""
    daily = {k: S["DBAA"][k]-S["DAAA"][k] for k in S["DBAA"] if k in S["DAAA"]}
    days = [k for k in sorted(daily) if k.year == d.year and k.month == d.month]
    if len(days) < 5: return None
    mtd = sum(daily[k] for k in days)/len(days)
    return zclip((mtd - MU["BAAAAA"])/SD["BAAAAA"])

# ----------------------------------------------------------------------------
# last real (published) obs per member, from raw S using the same transforms
# ----------------------------------------------------------------------------
def _last_real_obs(S):
    def lastkey(dct):
        return max(dct) if dct else None
    return {
        "CMRMT":   lastkey(yoy(S["CMRMTSPL"])),
        "INDPRO":  lastkey(yoy(S["INDPRO"])),
        "TCU":     lastkey(yoy(S["TCU"])),
        "HOUST":   lastkey(yoy(S["HOUST"])),
        "W875":    lastkey(yoy(S["W875RX1"])),
        "SAHM":    lastkey(S["SAHMREALTIME"]),
        "UNRATEv": lastkey(S["UNRATE"]),
        "BAAAAA":  lastkey({d: 1 for d in S["BAA"] if d in S["AAA"]}),
        "NFCI":    lastkey(S["NFCI"]),
    }

def _missing_months(last_obs, end_date):
    """Obs month-starts strictly after last_obs, up to END's month (inclusive)."""
    if last_obs is None:
        return []
    end_m = _monthstart(end_date)
    out = []; d = _next_month(_monthstart(last_obs))
    while d <= end_m:
        out.append(d); d = _next_month(d)
    return out

# ----------------------------------------------------------------------------
# public entry points
# ----------------------------------------------------------------------------
def live_edge_fills(S, MU, SD, end_date):
    """Return (fills, nowcast_from) for the LIVE EDGE ONLY.

    fills: {member: [(obs_date, member_z), ...]} where every obs_date is STRICTLY
           after that member's last real published obs. Injecting these into a
           carry-forward series (keyed by obs date) replaces carry-forward with the
           validated stack on the live edge and leaves all prior days untouched.
    nowcast_from: date, the earliest fill obs_date across all members = the boundary
           past which the reading diverges from pure carry-forward. None if no fills.

    S     : raw series dicts (index_v1's load()ed), incl. bridge inputs RRSFS,
            MORTGAGE30US, PAYEMS, CCSA, DBAA, DAAA.
    MU,SD : per-member baseline mean/sd from index_v1 (same formula as the harness).
    end_date : index_v1's END.
    """
    last = _last_real_obs(S)
    fills = {}

    def add(member, obs_date, z):
        if z is None: return
        fills.setdefault(member, []).append((obs_date, z))

    # bridged monthly members: one fill per genuinely-missing edge month, pure bridge z
    for d in _missing_months(last.get("CMRMT"), end_date):
        add("CMRMT", d, cmrmt_z(S, MU, SD, d))
    for d in _missing_months(last.get("INDPRO"), end_date):
        zi, _ = indpro_tcu_z(S, MU, SD, d); add("INDPRO", d, zi)
    for d in _missing_months(last.get("TCU"), end_date):
        _, zt = indpro_tcu_z(S, MU, SD, d); add("TCU", d, zt)
    for d in _missing_months(last.get("HOUST"), end_date):
        add("HOUST", d, houst_z(S, MU, SD, d))
    for d in _missing_months(last.get("W875"), end_date):
        add("W875", d, w875_z(S, MU, SD, d))
    for d in _missing_months(last.get("SAHM"), end_date):
        zs, _ = unrate_z(S, MU, SD, d); add("SAHM", d, zs)
    for d in _missing_months(last.get("UNRATEv"), end_date):
        _, zu = unrate_z(S, MU, SD, d); add("UNRATEv", d, zu)
    for d in _missing_months(last.get("BAAAAA"), end_date):
        add("BAAAAA", d, baaaaa_z(S, MU, SD, d))

    # NFCI: not bridged; carry its last published z forward corrected by the frozen
    # revision-bias b_hat, applied ONLY to the unpublished tail (days after last obs).
    nfci_last = last.get("NFCI")
    if nfci_last is not None and nfci_last < end_date:
        z_last = (S["NFCI"][nfci_last] - MU["NFCI"])/SD["NFCI"]
        add("NFCI", nfci_last + dt.timedelta(days=1),
            zclip(z_last + BHAT_END["NFCI"]))

    all_obs = [o for evs in fills.values() for o, _ in evs]
    nowcast_from = min(all_obs) if all_obs else None
    return fills, nowcast_from

def nowcast_stack(asof_date, published_series, MU=None, SD=None):
    """Convenience wrapper: {member: latest corrected estimate z} for stale members,
    as of asof_date. published_series/MU/SD as in live_edge_fills. Returns the last
    (freshest) fill value per member -- the current live-edge nowcast the reading uses."""
    if MU is None or SD is None:
        raise ValueError("nowcast_stack requires MU and SD (index_v1 baselines)")
    fills, _ = live_edge_fills(published_series, MU, SD, asof_date)
    return {m: sorted(evs)[-1][1] for m, evs in fills.items()}
