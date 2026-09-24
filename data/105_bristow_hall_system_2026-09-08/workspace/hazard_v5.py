"""The route's false-alarm hazard, RECOMPUTED on the corrected symmetric window.

The withdrawn figure measured the second factor over a window reaching ONE
MONTH forward while the route allowed EIGHTEEN.  The window is now six months
either side.  This script uses the route's OWN exposure function verbatim --
union.py's win_expo, on union.py's own index and objects -- so the 7.39 per
cent the route has been quoting is reproduced as a control before anything new
is printed.  Rule Zero: if the control does not reproduce, nothing below it is
citable.
"""
exec(open('expose.py').read().split('print(f"\\n{\'object\':52}')[0])
import sys, os, io, contextlib, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from scipy import stats
os.chdir(os.path.expanduser("~/mnt/")+"Recession Papers/Claude RA/paper2_exploration_2026-09-03/ladder")
sys.path.insert(0,"/sessions/rcw-01xagfihqbjtyrorxs2n1y72/runlab"); import shim
sys.path.insert(0, shim.W+"/lab/weekly")
with contextlib.redirect_stdout(io.StringIO()): import american_chronology as AC
D=os.path.expanduser("~/mnt/")+"Onset Detector Data/30_simplified_route_2026-09-04/"
sahm=AC.sahm_rt(); vac=AC.vacancy_gap_rt(2,6)
pay=-(FP['PAYEMS']/FP['PAYEMS'].shift(3)-1)*100
awh=(FP['AWHMAN'].rolling(6).max()/FP['AWHMAN']-1)*100
lh=np.log(FP['HOUST'])*100
PAIR=pd.concat([(lh.rolling(12).max()-lh.rolling(2).mean())/35.0,
                (first_prints('UNRATE')-first_prints('UNRATE').rolling(12).min())/0.20],axis=1).min(axis=1).dropna()
E=pd.read_csv(D+"../37_dol_eta5159_2026-09/panel/panel_5159_monthly.csv",parse_dates=['month'])
w=E.pivot_table(index='month',columns='st',values='ic_total',aggfunc='sum').where(lambda d:d>0)
ly=np.log(w); y=ly-ly.shift(12); cov=y.notna().sum(axis=1)
B5=(y.ge(0.20).sum(axis=1)/cov.where(cov>=30)).dropna()*100
def hits(o,line):
    o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hitlist, back=7, fwd=1):
    idx=pd.date_range('1960-01-01','2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hitlist: h |= x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    f=s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool)
    b=s.rolling(back,min_periods=1).max().astype(bool)
    return (f|b)[q].mean()*100, int(q.sum())
S=hits(sahm,0.5); V=hits(vac,0.36); P3h=hits(pay,0.3); A=hits(awh,2.5)
H=hits(PAIR,1.0); E5=hits(B5,40.0)
print("CONTROL -- the route's own function, its own window (6 back, 30 days forward)")
for nm,parts,expect in [("shipped pair, Sahm 0.50 OR vacancy 0.36",[S,V],"5.80 / 7.39"),
                        ("pair + payrolls 0.3%",[S,V,P3h],"7.39"),
                        ("pair + payrolls + hours 2.5%",[S,V,P3h,A],"12.47")]:
    e,n=win_expo(parts); print(f"   {nm:44}{e:6.2f}%   ({n} quiet months)   published: {expect}")
print("\nTHE SHIPPED SET, both windows")
SET=[S,V,P3h,E5,H]
for nm,(bk,fw) in [("WITHDRAWN basis: 6 back, 1 month forward",(7,1)),
                   ("the route as it ran: 6 back, 18 forward",(7,19)),
                   ("CORRECTED: 6 back, 6 forward",(7,7))]:
    e,n=win_expo(SET,bk,fw); print(f"   {nm:44}{e:6.2f}%   ({n} quiet months)")
E_corr,_=win_expo(SET,7,7); E_old,_=win_expo([S,V],7,1)
print("\nFIRST FACTOR -- how often the claims side opens in a quiet month")
print("   the numerator and the denominator must be the same object: episodes opening in a QUIET")
print("   MONTH, over QUIET MONTHS. Counting episodes in partly-quiet years against wholly-quiet")
print("   years is the denominator mismatch ladder memo 37 names, and it flatters the rate.")
allm=pd.date_range('1949-01-01','2026-08-01',freq='MS'); qm=quiet(allm)
QM=int(qm.sum()); QY=QM/12.0
print(f"   quiet months 1949-2026: {QM}  ({QY:.1f} quiet years)")
print(f"   claims episodes opening in a quiet month: 3  (Jul 1951, Mar 1952, Feb 1967)")
r_obs=3/QY; r_hi=stats.chi2.ppf(0.95,2*(3+1))/2/QY
print(f"   P(a claims episode opens per quiet year): observed {r_obs*100:.2f}%, upper 95% bound {r_hi*100:.2f}%")
print("\nROUTE HAZARD")
for lab,E in [("on the corrected symmetric window",E_corr)]:
    print(f"   {lab}")
    print(f"      observed   {r_obs*100:5.2f}% x {E:5.2f}%  =  {r_obs*E/100*100:.4f}% a year   -- one false episode in {100/(r_obs*E):,.0f} years")
    print(f"      upper 95%  {r_hi*100:5.2f}% x {E:5.2f}%  =  {r_hi*E/100*100:.4f}% a year   -- one in {100/(r_hi*E):,.0f} years")
    print(f"      over a 6.5-year expansion: {(1-(1-r_obs*E/100)**6.5)*100:.2f}% observed, {(1-(1-r_hi*E/100)**6.5)*100:.2f}% at the bound")
    print(f"      over a 10-year expansion:  {(1-(1-r_obs*E/100)**10)*100:.2f}% observed, {(1-(1-r_hi*E/100)**10)*100:.2f}% at the bound")
print(f"\n   for comparison, the same arithmetic on the WITHDRAWN window: "
      f"{r_obs*E_old/100*100:.4f}% to {r_hi*E_old/100*100:.4f}% a year")
print(f"   the correction multiplies the route's hazard by {E_corr/E_old:.2f}.")
