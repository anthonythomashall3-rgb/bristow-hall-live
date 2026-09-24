"""IS IT FITTED?  The causal replay of the route's own selections (5 September 2026).

Every line the route chose itself - leg U's 0.50, the vacancy 0.36, housing 35, the hours x nondurable pair (2.0, 1.20) -
is re-chosen at each recession using ONLY the record before it, by the route's own leave-one-out criterion (every prior
recession called with at most one other call; then the fastest median), in the order the route built them (U, then the
vacancy line, then housing, then the pair); the next recession is then scored with those lines.  Sahm's 0.50 is inherited
(published 2019) and is not re-chosen.  The tally is the honest out-of-sample record: what a user of this procedure would
have seen recession by recession.  Beside it, the frozen rule's in-sample record."""
exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, itertools, numpy as np, pandas as pd, json
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l
f3 =lambda v,l:(-(v/v.shift(3)-1)*100)/l
PR =lambda a,b: pd.concat([a,b],axis=1).min(axis=1).dropna()
SAHM=0.50
def objs(u,v,h,x,y,sl=None):
    pl=dict(PL); pl['U']=leg_U2(line=u)
    sec=[]
    if v is not None: sec.append(dict(name='vacancy',gap=vr,line=v,pub_day=30))
    if h is not None: sec.append(dict(name='housing',gap=pair(h),line=1.0,pub_day=18))
    if x is not None: sec.append(dict(name='pair',gap=PR(f12(AWH,x),f3(ND,y)),line=1.0,pub_day=5))
    return pl,sec
CACHE={}
def chron(u,v,h,x,y,sl=None):
    k=(u,v,h,x,y,sl)
    if k in CACHE: return CACHE[k]
    pl,sec=objs(u,v,h,x,y)
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:pl[q] for q in PK5},{q:TLG[q] for q in TR3},sahm=g,line=(SAHM if sl is None else sl),second=sec,horizon_months=4,back_months=6)
    on=[(o['published'],o['date']) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')]
    CACHE[k]=on; return on
def me(t): return t+pd.offsets.MonthEnd(0)
def scorer(on, until=None, since=None):
    """lags (days from the peak month's end) per committee peak inside [since, until); other calls dated in the same span."""
    lags={}; other=[]
    for pub,d in on:
        if until is not None and d>=until: continue
        if since is not None and d<since: continue
        hit=None
        for i,(p,q) in enumerate(zip(PK,TR)):
            if p-pd.DateOffset(months=6)<=d<=q: hit=i; break
        if hit is None: other.append(d)
        elif hit not in lags: lags[hit]=(pub-me(PK[hit])).days
    return lags,other
GU=[0.30,0.40,0.50,0.60,0.70]; GV=[0.24,0.30,0.36,0.42,0.50,0.60]; GH=[25,30,35,40,45]; GX=[1.4,1.7,2.0,2.5,3.0]; GY=[1.0,1.2,1.4,1.6]
MODE='fast'
def pick(cands, k):
    """the recessions before k only.  'fast': every prior recession called, at most one other call, then the fastest median
    (loo.py's criterion).  'safe': every prior recession called, the FEWEST other calls, then the HIGHEST line - Rule 21's
    corner, the setting the route says it adopts on a plateau."""
    until=PK[k]-pd.DateOffset(months=6); prior=[i for i in range(k) if PK[i]>=pd.Timestamp('1948-06-01')]
    best=None
    for j,c in enumerate(cands):
        lags,other=scorer(chron(*c) if len(c)==6 else chron(*c,sl=SAHM),until=until)
        got=[lags[i] for i in prior if i in lags]
        if MODE=='fast': key=(-(len(got)), max(len(other)-1,0), float(np.median(got)) if got else 1e9)
        else: key=(-(len(got)), len(other), -j)          # candidates are listed from the fastest line to the safest
        if best is None or key<best[0]: best=(key,c)
    return best[1]
import sys
MODE=sys.argv[1] if len(sys.argv)>1 else 'fast'
print(f"CAUSAL REPLAY, criterion = {MODE}  (each fold's lines chosen on the recessions before it; recession k scored with them)")
print(f"  {'recession':10} {'U':>5} {'vac':>5} {'hous':>5} {'hours':>6} {'ndur':>5}   {'called':>6} {'lag d':>6}   other calls until the next fold")
GS=[0.30,0.40,0.50,0.60,0.70]
EXT=len(sys.argv)>2 and sys.argv[2]=='ext'
tally=[]; chosen={}
for k in range(len(PK)):
    if k<3:   # need at least three prior recessions to choose anything
        continue
    if EXT:
        sl=pick([(0.50,None,None,None,None,sl_) for sl_ in GS],k)[5]
        SAHM=sl
    u=pick([(u,None,None,None,None) for u in GU],k)[0]
    v=pick([(u,v,None,None,None) for v in GV],k)[1]
    h=pick([(u,v,h,None,None) for h in GH],k)[2]
    x,y=pick([(u,v,h,x,y) for x in GX for y in GY],k)[3:]
    chosen[k]=(u,v,h,x,y)
    since=PK[k]-pd.DateOffset(months=6); until=(PK[k+1]-pd.DateOffset(months=6)) if k+1<len(PK) else pd.Timestamp('2026-12-01')
    lags,other=scorer(chron(u,v,h,x,y,sl=SAHM),until=until,since=since)
    lag=lags.get(k); oth=[d for d in other]
    tally.append((k,lag,oth))
    print(f"  {PK[k]:%Y-%m}  S{SAHM:4.2f}  {u:5.2f} {v:5.2f} {h:5.0f} {x:6.2f} {y:5.2f}   {'yes' if lag is not None else 'NO':>6} {'' if lag is None else lag:>6}   {', '.join(f'{d:%Y-%m}' for d in oth)}")
got=[l for _,l,_ in tally if l is not None]; oth=[d for _,_,o in tally for d in o]
print(f"\n  causal: {len(got)}/{len(tally)} recessions called (1960 on), median lag {np.median(got):.0f} d, worst {max(got)}, other calls {len(oth)}: {', '.join(f'{d:%Y-%m}' for d in oth)}")
lags,other=scorer(chron(0.50,0.36,35,2.0,1.2))
print(f"  frozen v8 in-sample: {len(lags)}/{len(PK)} called, median {np.median(list(lags.values())):.0f} d, worst {max(lags.values())}, other calls {len(other)}: {', '.join(f'{d:%Y-%m}' for d in other)}")
# the split-sample version: everything chosen on 1948-1982 (eight recessions), scored 1990-2020
k=8; u=pick([(u,None,None,None,None) for u in GU],k)[0]; v=pick([(u,v,None,None,None) for v in GV],k)[1]; h=pick([(u,v,h,None,None) for h in GH],k)[2]; x,y=pick([(u,v,h,x,y) for x in GX for y in GY],k)[3:]
lags,other=scorer(chron(u,v,h,x,y),since=PK[8]-pd.DateOffset(months=6))
print(f"  split sample, lines chosen on 1948-82 = U {u} vac {v} housing {h} pair ({x},{y}); 1990-2026: {len([i for i in lags if i>=8])}/4 called, lags {[lags.get(i) for i in range(8,12)]}, other {', '.join(f'{d:%Y-%m}' for d in other)}")
json.dump({str(k):v for k,v in chosen.items()},open('causal_choices.json','w'))
