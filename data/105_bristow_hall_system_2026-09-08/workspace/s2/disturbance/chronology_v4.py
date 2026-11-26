"""Chronology version 4 of the Bristow-Hall System (collection 1174, RECORD-1174/1176/1178; rulings of 25 Nov 2026). No AI.
The growth cycle chronology on the Conference Board's Coincident Economic Index: payrolls, real personal income less transfer payments,
industrial production and real manufacturing and trade sales, with the Conference Board's standardization factors (effective Feb 2019).
Trend: centred 75-month moving average (extended at the ends with the slope of its first or last 36 computed months). Turning points: the
full Bry-Boschan routine. A contraction counts when its deviation falls FLOOR points or more and ends below trend; one that fails is removed
with its trough and the lower of its two peaks. Published dates (Zarnowitz and Ozyildirim 2002, Conference Board) stand through 2000; NBER
dates mark recessions. Tier 1: the live reading (not a call). Tier 2: an episode is confirmed once its trough is WAIT months old."""
import numpy as np, pandas as pd
TCB = dict(PAYEMS=0.5290, W875RX1=0.2054, INDPRO=0.1454, CMRMTSPL=0.1202)
FLOOR = 0.95; WAIT = 18
ZO = [('1948-01','1949-10'),('1951-01','1952-07'),('1953-03','1954-08'),('1957-02','1958-04'),('1960-01','1961-02'),
      ('1962-04','1964-01'),('1966-03','1967-10'),('1969-08','1970-11'),('1973-11','1975-04'),('1979-03','1980-07'),
      ('1981-07','1982-12'),('1984-09','1987-01'),('1989-01','1991-12'),('1995-01','1996-01')]
ZO_PEAK_2000 = '2000-06'
OECD = [('2000-04','2003-02'),('2007-10','2009-05'),('2012-03','2014-02'),('2015-02','2017-03'),('2019-12','2020-05')]
M = lambda s: pd.Timestamp(s + '-01')
def mdiff(a, b): return (a.year - b.year) * 12 + a.month - b.month
def ov(a, b, c, d): return not ((b if b is not None else M('2100-01')) < c or a > (d if d is not None else M('2100-01')))

def index(ser, start='1947-01-01'):
    chg = {n: (lambda x: (200 * (x - x.shift(1)) / (x + x.shift(1))).dropna())(ser[n][ser[n].index >= pd.Timestamp(start)]) for n in TCB}
    df = pd.DataFrame(chg); last = min(chg['PAYEMS'].index[-1], chg['INDPRO'].index[-1]); df = df[df.index <= last]
    av = df.notna(); wm = pd.DataFrame({n: av[n] * TCB[n] for n in TCB}); wm = wm.div(wm.sum(axis=1), axis=0)
    c = (df.fillna(0) * wm).sum(axis=1); lv = [100.0]
    for x in c.values: lv.append(lv[-1] * (200 + x) / (200 - x))
    return pd.Series(lv[1:], index=c.index), av

# ---------- smoothing tools ----------
SPW = np.array([-3,-6,-5,3,21,46,67,74,67,46,21,3,-5,-6,-3]) / 320.0
def pad(v, k):
    return np.r_[np.full(k, v[:k].mean()), v, np.full(k, v[-k:].mean())]
def spencer(v):
    p = pad(v, 7); return np.convolve(p, SPW[::-1], mode='valid')
def cma(v, k):
    """centred moving average of span k (2xk for even k)"""
    if k % 2 == 1:
        h = k // 2; p = pad(v, h); return np.convolve(p, np.ones(k) / k, mode='valid')
    w = np.r_[0.5, np.ones(k - 1), 0.5] / k; h = k // 2; p = pad(v, h); return np.convolve(p, w, mode='valid')
def mcd_span(v):
    c = spencer(v); i = v - c
    for k in range(1, 7):
        I = np.mean(np.abs(i[k:] - i[:-k])); C = np.mean(np.abs(c[k:] - c[:-k]))
        if C > 0 and I / C < 1: return k
    return 6

# ---------- Bry-Boschan ----------
def local_turns(v, win):
    t = []
    for i in range(len(v)):
        a, b = max(0, i - win), min(len(v), i + win + 1); seg = v[a:b]
        if v[i] == seg.max() and (seg == v[i]).sum() == 1: t.append((i, 'P'))
        elif v[i] == seg.min() and (seg == v[i]).sum() == 1: t.append((i, 'T'))
    return t
def alternate(t, v):
    out = []
    for i, k in sorted(t):
        if out and out[-1][1] == k:
            j = out[-1][0]
            if (k == 'P' and v[i] > v[j]) or (k == 'T' and v[i] < v[j]): out[-1] = (i, k)
        else: out.append((i, k))
    return out
def min_cycle(t, v, mc):
    t = list(t); changed = True
    while changed:
        changed = False
        for a in range(len(t) - 2):
            if t[a + 2][0] - t[a][0] < mc:
                i, k = t[a]; j, _ = t[a + 2]
                drop = a if ((k == 'P' and v[i] < v[j]) or (k == 'T' and v[i] > v[j])) else a + 2
                del t[drop]; t = alternate(t, v); changed = True; break
    return t
def refine(t, v, win):
    out = []
    for i, k in t:
        a, b = max(0, i - win), min(len(v), i + win + 1); seg = v[a:b]
        j = a + (int(np.argmax(seg)) if k == 'P' else int(np.argmin(seg))); out.append((j, k))
    return alternate(out, v)
def bry_boschan(x, mp=5, mc=15, ends=6):
    v = np.asarray(x, float); n = len(v)
    sp = spencer(v); d = v - sp; sd = d.std(); v1 = np.where(np.abs(d) > 3.5 * sd, sp, v)
    m12 = cma(v1, 12)
    t = alternate(local_turns(m12, 5), m12)
    s1 = spencer(v1); t = refine(t, s1, 5); t = min_cycle(t, s1, mc)
    k = max(3, min(6, mcd_span(v1))); mm = cma(v1, k); t = refine(t, mm, 5)
    t = refine(t, v, max(4, k))
    t = [(i, kk) for i, kk in t if ends <= i <= n - 1 - ends]
    # end turns must be the extremes relative to values closer to the end
    while t:
        i, kk = t[0]; seg = v[:i]
        if (kk == 'P' and len(seg) and seg.max() > v[i]) or (kk == 'T' and len(seg) and seg.min() < v[i]): t = t[1:]
        else: break
    while t:
        i, kk = t[-1]; seg = v[i + 1:]
        if (kk == 'P' and len(seg) and seg.max() > v[i]) or (kk == 'T' and len(seg) and seg.min() < v[i]): t = t[:-1]
        else: break
    changed = True
    while changed:
        changed = False
        t2 = min_cycle(t, v, mc)
        if t2 != t: t = t2; changed = True; continue
        for a in range(len(t) - 1):
            if t[a + 1][0] - t[a][0] < mp: del t[a:a + 2]; t = alternate(t, v); changed = True; break
    return t
def simple_bb(x, win=5, mp=5, mc=15):
    v = np.asarray(x, float); t = alternate(local_turns(v, win), v)
    t = [(i, k) for i, k in t if win <= i <= len(v) - 1 - win]
    changed = True
    while changed:
        changed = False
        for a in range(len(t) - 1):
            if t[a + 1][0] - t[a][0] < mp: del t[a:a + 2]; t = alternate(t, v); changed = True; break
        if changed: continue
        t2 = min_cycle(t, v, mc)
        if t2 != t: t = t2; changed = True
    return t

def ma75(y):
    v = y.values; n = len(v); h = 37; m = np.full(n, np.nan)
    for i in range(h, n - h): m[i] = v[i - h:i + h + 1].mean()
    a, b = h, n - h - 1; s0 = (m[a + 35] - m[a]) / 35; s1 = (m[b] - m[b - 35]) / 35
    for i in range(0, a): m[i] = m[a] - s0 * (a - i)
    for i in range(b + 1, n): m[i] = m[b] + s1 * (i - b)
    return pd.Series(m, index=y.index)

def contractions(dev, floor=FLOOR):
    v = dev.values; t = bry_boschan(v); changed = True
    while changed:
        changed = False
        for a in range(len(t) - 1):
            (i, k), (j, kk) = t[a], t[a + 1]
            if k == 'P' and kk == 'T' and not (v[j] < 0 and v[i] - v[j] >= floor):
                nx = a + 2 if a + 2 < len(t) and t[a + 2][1] == 'P' else None
                if nx is None: break
                drop = [a, a + 1] if v[i] < v[t[nx][0]] else [a + 1, nx]
                t = [x for q, x in enumerate(t) if q not in drop]; changed = True; break
    out = []; p = None
    for i, k in t:
        if k == 'P': p = i
        elif p is not None: out.append((dev.index[p], dev.index[i])); p = None
    return out

def build(ser, nber):
    """Returns the deviation, the adopted episodes (peak, trough or None, source, method dates) and the tier 1 live reading."""
    lvl, av = index(ser); y = np.log(lvl); dev = 100 * (y - ma75(y)); closed = contractions(dev)
    eps = []
    for a, b in ZO + [(ZO_PEAK_2000, None)]:
        pa, pb = M(a), (M(b) if b else None)
        m = min([x for x in closed if ov(x[0], x[1], pa, pb if pb is not None else M('2000-12'))], key=lambda q: abs(mdiff(q[0], pa)))
        eps.append(dict(peak=pa, trough=pb if pb is not None else m[1], source='Zarnowitz-Ozyildirim 2002' if b else 'Zarnowitz 2003/2007 peak; method trough',
                        method_peak=m[0], method_trough=m[1]))
    for p, t in closed:
        if p > M('2001-01'): eps.append(dict(peak=p, trough=t, source='chronology v4 method', method_peak=p, method_trough=t))
    # open episode: judged like a closed one, on its lowest month so far (the provisional trough), not on the latest month
    last_tr = max(t for _, t in closed); after = dev[dev.index > last_tr]; pk = after.idxmax(); post = dev[dev.index > pk]
    now = float(dev.iloc[-1]); low = post.idxmin() if len(post) else pk
    fall = float(dev[pk] - dev[low]); meets = len(post) >= 6 and fall >= FLOOR and float(dev[low]) < 0
    if meets: eps.append(dict(peak=pk, trough=None, source='chronology v4 method', method_peak=pk, method_trough=None, low=low))
    elif len(post) >= 6 and fall > 0:
        # a slowdown under way that is not (yet) a disturbance: listed as unsettled, never counted as a disturbance or a recession
        eps.append(dict(peak=pk, trough=None, source='chronology v4 method', method_peak=pk, method_trough=None, low=low, unsettled=True))
    last = dev.index[-1]
    for e in eps:
        e['nber'] = [(x, z) for x, z in nber if ov(e['peak'], e['trough'], M(x), M(z))]
        e['oecd'] = [(x, z) for x, z in OECD if ov(e['peak'], e['trough'], M(x), M(z))]
        mp, mt = e['method_peak'], e['method_trough']
        e['fall_pp'] = round(float(dev[mp] - (dev[mt] if mt is not None else dev[e['low']])), 2)
        e['confirmed'] = e['trough'] is not None and mdiff(last, e['trough']) >= WAIT
    live = dict(data_through=last.strftime('%Y-%m'), components_in_latest_month=[n for n in TCB if bool(av.iloc[-1][n])],
                gap_from_trend=round(now, 2), below_trend=bool(now < 0), high_since_last_trough=pk.strftime('%Y-%m'),
                high_gap=round(float(dev[pk]), 2), lowest_since_high=low.strftime('%Y-%m'), lowest_gap=round(float(dev[low]), 2),
                fall_to_lowest=round(fall, 2), meets_disturbance_rule_on_todays_data=bool(meets),
                typical_error_latest_month_pp=2.3, note='a reading of current conditions, not a call')
    return lvl, dev, eps, live
