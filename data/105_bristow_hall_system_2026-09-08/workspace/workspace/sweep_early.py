"""THE FOUR CALLS THAT ARE TOO EARLY ALL COME FROM TWO LEGS, AND NO OTHER CALL DOES.

Anthony wants every call as close to a week early as possible.  Five of the nine already clear that
bar; the argument about the other four - 1990 at -5, 2001 at -2, 2020 at +12, 2024 at +3 - has been
about finding faster data, and collections 113 and 114 have now shown there is none in FRED.

But the record has a second half nobody has worked on.  Four calls are not late, they are far too
early: 1969 at -86, 1973 at -74, 1979 at -63 and 1981 at -155 days.  Against a target of -7 those
four are between two and five months of error, which is more total error than the late side carries.

The structure of the rule makes them separable.  Reading the walk-end diary by branch:

    1969  L      1990  W      2020  K
    1973  V      2001  U      2024  X
    1979  L      2007  B
    1981  L

The four early calls are the ONLY calls that come from legs L and V.  L is the unemployment-gap leg
read at the low line (0.2) over a 52-week window; V is the state-vacancy leg at its second line
(0.6).  Every other call comes from a different leg.  So raising those two lines can move the four
early calls later - toward -7 - and cannot touch the other five.

It also cannot manufacture a false alarm: raising a line only ever makes a leg fire later or not at
all.  The only risk is a miss, and that is exactly what this sweep measures.

Run from the workspace directory:  python3 sweep_early.py
"""
import os, sys, io, contextlib, itertools, json
os.environ['BHS_SEARCH_TERMS'] = 'unemp,layoffs,laidoff'
sys.argv = ['walk55.py', '1962', '2026', 'sweep']
_MARK = "# ---- the walk " + "itself"
_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "sweep_%s.out")
with contextlib.redirect_stdout(io.StringIO()):
    exec(_hdr)
import pandas as pd, numpy as np

BASE = dict(bshare=0.6, cD=6, cn=3, cs=15, deep=999, half=4, hback=9, hline=1.0, hrs=2.0,
            ic=40, kc=(35, 20), look=52, low=0.2, minw=18, nd=1.2, qst=13, rst=8,
            sahm=0.3667, spr=0.9, starts=29, tst=6, u45=0.45, vb=4, vk=4, vl=0.2,
            wline=0.3, wline2=0.6)
NINE = ['1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']
END = lambda s: pd.Timestamp(s + '-01') + pd.offsets.MonthEnd(0)
TARGET = -7

def read(turns):
    """turns -> list of (kind, date, branch); pull the peaks out however they are shaped."""
    out = []
    for t in turns:
        if isinstance(t, dict):
            k = t.get('kind') or t.get('type'); d = t.get('fired') or t.get('date'); b = t.get('branch') or t.get('leg')
        else:
            k, d, b = (list(t) + [None, None, None])[:3]
        out.append((str(k), pd.Timestamp(d) if d is not None else None, b))
    return out

def score(turns):
    rows = read(turns)
    peaks = [r for r in rows if str(r[0]).lower().startswith(('p', 'open'))]
    dates = sorted(d for _, d, _ in peaks if d is not None)
    matched, used, false = {}, set(), []
    for d in dates:
        best = None
        for m in NINE:
            e = END(m)
            if -400 <= (d - e).days <= 120 and m not in used:
                if best is None or abs((d - e).days) < abs((d - END(best)).days): best = m
        if best: matched[best] = d; used.add(best)
        else: false.append(str(d.date()))
    days = {m: (matched[m] - END(m)).days for m in matched}
    err = sum(abs(v - TARGET) for v in days.values()) + 400 * (9 - len(days))
    return len(days), len(false), days, err, false

b0 = build_v(dict(BASE))
n0, f0, d0, e0, fa0 = score(b0[1])
print('BASE  detected', n0, 'false', f0, 'total |days +7|', e0)
print('      ', {k: d0.get(k) for k in NINE})
print()

res = []
LOWS  = [0.20, 0.25, 0.30, 0.325, 0.35, 0.375, 0.40, 0.425, 0.45, 0.50]
WL2   = [0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5]
for lo, w2 in itertools.product(LOWS, WL2):
    p = dict(BASE); p['low'] = lo; p['wline2'] = w2
    try:
        s, turns = build_v(p)
    except Exception as ex:
        print('fail', lo, w2, str(ex)[:60]); continue
    n, f, d, e, fa = score(turns)
    res.append(dict(low=lo, wline2=w2, detected=n, false=f, err=e, **{m: d.get(m) for m in NINE}))
    print(f'low={lo:<6} wline2={w2:<4} detected={n} false={f} err={e:<6} ' +
          ' '.join(f'{m[:4]}:{d.get(m)}' for m in NINE), flush=True)

df = pd.DataFrame(res)
df.to_csv('sweep_early.csv', index=False)
ok = df[(df['detected'] == 9) & (df['false'] == 0)].sort_values('err')
print('\nnine of nine, no false alarm, ranked by total distance from a week early:')
print(ok.head(15).to_string(index=False))
