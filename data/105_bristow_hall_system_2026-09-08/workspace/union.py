exec(open('expose.py').read().split('print(f"\\n{\'object\':52}')[0])
import sys, os, io, contextlib, pandas as pd, numpy as np
os.chdir(os.path.expanduser("~/mnt/")+"Recession Papers/Claude RA/paper2_exploration_2026-09-03/ladder")
sys.path.insert(0,"/sessions/rcw-01xagfihqbjtyrorxs2n1y72/runlab")
import shim
sys.path.insert(0, shim.W+"/lab/weekly")
with contextlib.redirect_stdout(io.StringIO()):
    import american_chronology as AC
sahm=AC.sahm_rt(); vac=AC.vacancy_gap_rt(2,6)
awh=(FP['AWHMAN'].rolling(6).max()/FP['AWHMAN']-1)*100
pay=-(FP['PAYEMS']/FP['PAYEMS'].shift(3)-1)*100
def hits(o,line):
    o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hitlist):
    idx=pd.date_range('1960-01-01','2026-07-01',freq='MS')
    h=np.zeros(len(idx),bool)
    for x in hitlist: h |= x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    fwd=s[::-1].rolling(1,min_periods=1).max()[::-1].astype(bool)
    back=s.rolling(7,min_periods=1).max().astype(bool)
    return (fwd|back)[q].mean()*100, int(q.sum())
S=hits(sahm,0.5); V=hits(vac,0.36); A=hits(awh,2.5); P=hits(pay,0.3)
for name,parts in [("shipped pair  Sahm 0.50 OR vacancy 0.36",[S,V]),
                   ("pair + factory hours 2.5%",[S,V,A]),
                   ("pair + payrolls 3-month 0.3%",[S,V,P]),
                   ("pair + hours + payrolls",[S,V,A,P]),
                   ("hours + payrolls alone",[A,P])]:
    w,n=win_expo(parts); print(f"{name:44} window exposure {w:5.2f}%   ({n} quiet months)")
