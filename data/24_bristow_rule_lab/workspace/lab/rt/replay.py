"""True first-print replay of the rule's real-time trough call on the United States.

At every vintage day T the panel is rebuilt from the vintages in force on T (ALFRED), the
composite deviation statistic is recomputed from that data alone, and the trough decision of
`real_time_trough_calls` is taken on it.  Nothing published after T is used at T.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/rt')
import bristow_rule_v3 as br, alfred as al

NBER_T = [pd.Timestamp(x) for x in ('1970-11-01','1975-03-01','1980-07-01','1982-11-01',
                                    '1991-03-01','2001-11-01','2009-06-01','2020-04-01')]
NBER_P = [pd.Timestamp(x) for x in ('1969-12-01','1973-11-01','1980-01-01','1981-07-01',
                                    '1990-07-01','2001-03-01','2007-12-01','2020-02-01')]

PANELS = {
 'core3':  [('INDPRO','level'),('PAYEMS','level'),('UNRATE','rate')],
 'core4':  [('INDPRO','level'),('PAYEMS','level'),('UNRATE','rate'),('PCEC96','level')],
 'core6':  [('INDPRO','level'),('PAYEMS','level'),('UNRATE','rate'),('PCEC96','level'),
            ('MANEMP','level'),('AWHMAN','level')],
}

def panel_asof(spec, T):
    out = []
    for sid, kind in spec:
        s = al.asof(sid, T)
        if s is None or len(s) < 40: continue
        out.append((sid, br.procyclical(s.astype(float), kind)))
    return out

def vintage_days(spec, t0, t1):
    days = set()
    for sid, _ in spec:
        for v in al.vintages(sid):
            if t0 <= v <= t1: days.add(v)
    return sorted(days)

def replay(spec, t0='1962-01-01', t1='2026-08-31', threshold=2.0, fall_months=4, drop=0.5,
           min_cycle=15, lookback=12, smooth=3, min_channels=2, warmup=24, verbose=False):
    t0 = pd.Timestamp(t0); t1 = pd.Timestamp(t1)
    calls = []; start = None
    for T in vintage_days(spec, t0, t1):
        ch = panel_asof(spec, T)
        if len(ch) < min_channels: continue
        D = br.composite_deviation(ch, lookback, smooth, min_channels).dropna()
        if len(D) < warmup: continue
        if start is None: start = D.index[0]
        seg = D[start:]
        if len(seg) < 4: continue
        at = seg.idxmax(); hi = float(seg.max())
        if hi < threshold: continue
        after = seg[seg.index > at]
        if len(after) < fall_months: continue
        tail = list(after.iloc[-fall_months:])
        prev = float(after.iloc[-fall_months - 1]) if len(after) > fall_months else hi
        falling = all(tail[k] < (tail[k - 1] if k > 0 else prev) for k in range(fall_months))
        if falling and (hi - float(after.iloc[-1])) >= drop:
            start = D.index[-1] + pd.DateOffset(months=1)
            if calls and min_cycle and br._md(at, calls[-1][1]) < min_cycle: continue
            calls.append((T, at, D.index[-1]))
            if verbose: print(f'  call on {T.date()}: trough {at:%Y-%m}, data through {D.index[-1]:%Y-%m}')
    return calls

def score(calls, label=''):
    rows = []; used = set()
    for tr in NBER_T:
        best = None
        for i, c in enumerate(calls):
            T, at = c[0], c[1]
            if i in used: continue
            e = br._md(at, tr)
            if abs(e) <= 6 and (best is None or abs(e) < abs(best[1])): best = (i, e, T)
        if best is None: rows.append((tr, None, None, None)); continue
        used.add(best[0]); T = best[2]
        rows.append((tr, calls[best[0]][1], best[1], (T - tr).days))
    other = [c for i, c in enumerate(calls) if i not in used]
    hit = sum(r[1] is not None for r in rows); ex = sum(r[2] == 0 for r in rows)
    w1 = sum(r[2] is not None and abs(r[2]) <= 1 for r in rows)
    print(f'{label}: {hit}/8 called, {ex} exact, {w1} within 1, other calls {len(other)}')
    for tr, at, e, lag in rows:
        print(f'  {tr:%Y-%m}  {"-" if at is None else at.strftime("%Y-%m")}  err {e}  lag {lag} days')
    for c in other: print(f'  OTHER call {c[0].date()} trough {c[1]:%Y-%m}')
    return rows, other

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--panel', default='core3')
    ap.add_argument('--smooth', type=int, default=3); ap.add_argument('--fall', type=int, default=4)
    ap.add_argument('--drop', type=float, default=0.5); ap.add_argument('--thr', type=float, default=2.0)
    a = ap.parse_args()
    calls = replay(PANELS[a.panel], smooth=a.smooth, fall_months=a.fall, drop=a.drop, threshold=a.thr, verbose=True)
    score(calls, f'{a.panel} smooth={a.smooth} fall={a.fall} drop={a.drop} thr={a.thr}')
