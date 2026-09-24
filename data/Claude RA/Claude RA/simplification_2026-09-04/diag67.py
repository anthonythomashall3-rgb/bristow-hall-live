import sys, os, io, contextlib
os.chdir("/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/ladder")
sys.path.insert(0,os.getcwd())
with contextlib.redirect_stdout(io.StringIO()):
    exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool)
CH={"Sahm>=0.35":SAHM[0.35],"IUR gap>=0.40":gapch(iur4,0.40),"payrolls<=-0.1%":PAY,
    "housing -20% x2":persist2(h3,20),"bill -1.43/60d":fall(tb6,60,1.43)}
w=(cal>=pd.Timestamp("1967-06-01"))&(cal<=pd.Timestamp("1968-03-01"))
print("gate armed on 1967-10-11:", bool(G[np.argmin(abs(cal-pd.Timestamp('1967-10-11')))]))
for nm,c in CH.items():
    a=np.asarray(c,bool)&w
    d=[str(cal[i].date()) for i in np.flatnonzero(a)]
    print(f"  {nm:18} fires in window: {d[:4]}{' ...' if len(d)>4 else ''}  (n={len(d)})")
for nm in ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"]:
    a=np.asarray(BS[nm],bool)&w
    print(f"  {nm:18} n={a.sum()}")
# how big a threshold change kills it?
print("\nraise the firing channel's threshold:")
for th in (0.35,0.40,0.45,0.50):
    a=np.asarray(SAHM[th],bool)&w
    print(f"   Sahm>={th}: fires in 1967 window {a.sum()}")
for g in (0.40,0.45,0.50,0.55):
    a=np.asarray(gapch(iur4,g),bool)&w
    print(f"   IUR gap>={g}: fires in 1967 window {a.sum()}")
for pct in (20,22,25,30):
    a=np.asarray(persist2(h3,pct),bool)&w
    print(f"   housing -{pct}% x2: fires in 1967 window {a.sum()}")
