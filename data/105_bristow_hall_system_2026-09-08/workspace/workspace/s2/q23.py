# q23.py - is anything faster than 19 March 2020 possible? The market crash (the sudden stop's 20 per cent under the
# 20-day high, at the prior close) as a PROPOSER on its own, with the rule's spread object (13-week mean of the paper
# spread above its 39-week low, line 0.9, as published by the H.15 release day), and with the claims week at lower
# jumps than 35 per cent on the same release day. Frozen 1962-2026: every day the condition holds, grouped by episode
# (a new episode after 26 weeks quiet); episodes outside a recession window (six months before the peak month to the
# trough month) are false alarms. Run: PYTHONPATH=. python3 s2/q23.py
import sys,os,io,contextlib
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk46.py').read().split(_MARK)[0])
PKm=[pd.Timestamp(x) for x in PK]; TRm=[pd.Timestamp(x) for x in TR]
def in_rec(t): return any(PKm[i]-pd.DateOffset(months=6)<=pd.Timestamp(t.year,t.month,1)<=TRm[i] for i in range(len(PKm)))
def episodes(days,gap=182):
    eps=[]; last=None
    for d in sorted(days):
        if last is None or (d-last).days>gap: eps.append(d)
        last=d
    return eps
def report(name,days):
    eps=episodes(days); fa=[d for d in eps if not in_rec(d)]
    print(f"{name}: {len(eps)} episodes; first days {[d.date().isoformat() for d in eps]}; FALSE {len(fa)}: {[d.date().isoformat() for d in fa]}")
# 1. the crash alone, daily (prior close >= 20 under the 20-day high), from 1962
cr=_crash[(_crash.index>='1962-01-01')]; d20=list(cr[cr>=20-EPS].index); report('crash >=20 alone',d20)
# 2. the crash with the spread object at its line, as published (latest H.15 release day <= the day)
spub=pd.Series({rel_h15(t):v for t,v in GSP.items()}).sort_index(); spub=spub[~spub.index.duplicated(keep='last')]
def spread_asof(day):
    s=spub[spub.index<=day]; return float(s.iloc[-1]) if len(s) else np.nan
d2=[d for d in d20 if spread_asof(d)>=0.9-EPS]; report('crash >=20 AND spread object >=0.9 (published)',d2)
for line in (0.6,0.45,0.3):
    d3=[d for d in d20 if spread_asof(d)>=line-EPS]; report(f'crash >=20 AND spread object >={line}',d3)
# 3. the crash with the claims week at lower jumps (same release day), the sudden stop at 35/20 for reference
for pct in (35,25,20,15,10):
    c=leg_K_x(ICfp.dropna(),pct,20); report(f'claims week >= {pct} per cent over base with crash >= 20 (K at {pct}/20)',[d for d,m in c])
# 4. what stood on the days 9-19 March 2020: crash at prior close, the spread object as published, the claims week
print('--- March 2020, day by day (crash at prior close | spread object as published | claims week released that day)')
for d in pd.date_range('2020-03-02','2020-03-27',freq='B'):
    ic=ICfp.dropna(); wk=[t for t in ic.index if rel_ic(t)==d]
    print(d.date(), round(crash_on(d),1), round(spread_asof(d),3), [(t.date().isoformat(),int(ic[t])) for t in wk])
# 5. 1987 for the record
print('--- October-November 1987: crash at prior close and the spread object as published')
for d in pd.date_range('1987-10-19','1987-12-04',freq='W-THU'): print(d.date(), round(crash_on(d),1), round(spread_asof(d),3))
