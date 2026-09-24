"""THE DEEP BRANCH AS A QUANTILE RULE, NOT A NUMBER. The claims deep branch fires when the four-week mean of first-
print initial claims stands a given per cent above its own fifty-two-week minimum. That per cent has so far been a grid
number, and the causal chooser will not pick the value that catches July 1981. Here the threshold is instead built the
way the spread's line is built: a multiple of the largest rise ever seen in a quiet week up to that date."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('deep2.out','w')"))
m4=ICfp.rolling(4).mean(); rel_=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
P(f"claims deep reading: {rel_.index[0]:%Y-%m-%d} to {rel_.index[-1]:%Y-%m-%d}, {len(rel_)} weeks")
ANN={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
     '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]
def quiet_max(cut):
    """largest reading in any week that, at the cut, was known to be quiet: outside every announced recession window"""
    ks=[i for i in range(13) if ANNT[i]<cut]
    v=rel_[rel_.index<cut]
    if not len(v): return None
    mask=pd.Series(True,index=v.index)
    for i in ks:
        a=PK[i]-pd.DateOffset(months=9); b=TR[i]+pd.DateOffset(months=6)
        mask &= ~((v.index>=a)&(v.index<=b))
    q=v[mask]
    return (float(q.max()),q.idxmax()) if len(q) else None

def quiet_q(cut,qs=(0.90,0.95,0.975,0.99)):
    ks=[i for i in range(13) if ANNT[i]<cut]
    v=rel_[rel_.index<cut]
    if not len(v): return None
    mask=pd.Series(True,index=v.index)
    for i in ks:
        a=PK[i]-pd.DateOffset(months=9); b=TR[i]+pd.DateOffset(months=6)
        mask &= ~((v.index>=a)&(v.index<=b))
    q=v[mask]
    return [float(q.quantile(x)) for x in qs], len(q)
P(f"\n{'as of':8s} {'n quiet':>8s} {'p90':>7s} {'p95':>7s} {'p97.5':>7s} {'p99':>7s}")
for Y in [1971,1974,1978,1980,1981,1983,1990,2001,2008,2020,2022,2026]:
    r=quiet_q(pd.Timestamp(Y,1,1))
    if r: P(f"{Y:<8d} {r[1]:8d} "+" ".join(f"{x:7.2f}" for x in r[0]))
r=quiet_q(pd.Timestamp(1981,7,1)); P(f"\nas of July 1981: n={r[1]}  p90={r[0][0]:.2f}  p95={r[0][1]:.2f}  p97.5={r[0][2]:.2f}  p99={r[0][3]:.2f}")
out.close()
