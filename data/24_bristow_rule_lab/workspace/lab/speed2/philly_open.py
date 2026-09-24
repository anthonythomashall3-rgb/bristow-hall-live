"""The Philadelphia Fed survey as a trough object gated only by the route's open state (3 September 2026, night, fourth
pass): without the activity panel's D as its gate it fires on every bounce inside a recession (March 1970, April 1974,
December 1981, October 1990, March 2001, April 2008, September 2023).  Not adopted; leg P keeps its D gate.
Output philly_open.log."""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed'); sys.path.insert(0,'/home/claude/lab/weekly')
import numpy as np, pandas as pd, twostage_us as TU, ecbcs_speed as E
P=TU.philly(); X=pd.DataFrame({k:E.sa_rt(v) for k,v in P.items()}).dropna(how='all')
ga=X['general activity'].dropna()
print("Philly general activity (real-time SA), 1968-05 on; read as a trough object gated only by the route's OPEN state (episode opened at the peak call): the first month the index stands a points above its minimum since the opening, for r months")
EP=[('1970-01-31','1970-11'),('1974-02-16','1975-03'),('1980-03-20','1980-07'),('1981-12-20','1982-11'),('1990-09-20','1991-03'),('2001-03-31','2001-11'),('2007-12-28','2009-06'),('2020-03-28','2020-04'),('2023-08-28','2026-02')]
def md(a,b): return (a.year-b.year)*12+a.month-b.month
for a_,r in ((5,1),(10,1),(15,1),(10,2),(20,1)):
    row=[]
    for op,tr in EP:
        op=pd.Timestamp(op); m0=pd.Timestamp(op.year,op.month,1)
        seg=ga[m0:]
        call=None; lo=None
        for i,t in enumerate(seg.index):
            s=seg[:t]; mn=s.min()
            if len(s)>=r+1 and (s.iloc[-r:]>=mn+a_).all() and s.idxmin()<t:
                call=t; lo=s.idxmin(); break
        T=pd.Timestamp(tr+'-01')
        row.append(f"{tr}: call {call:%Y-%m} dated {lo:%Y-%m} ({md(lo,T):+d}, call {md(call,T):+d}m)" if call is not None else f'{tr}: none')
    print(f'\na={a_}, r={r}'); [print('   ',x) for x in row]
print('\nthe survey through the 1970 pause (real-time SA general activity), 1970-01..1971-03:', ga['1970-01':'1971-03'].round(0).tolist())
