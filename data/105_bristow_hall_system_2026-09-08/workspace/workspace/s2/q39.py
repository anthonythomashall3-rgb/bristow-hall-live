# q39.py - CAN 2020 BE FASTER THAN 12 MARCH? The sudden stop's market gate first held (20 under the 20-day high) at the
# close of 12 March 2020, so under that gate no datum can fire earlier. The walk's own grid also carries (35,15),
# (30,15) and (30,10); here every search term is read against gates 20, 15, 12 and 10 and search lines 35 and 30, on the
# stitched histories 2004-2026: every fire, every fire outside a recession window (six months before the peak month to the
# trough month; 2024 the rule's own), and the 2020 day. A lower gate that fires anywhere outside a window is refused.
# Run: PYTHONPATH=. python3 s2/q39.py
import sys,os,io,contextlib,pickle
sys.path.insert(0,os.getcwd()); sys.argv=['walk54.py','1962','2026','w54']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
SEARCH_TERMS=['unemp','layoffs','laidoff']; os.environ['BHS_SEARCH_TERMS']=','.join(SEARCH_TERMS)
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk54.py').read().split(_MARK)[0])
REC=[(pd.Timestamp(a)-pd.DateOffset(months=6),pd.Timestamp(b)+pd.offsets.MonthEnd(0)) for a,b in zip(PK,TR)]
def inwin(d): return any(a<=d<=b for a,b in REC)
print('first days the S&P 500 stood g under its 20-day high in Feb-Mar 2020:',{g:next((d.date().isoformat() for d,v in _crash2['2020-02-01':'2020-03-31'].items() if v>=g-EPS),None) for g in (20,15,12,10)})
for pct in (35,30):
    for g in (20,15,12,10):
        allf=[]; out=[]
        for tag,(_day,_g7,_rel) in GT_TERMS.items():
            f=[d for d,m in leg_K_search_one(_rel,pct,g)]
            allf+=[(d,tag) for d in f]; out+=[(d.date().isoformat(),tag) for d in f if not inwin(d)]
        d20=sorted(d for d,t in allf if pd.Timestamp('2020-01-01')<=d<=pd.Timestamp('2020-06-30'))
        print(f'line {pct}, gate {g}: fires {len(allf)} | outside a recession window: {sorted(out)} | first 2020 fire: {d20[0].date().isoformat() if d20 else None}')
