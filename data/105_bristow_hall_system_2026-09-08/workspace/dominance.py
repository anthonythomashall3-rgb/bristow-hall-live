"""IS v8 THE LOWEST HAZARD FOR ITS SPEED?  Every subset of the five claims legs x every subset of the four confirming
objects, at the frozen lines: record (peaks called of 12, other calls, median and worst lag) and hazard = first factor
(quiet claims episodes per quiet year, for that leg subset) x window exposure (6 back, 4 forward) of that confirmer union.
A configuration DOMINATES v8 if it is at least as good on every one of: called, other calls, median, worst, hazard - and
strictly better on one.  (5 September 2026)"""
exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, itertools, numpy as np, pandas as pd, os
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l
f3 =lambda v,l:(-(v/v.shift(3)-1)*100)/l
PR =lambda a,b: pd.concat([a,b],axis=1).min(axis=1).dropna()
P1=PR(f12(AWH,2.0),f3(ND,1.2))
CONF={'S':None,'V':dict(name='vacancy',gap=vr,line=0.36,pub_day=30),'H':dict(name='housing35',gap=pair(35),line=1.0,pub_day=18),'P':dict(name='pair',gap=P1,line=1.0,pub_day=5)}
cwd=os.getcwd()
exec(open('hazard_v5.py').read().split('print("CONTROL')[0])       # hits, win_expo, quiet, S, V, H(housing), FP
os.chdir(cwd)
HS={'S':S,'V':V,'H':H,'P':hits(P1,1.0)}
allm=pd.date_range('1949-01-01','2026-08-01',freq='MS'); qm=quiet(allm); QY=int(qm.sum())/12.0
def me(t): return t+pd.offsets.MonthEnd(0)
def record(on):
    lags={}; other=[]
    for pub,d in on:
        hit=None
        for i,(p,q) in enumerate(zip(PK,TR)):
            if p-pd.DateOffset(months=6)<=d<=q: hit=i; break
        if hit is None: other.append(d)
        elif hit not in lags: lags[hit]=(pub-me(PK[hit])).days
    L=list(lags.values()); return len(lags),len(other),(float(np.median(L)) if L else np.nan),(max(L) if L else np.nan),other
def onsets(legs, conf):
    sec=[CONF[c] for c in conf if c!='S']; sahm=g if 'S' in conf else None
    with contextlib.redirect_stdout(io.StringIO()):
        if conf: t=B.american_chronology({q:PLU[q] for q in legs},{q:TLG[q] for q in TR3},sahm=sahm,line=0.5,second=sec if sec else None,horizon_months=4,back_months=6)
        else:    t=B.american_chronology({q:PLU[q] for q in legs},{q:TLG[q] for q in TR3})
    return [(o['published'],o['date']) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')]
def first_factor(legs):
    on=onsets(legs,()); n=sum(1 for pub,d in on if qm.get(pd.Timestamp(d.year,d.month,1),False)); return n/QY, n
rows=[]
for nl in range(1,6):
    for legs in itertools.combinations(PK5,nl):
        ff,nq=first_factor(legs)
        for nc in range(0,5):
            for conf in itertools.combinations('SVHP',nc):
                called,other,med,worst,oth=record(onsets(legs,conf))
                expo=win_expo([HS[c] for c in conf],7,5)[0] if conf else 100.0
                hz=ff*expo/100
                rows.append(dict(legs=''.join(legs),conf=''.join(conf) or '-',called=called,other=other,med=med,worst=worst,ff=ff*100,nq=nq,expo=expo,hazard=hz*100,oneIn=(1/hz if hz>0 else np.inf)))
df=pd.DataFrame(rows); df.to_csv('DOMINANCE_2026-09-05.csv',index=False)
v8=df[(df.legs=='ABCMU')&(df.conf=='SVHP')].iloc[0]
print(f"v8: called {v8.called}/12 other {v8.other} median {v8.med:.0f} worst {v8.worst} | first factor {v8.ff:.2f}%/yr (quiet episodes {v8.nq}) x exposure {v8.expo:.2f}% = hazard {v8.hazard:.3f}%/yr, one in {v8.oneIn:.0f}")
dom=df[(df.called>=v8.called)&(df.other<=v8.other)&(df.med<=v8.med)&(df.worst<=v8.worst)&(df.hazard<=v8.hazard)&((df.called>v8.called)|(df.other<v8.other)|(df.med<v8.med)|(df.worst<v8.worst)|(df.hazard<v8.hazard))]
print(f"\nconfigurations that DOMINATE v8: {len(dom)}")
print(dom.to_string(index=False) if len(dom) else "  none")
full=df[(df.called==12)&(df.other<=1)].sort_values(['hazard','med'])
print(f"\nall configurations with 12/12 and at most one other call ({len(full)}), by hazard then median:")
print(full.head(40).to_string(index=False,float_format=lambda x:f'{x:.2f}'))
print("\nthe frontier: for each hazard level, the fastest median among complete configurations")
fr=[]; best=1e9
for _,r in full.sort_values('hazard').iterrows():
    if r.med<best: best=r.med; fr.append(r)
print(pd.DataFrame(fr)[['legs','conf','called','other','med','worst','hazard','oneIn']].to_string(index=False,float_format=lambda x:f'{x:.2f}'))
