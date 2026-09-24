import sys, os
os.chdir("/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/ladder")
sys.path.insert(0,os.getcwd())
import io, contextlib
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
print("calendar span:", cal[0].date(), "->", cal[-1].date(), "N =", N)
for nm,arr in [("Sahm 0.35",SAHM[0.35]),("IUR4 gap 0.40",gapch(iur4,0.40)),("payrolls",PAY),("housing -20x2",persist2(h3,20)),("bill 1.43/60d",fall(tb6,60,1.43))]:
    a=np.asarray(arr,bool); idx=np.flatnonzero(a)
    print(f"  {nm:16} first True {cal[idx[0]].date() if len(idx) else '-'}")
print("gate 12m: first True", cal[np.flatnonzero(np.asarray(GATE[12],bool))[0]].date())
for nm in ["sahm","iur4","ma8d","h3","tb6","PAYs" ]:
    v=globals().get(nm)
    if v is None: continue
    try:
        s=pd.Series(np.asarray(v,float),index=cal).dropna()
        print(f"  series {nm:6} {s.index[0].date()} -> {s.index[-1].date()}")
    except Exception as e: print("  ",nm,"?",e)
