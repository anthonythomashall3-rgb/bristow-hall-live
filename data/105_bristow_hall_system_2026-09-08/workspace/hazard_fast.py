from mini import *
from legu_min import s_cur, spl
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('hazard_fast.out','w')"))
from scipy import stats
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PK,TR): q[(idx>=p-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line): o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hitlist, back=7, fwd=5, start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hitlist: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    f=s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool); b=s.rolling(back,min_periods=1).max().astype(bool)
    return (f|b)[q].mean()*100, int(q.sum())
H=hits(PAIR,1.0); eH,n=win_expo([H]); P(f"housing x rate pair, window (6,4) exposure on quiet months 1960-2026: {eH:.2f}% ({n} quiet months); months at line in quiet: {int(H.reindex(pd.date_range('1960-01-01','2026-07-01',freq='MS')).fillna(False)[quiet(pd.date_range('1960-01-01','2026-07-01',freq='MS'))].sum())}")
for vint,s,Bx in [('current file',s_cur,BR),('first prints',spl,BRs)]:
    gp=gapof(s); idx=pd.date_range('1972-01-01','2026-07-01',freq='MS'); q=quiet(idx); QY=q.sum()/12
    nq=sum(1 for p,dd in leg_gap(gp,0.25) if q.reindex([dd]).fillna(False).iloc[0])
    r=nq/QY; rb=stats.chi2.ppf(0.95,2*(nq+1))/2/QY
    P(f"{vint}: IUR>=0.25 quiet proposals {nq} in {QY:.1f} quiet years = {r*100:.1f}%/yr (bound {rb*100:.1f}); x housing exposure {eH:.2f}% -> hazard {r*eH:.3f}%/yr observed (one in {1/(r*eH/100):.0f}), {rb*eH:.3f}% at the bound (one in {1/(rb*eH/100):.0f})")
    idx2=pd.date_range('1987-06-01','2026-07-01',freq='MS'); q2=quiet(idx2); QY2=q2.sum()/12
    nb=sum(1 for p,dd in leg_br(Bx) if q2.reindex([dd]).fillna(False).iloc[0]); rb2=stats.chi2.ppf(0.95,2*(nb+1))/2/QY2
    P(f"{vint}: breadth>=50 quiet proposals {nb} in {QY2:.1f} quiet years; x housing -> {nb/QY2*eH:.3f}%/yr observed, {rb2*eH:.3f}% at the bound (one in {1/(rb2*eH/100):.0f})")
out.close()
