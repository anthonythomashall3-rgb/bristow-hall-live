# Round 19c: is the failure abroad the THRESHOLDS or the STRUCTURE?
# Per-country max-margin re-fit of the same channels, then leave-one-out.
import os, json, itertools
import pandas as pd, numpy as np
BASE = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
src = open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0]
exec(src)
NBER = [("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),
        ("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),
        ("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),
        ("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),
        ("2024-04","2024-08")]
NBER = [(pd.Timestamp(a+"-01"), pd.Timestamp(b+"-01")) for a,b in NBER]

def stats(iso):
    """raw channel statistics on a monthly grid (no thresholds applied)."""
    ur = first("LRHUTTTT%sM156S"%CC[iso], "LRUNTTTT%sM156S"%CC[iso], "LRHUTTTT%sM156N"%CC[iso])
    if ur is None: return None
    iu = first("LMUNRRTT%sM156S"%CC[iso], "LMUNRRTT%sM156N"%CC[iso])
    st = first("IR3TIB01%sM156N"%CC[iso], "IRSTCI01%sM156N"%CC[iso])
    lt = first("IRLTLT01%sM156N"%CC[iso])
    ip = first("%sPROINDMISMEI"%iso)
    idx = pd.DatetimeIndex(pd.date_range(ur.index[0], ur.index[-1], freq="MS"))
    u = ur.reindex(idx).interpolate(limit_area="inside")
    S = {}
    S["u"] = u.rolling(3).mean() - u.rolling(12).min()             # bigger = worse
    if iu is not None:
        v = iu.reindex(idx).interpolate(limit_area="inside")
        S["iu"] = v.rolling(3).mean() - v.rolling(12).min()
    if st is not None:
        s = st.reindex(idx, method="ffill"); S["r"] = -(s - s.shift(3))   # bigger = bigger fall
    if ip is not None:
        p = ip.reindex(idx, method="ffill"); d = -(p/p.shift(1)-1)*100
        S["ip"] = pd.concat([d, d.shift(1)], axis=1).min(axis=1)     # two consecutive
    gate = pd.Series(True, index=idx)
    if st is not None and lt is not None:
        sp = lt.reindex(idx, method="ffill") - st.reindex(idx, method="ffill")
        gate = (sp < 0).rolling(12, min_periods=1).max().fillna(0).astype(bool)
    return idx, S, gate

def windows(iso, idx):
    lo, hi = idx[0], idx[-1]
    if iso == "USA": eps = [(P,T) for P,T in NBER if P>=lo and T<=hi]
    else:
        eps,_ = technical(iso); eps = [(P,T) for P,T in eps if P>=lo and T<=hi]
    return eps

def maxmargin(iso, gated=True, holdout=None, pre=6, post=3):
    r = stats(iso)
    if r is None: return None
    idx, S, gate = r
    eps = windows(iso, idx)
    if len(eps) < 2: return None
    fit = [e for k,e in enumerate(eps) if k != holdout]
    # quiet = what the machine actually sees: no episode open.  An episode runs
    # from pre months before the peak until the unemployment gap has been back
    # under 0.20 pp for three straight months after the trough (the close rule).
    ug = S["u"]; q3 = (ug < 0.20).rolling(3).min().fillna(0).astype(bool)
    quiet = pd.Series(True, index=idx)
    for P,T in eps:
        later = q3.index[(q3.index > T) & q3.values]
        close = later[0] if len(later) else idx[-1]
        quiet &= ~((idx >= P - pd.DateOffset(months=pre)) & (idx <= close))
    if gated: quiet &= gate
    th, carried = {}, {}
    for k, s in S.items():
        s = s.astype(float)
        qmax = s[quiet.values & s.notna().values].max()
        # smallest onset-window peak among the recessions this channel can carry
        peaks = []
        for P,T in fit:
            m = (idx >= P - pd.DateOffset(months=pre)) & (idx <= T)
            if gated: m &= gate.values
            v = s[m]
            if len(v.dropna()): peaks.append(v.max())
        good = [p for p in peaks if p > qmax]
        if not good or not np.isfinite(qmax): continue
        th[k] = (qmax + min(good)) / 2.0
        carried[k] = len(good)
    return idx, S, gate, eps, th, carried, quiet

def replay(iso, th, gated=True, pre=6, post=3):
    idx, S, gate = stats(iso); eps = windows(iso, idx)
    fires = pd.Series(False, index=idx); who = {}
    for k, t in th.items():
        f = (S[k] >= t)
        if gated and k in ("u","r","iu"): f = f & gate
        f = f.fillna(False)
        for d in idx[f.values]: who.setdefault(d, k)
        fires |= f
    ev = sorted(who.items())
    ug = S["u"]; q3 = (ug < 0.20).rolling(3).min().fillna(0).astype(bool)
    lagm = dict(u=1, iu=1, ip=1, r=0)
    ops, until = [], None
    for d, k in ev:
        cm = (pd.Timestamp(d) + pd.DateOffset(months=lagm[k])).replace(day=1)
        if until is not None and cm <= until: continue
        ops.append((cm, k))
        later = q3.index[(q3.index > cm) & q3.values]
        until = later[0] if len(later) else idx[-1]
    res, used = [], set()
    closes = []
    for (P,T) in eps:
        later = q3.index[(q3.index > T) & q3.values]
        closes.append(later[0] if len(later) else idx[-1])
    for (P,T),cl in zip(eps, closes):
        hit = [o for o in ops if (P - pd.DateOffset(months=pre)) <= o[0] <= T]
        if hit:
            cm,k = hit[0]; used.add(hit[0])
            res.append(((cm.year-P.year)*12 + (cm.month-P.month), k))
        else: res.append((None, None))
    fa = [o for o in ops if o not in used and not any(
          (P-pd.DateOffset(months=pre)) <= o[0] <= cl for (P,T),cl in zip(eps,closes))]
    return res, fa, eps, idx

print("=== per-country max-margin re-fit (in-sample) ===")
print("%-4s %-15s %-7s %-6s %-9s %-4s %s" % ("iso","country","det","<=+3m","lag range","FA","thresholds"))
tot=hit=inw=fas=0; yrs=0.0; LOO=[]
for iso in sorted(CC):
    m = maxmargin(iso)
    if m is None: continue
    idx,S,gate,eps,th,carried,quiet = m
    if not th: continue
    res, fa, eps, idx = replay(iso, th)
    L = [l for l,_ in res if l is not None]
    tot += len(res); hit += len(L); inw += sum(1 for l in L if -3<=l<=3); fas += len(fa)
    yrs += (idx[-1]-idx[0]).days/365.25
    print("%-4s %-15s %2d/%-4d %-6d %-9s %-4d %s" % (
        iso, NAME[iso], len(L), len(res), sum(1 for l in L if -3<=l<=3),
        ("%d..%d"%(min(L),max(L))) if L else "-", len(fa),
        " ".join("%s=%.2f"%(k,v) for k,v in sorted(th.items()))))
print("-"*92)
print("TOTAL detected %d/%d = %.0f%% | within +-3m %d/%d = %.0f%% | FA %d in %.0f country-years (1 per %.1f yr)"
      % (hit,tot,100*hit/max(tot,1), inw,hit,100*inw/max(hit,1), fas,yrs,yrs/max(fas,1)))

print("\n=== leave-one-out: threshold fitted without the held-out recession ===")
oo_hit = oo_tot = oo_in = 0; oo_l = []
for iso in sorted(CC):
    base = maxmargin(iso)
    if base is None: continue
    eps = base[3]
    for k in range(len(eps)):
        m = maxmargin(iso, holdout=k)
        if m is None or not m[4]: continue
        res, fa, eps2, idx = replay(iso, m[4])
        l, ch = res[k]
        oo_tot += 1
        if l is not None:
            oo_hit += 1; oo_l.append(l)
            if -3 <= l <= 3: oo_in += 1
print("held-out recessions %d | detected %d = %.0f%% | within +-3m %d = %.0f%% | lag range %s | median %.1f"
      % (oo_tot, oo_hit, 100*oo_hit/max(oo_tot,1), oo_in, 100*oo_in/max(oo_hit,1),
         ("%d..%d"%(min(oo_l),max(oo_l))) if oo_l else "-", np.median(oo_l) if oo_l else 0))
