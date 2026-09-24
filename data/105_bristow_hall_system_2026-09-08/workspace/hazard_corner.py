from mini import *
from legu_min import leg_U, s_cur
from scipy import stats
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PK,TR): q[(idx>=p-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line):
    o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hitlist, back=7, fwd=5, start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hitlist: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    f=s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool); b=s.rolling(back,min_periods=1).max().astype(bool)
    return (f|b)[q].mean()*100, int(q.sum())
for vl in [0.30,0.36]:
    V=hits(vr,vl); H=hits(PAIR,1.0); P=hits(P1,1.0)
    eV,n=win_expo([V]); eVHP,_=win_expo([V,H,P]); eVb,_=win_expo([V],back=7,fwd=1,start='1949-01-01')
    print(f"vacancy line {vl}: window (6,4) exposure V {eV:.2f}%, V|H|P {eVHP:.2f}% ({n} quiet months 1960-2026); six-back exposure {eVb:.2f}%")
idx=pd.date_range('1972-01-01','2026-07-01',freq='MS'); q=quiet(idx); QY=q.sum()/12
print(f"leg U at 0.45: quiet-month proposals 1972-2026: {sum(1 for p,d in leg_U(s_cur,0.45) if q.reindex([pd.Timestamp(d.year,d.month,1)]).fillna(False).iloc[0])} in {QY:.1f} quiet years -> bound {3/QY*100:.2f}%/yr")
idx2=pd.date_range('1949-01-01','2026-07-01',freq='MS'); q2=quiet(idx2); QY2=q2.sum()/12
for sl in [0.43,0.50]:
    eps=[]; armed=True
    for m,v in g.items():
        if m<idx2[0]: continue
        if armed and v>=sl:
            armed=False
            if q2.reindex([m]).fillna(False).iloc[0]: eps.append(m.strftime('%Y-%m'))
        elif not armed and v<sl: armed=True
    print(f"Sahm line {sl}: quiet crossings {len(eps)} {eps} in {QY2:.1f} quiet years = {len(eps)/QY2*100:.2f}%/yr; upper bound {stats.chi2.ppf(0.95,2*(len(eps)+1))/2/QY2*100:.2f}%/yr")
