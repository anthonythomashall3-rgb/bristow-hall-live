from mini import *
from legu_min import leg_U, s_cur, spl
def leg_U_min(series,line=0.50,look=52,pub=5,how='min'):
    """dated at the month of the insured rate's 52-week minimum preceding the crossing (the rate's own trough = the peak of activity),
    or at the last week the rate stood at that minimum"""
    mn=series.rolling(look,min_periods=look).min().shift(1); gap=series-mn; c=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line:
            w=series[(series.index>t-pd.Timedelta(weeks=look))&(series.index<t)]
            if how=='min': d=w.idxmin()
            else: d=w[w==w.min()].index[-1]
            c.append((t+pd.Timedelta(days=pub),pd.Timestamp(d.year,d.month,1))); armed=False
        elif not armed and v<=0.0: armed=True
    return c
for nm,calls in [('U dated at the crossing week',leg_U(s_cur)),('U dated at the IUR minimum (first week)',leg_U_min(s_cur,how='min')),('U dated at the IUR minimum (last week at min)',leg_U_min(s_cur,how='last')),('U(fp) dated at the IUR minimum (last)',leg_U_min(spl,how='last'))]:
    errs=[]
    for p,d in calls:
        near=min(PK,key=lambda k:abs(md(d,k))); errs.append((near.strftime('%Y-%m'),d.strftime('%Y-%m'),md(d,near)))
    print(f"{nm:46}",[(e[0],e[1],e[2]) for e in errs]," exact",sum(1 for e in errs if e[2]==0),"within1",sum(1 for e in errs if abs(e[2])<=1),"mae",round(np.mean([abs(e[2]) for e in errs]),2))
