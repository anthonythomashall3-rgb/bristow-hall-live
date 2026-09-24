"""HOW CLOSE TO A WEEK EARLY CAN THE RULE BE MADE, WITHOUT NEW DATA?

Anthony's target is minus seven days on every call. The programme has spent its effort on the late
side - 2020 at +12 and 2024 at +3 - and collections 113 and 114 have now established that FRED holds
nothing that fixes either. The early side has never been worked on at all, and it carries more total
error: at the frozen walk-end lines the calls run

    1948  -51 U     1969 -156 L     1990  -76 W     2020  +12 K
    1953  +62 U     1973  -74 L     2001  -16 I     2024   +3 X
    1957   +5 X     1980  -87 L     2007   -7 B
    1960  +91 U     1981 -155 L

Four of the thirteen come from leg L, the unemployment-gap leg read at its low line, and no other
call does. Raising a line can only make a leg fire later or not at all, so it cannot manufacture a
false alarm; the only risk is a miss, and that is what this measures.

Scored with the rule's own score13, so the numbers are comparable with the record. The objective is
the total distance from minus seven days across all thirteen episodes, admitted only when all
thirteen are still called and the false-alarm list is still empty.

Nothing here changes the tool. It is a measurement of what is available, and any change would need
a pre-registered amendment and a fresh walk.
"""
import os, sys, io, contextlib, itertools, json
os.environ['BHS_SEARCH_TERMS'] = 'unemp,layoffs,laidoff'
sys.argv = ['walk55.py', '1962', '2026', 'sweep']
_M = '# ---- the walk ' + 'itself'
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('walk54.py').read().split(_M)[0].replace('walk54_%s.out', 'sweep2_%s.out'))
import pandas as pd, numpy as np

BASE = dict(bshare=0.6, cD=6, cn=3, cs=15, deep=999, half=4, hback=9, hline=1.0, hrs=2.0,
            ic=40, kc=(35, 20), look=52, low=0.2, minw=18, nd=1.2, qst=13, rst=8,
            sahm=0.3667, spr=0.9, starts=29, tst=6, u45=0.45, vb=4, vk=4, vl=0.2,
            wline=0.3, wline2=0.6)
TARGET = -7
NAMES = ['1948','1953','1957','1960','1969','1973','1980','1981','1990','2001','2007','2020','2024']
MODERN = list(range(4, 13))

def summarise(s):
    lags = s['lags_p']; called = set(s['called']); other = s['other']
    legs = {i: s['opens'][i]['leg'] for i in s['opens']}
    all13 = sum(abs(lags[i]-TARGET) for i in lags) + 500*(13-len(called))
    mod9 = sum(abs(lags[i]-TARGET) for i in lags if i in MODERN) + 500*(9-len([i for i in called if i in MODERN]))
    worst = max((abs(lags[i]-TARGET) for i in lags), default=999)
    return dict(called=len(called), false=len(other), err13=all13, err9=mod9, worst=worst,
                lags={NAMES[i]: lags[i] for i in sorted(lags)},
                legs={NAMES[i]: legs.get(i) for i in sorted(lags)})

s0, _ = build_v(dict(BASE))
b = summarise(s0)
print('BASE  called', b['called'], 'false', b['false'], 'err13', b['err13'], 'err9', b['err9'])
print('     ', b['lags']); print('     ', b['legs']); print(flush=True)

LOW   = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
WLINE = [0.3, 0.4, 0.5, 0.6, 0.8, 1.0]
WL2   = [0.6, 0.9, 1.2]
rows = []
for lo, wl, w2 in itertools.product(LOW, WLINE, WL2):
    if w2 <= wl: continue
    p = dict(BASE); p['low'] = lo; p['wline'] = wl; p['wline2'] = w2
    try:
        s, _ = build_v(p)
    except Exception as ex:
        print('fail', lo, wl, w2, str(ex)[:50], flush=True); continue
    r = summarise(s); r.update(low=lo, wline=wl, wline2=w2)
    rows.append(r)
    print(f"low={lo:<5} wline={wl:<4} wline2={w2:<4} called={r['called']} false={r['false']} "
          f"err13={r['err13']:<5} err9={r['err9']:<5} worst={r['worst']:<4} "
          + ' '.join(f"{k}:{v}{r['legs'][k]}" for k, v in r['lags'].items()), flush=True)

df = pd.DataFrame([{k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in r.items()} for r in rows])
df.to_csv('sweep_early2.csv', index=False)
ok = df[(df['called'] == 13) & (df['false'] == 0)].sort_values('err13')
print(f'\nall thirteen called, no false alarm: {len(ok)} of {len(df)}')
print(ok.head(12).to_string(index=False))
