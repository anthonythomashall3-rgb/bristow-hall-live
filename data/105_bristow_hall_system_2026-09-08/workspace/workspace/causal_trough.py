"""IS THE TROUGH SIDE FITTED?  K's drop (4.0 log points, weekly continued claims), J's (5.0, monthly continued claims) and H's
(8.0, monthly initial claims) were set on the full record ("the lowest drop with no 1970 misfire").  Re-chosen at each recession
from the record before it, two criteria stated in advance (fast: every prior trough closed within six months, fewest early
closes, then the fastest median; safe: fewest early closes, every prior trough closed, then the highest drops), and the next
trough scored with those drops.  (5 September 2026)"""
exec(open('dominance.py').read().split('rows=[]')[0])
import sys
MODE=sys.argv[1] if len(sys.argv)>1 else 'safe'
L=G['L']; T=G['T']; nat=L._nat_rt(); icm=np.log(nat['initial claims'].dropna()); ccm=np.log(nat['continued weeks claimed'].dropna())
def troughlegs(k,j,h):
    K=[(p,d) for p,d in T.C.calls(T.C.series(4),6,k,30.) if p>=pd.Timestamp('1969-06-01')]
    Hh=[(L.pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(icm,drop=h)]
    Jj=[(L.pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(ccm,drop=j)]
    Hh=[x for x in Hh if x[0]>=L.RECORD_START]; Jj=[x for x in Jj if x[0]>=L.RECORD_START]
    return dict(K=K,J=Jj,H=Hh)
CACHE={}
def turns(k,j,h):
    key=(k,j,h)
    if key in CACHE: return CACHE[key]
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:PLU[q] for q in PK5},troughlegs(k,j,h),sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']],horizon_months=4,back_months=6)
    CACHE[key]=t; return t
def score_troughs(t, until=None, since=None):
    """for each committee trough: the end call of the downturn opened at that peak: lag (days from the trough month's end), date error (months)"""
    res={}; early=[]
    cur=None
    for o in t:
        if o['kind']=='peak':
            cur=None
            for i,(p,q) in enumerate(zip(PK,TR)):
                if p-pd.DateOffset(months=6)<=o['date']<=q: cur=i; break
        elif o['kind']=='trough' and cur is not None and cur not in res:
            d=o['date']
            if until is not None and o['published']>=until: continue
            if since is not None and o['published']<since: continue
            err=(d.year-TR[cur].year)*12+d.month-TR[cur].month; lag=(o['published']-me(TR[cur])).days
            res[cur]=(lag,err)
            if err<-6: early.append(cur)
    return res,early
GK=[2.,3.,4.,5.,6.,8.]; GJ=[3.,4.,5.,6.,8.,10.]; GH=[5.,6.,8.,10.,12.,15.]
def pick(cands,k):
    until=PK[k]-pd.DateOffset(months=6); prior=[i for i in range(k)]
    best=None
    for jx,c in enumerate(cands):
        res,early=score_troughs(turns(*c),until=until)
        closed=[i for i in prior if i in res and abs(res[i][1])<=6]; lags=[res[i][0] for i in closed]
        if MODE=='fast': key=(-len(closed),len(early),float(np.median(lags)) if lags else 1e9)
        else: key=(len(early),-len(closed),-jx)
        if best is None or key<best[0]: best=(key,c)
    return best[1]
print(f"CAUSAL REPLAY OF THE TROUGH DROPS, criterion = {MODE}")
print(f"  {'recession':10} {'K':>4} {'J':>4} {'H':>4}   {'closed':>6} {'lag d':>6} {'err':>4}")
tally=[]
for k in range(3,len(PK)):
    kk=pick([(kk,5.,8.) for kk in GK],k)[0]; jj=pick([(kk,jj,8.) for jj in GJ],k)[1]; hh=pick([(kk,jj,hh) for hh in GH],k)[2]
    res,early=score_troughs(turns(kk,jj,hh)); r=res.get(k)
    ok=r is not None and abs(r[1])<=6
    tally.append((k,r,ok)); print(f"  {PK[k]:%Y-%m}     {kk:4.0f} {jj:4.0f} {hh:4.0f}   {'yes' if ok else 'NO':>6} {'' if r is None else r[0]:>6} {'' if r is None else r[1]:>+4}")
closed=[r for _,r,ok in tally if ok]; print(f"\n  causal: {len(closed)}/{len(tally)} troughs closed within six months, median lag {np.median([r[0] for r in closed]):.0f} d, worst {max(r[0] for r in closed)}, dates exact {sum(1 for r in closed if r[1]==0)}, within one {sum(1 for r in closed if abs(r[1])<=1)}")
res,early=score_troughs(turns(4.,5.,8.)); cl=[res[i] for i in res if abs(res[i][1])<=6]
print(f"  frozen (4,5,8) in-sample: {len(cl)}/12 closed, median {np.median([r[0] for r in cl]):.0f} d, worst {max(r[0] for r in cl)}, exact {sum(1 for r in cl if r[1]==0)}, within one {sum(1 for r in cl if abs(r[1])<=1)}, early closes {early}")
