# q40.py - IS THE SUDDEN STOP'S NO-FALSE-ALARM PROPERTY VACUOUS? Anthony, 11 September 2026: "why is our no false alarm
# vacuous?! we don't want that". The v3.29 addendum said the no-false-alarm test is "nearly vacuous for the datum"
# because, since 2004, the market gate has held only inside recession windows. This script tests the claim properly, on
# the whole sample and on each leg separately:
#   (a) the market gate alone (20 per cent under the 20-day high) - every episode since 1962 and which lie outside a
#       recession window;
#   (b) the claims week alone (35 per cent over its base, no gate) - every fire and those outside a window;
#   (c) each search term alone (35 over its base, no gate), 2004-2026;
#   (d) the conjunction, as the rule reads it.
# and, for the one gate episode outside a recession (October 1987), how low the claims line would have to be set for the
# crash to have opened a recession - the margin by which the labour leg rejects it.
# Run: PYTHONPATH=. python3 s2/q40.py
import sys,os,io,contextlib
sys.path.insert(0,os.getcwd()); sys.argv=['walk54.py','1962','2026','w54']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
SEARCH_TERMS=['unemp','layoffs','laidoff']; os.environ['BHS_SEARCH_TERMS']=','.join(SEARCH_TERMS)
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk54.py').read().split(_MARK)[0])

REC=[(pd.Timestamp(a)-pd.DateOffset(months=6),pd.Timestamp(b)+pd.offsets.MonthEnd(0)) for a,b in zip(PK,TR)]
def inwin(d): return any(a<=d<=b for a,b in REC)
def iso(d): return pd.Timestamp(d).date().isoformat()

# which series the claims week reads (from the walk's own call)
CALL=[l.strip() for l in open('walk39.py').read().splitlines() if 'leg_K_x(' in l and 'def ' not in l]
print('the walk calls the claims week as:', CALL[:2])
SER=None
for nm in ('ICc','IC','ic','icw','claims','ICSA','S_IC'):
    if nm in globals() and hasattr(globals()[nm],'index'): SER=globals()[nm]; print('claims series found in the lab:',nm,len(SER),iso(SER.index[0]),'->',iso(SER.index[-1])); break

# (a) the market gate alone
g=_crash2.dropna(); eps=[]; armed=True
for d,v in g.items():
    if armed and v>=20-EPS: eps.append((d,float(v))); armed=False
    elif not armed and v<20-EPS: armed=True
print('\n(a) THE GATE ALONE - the S&P 500 20 per cent under its 20-day high, first day of each episode since',iso(g.index[0]))
for d,v in eps: print(f'    {iso(d)}  {v:5.1f}   {"inside" if inwin(d) else "OUTSIDE"} a recession window')
print('    episodes:',len(eps),'| outside a recession window:',sum(1 for d,_ in eps if not inwin(d)))
for y0 in (1948,1967):
    e2=[(d,v) for d,v in eps if d>=pd.Timestamp(f'{y0}-01-01')]
    print(f'    since {y0} (the chronology the rule is scored on; claims begin 1967): episodes {len(e2)} | outside a recession window {sum(1 for d,_ in e2 if not inwin(d))} {[iso(d) for d,_ in e2 if not inwin(d)]}')

# (b) the claims week alone (gate switched off: cl=0)
if SER is not None:
    for pct in (35,):
        allf=_leg_K_claims(SER,pct,0.0)
        out=[iso(d) for d,m in allf if not inwin(d)]
        print(f'\n(b) THE CLAIMS WEEK ALONE - {pct} per cent over its base, no market gate, {iso(SER.index[0])}-{iso(SER.index[-1])}')
        print('    fires:',len(allf),'| outside a recession window:',len(out),out[:20])

# (c) each search term alone
print('\n(c) EACH SEARCH TERM ALONE - 35 per cent over its own base, no market gate, 2004-2026')
for tag,(_d,_g7,_rel) in GT_TERMS.items():
    f=leg_K_search_one(_rel,35,0.0); out=[iso(d) for d,m in f if not inwin(d)]
    print(f'    {tag:8s} fires {len(f):3d} | outside a recession window {len(out):3d}')

# (d) the conjunction, as the rule reads it
if SER is not None:
    both=leg_K_x(SER,35,20.0)
    print('\n(d) THE CONJUNCTION (the rule): fires',[iso(d) for d,m in both],'| outside a recession window:',[iso(d) for d,m in both if not inwin(d)])

# the margin at October 1987
if SER is not None:
    W=(pd.Timestamp('1987-09-01'),pd.Timestamp('1988-06-30'))
    print('\nTHE MARGIN AT OCTOBER 1987 (the gate held 19 October 1987, outside any recession)')
    hit=None
    for pct in (35,30,25,20,15,12,10,8,6,5,4,3,2,1):
        f=[d for d,m in _leg_K_claims(SER,float(pct),20.0) if W[0]<=d<=W[1]]
        if f and hit is None: hit=(pct,iso(f[0]))
    print('    the lowest claims line tested that still does NOT fire in 1987-88:', 'none of 35..1' if hit is None else f'above {hit[0]}')
    print('    the highest claims line that WOULD have fired:', hit if hit else 'no claims line down to 1 per cent fires - the claims week never moved')
    # the claims week's own reading through the window, for the record
    try:
        base=None
        for pct in (0.001,):
            pass
        s=SER[(SER.index>=W[0]-pd.Timedelta(days=400))&(SER.index<=W[1])]
        m4=s.rolling(4,min_periods=4).mean(); lo=m4.rolling(52,min_periods=20).min()
        rel=((m4/lo-1)*100).dropna()
        r=rel[(rel.index>=W[0])&(rel.index<=W[1])]
        print('    the claims four-week mean over its 52-week low through the window: max',round(float(r.max()),1),'per cent on',iso(r.idxmax()),'| at the crash week',round(float(r[r.index<=pd.Timestamp("1987-10-26")].iloc[-1]),1))
    except Exception as e: print('    (reading:',e,')')
