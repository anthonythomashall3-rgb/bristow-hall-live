"""Onset (peak) calls from the channels themselves: how many channels must have turned, and a
threshold that moves with each channel's own history, instead of waiting for the median
drawdown to reach two per cent.

Anthony's two ideas of 2 September 2026, tested as asked: (1) "only a certain number of
channels have to stop rising" - a k-of-n clause on the channels' own drawdowns; (2) "a moving
threshold based on something, because we need it to work forever" - each channel judged
against its own trailing distribution, so the clause is self-normalising and never needs a
level a later decade would make stale.

Panels: the six monthly chronologies' level panels as shipped (bench.PANELS 'ch'), every
channel; each reading treated as in hand `LAG` months after its month (1 in the United
States, 2 elsewhere - the OECD publication lag; memo section 8c found the first prints date
like the final vintage).  Every clause is causal: a call in month t uses readings in hand by
t only.  One call per contraction: after a call the clause is silent until its own condition
has been off for `REARM` months.

Clauses (each channel's log level x100, smoothed `sm` months):
  median   the shipped statistic: composite_deviation (median drawdown) >= 2.0
  kofn     drawdown from the trailing 12-month max >= band on at least k channels, `c` months
  quant    the `h`-month change below its own trailing 120-month p-th percentile on k channels
  vol      drawdown >= mult x the channel's own trailing 60-month volatility of `h`-month
           changes on k channels
  cross    level below its trailing 12-month mean by >= margin on k channels
  zmed     the median across channels of the `h`-month change, standardised on each channel's
           own trailing 120 months, at or below -z0 for `c` months (a self-normalising D)
Scoring against the committee's peaks: a call whose data month lies in [peak-3, min(peak+18,
trough+3)] is that peak's call (the earliest such call); a later call inside the same
contraction is a repeat and is not counted against the clause; a call in an expansion is an
other call.  The lag is call month (data month + LAG) minus peak month; 'lag<=1' is the
reading for the peak month itself, first in hand.  The whole grid is printed pooled and per
chronology beside the shipped clause; then the plan's leave-one-chronology-out selection
(among clauses with no more other calls than the shipped clause on the other five: most hits, then fewest other calls, then most within six months) is
applied to the sixth; then the shipped clause and the clauses the folds chose are shown on
the held-out chronologies (Germany on the Council's four channels, Mexico on the panel with
the vehicle channel) that entered no choice.
"""
import sys, itertools, warnings, collections; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, bench
from bench import pro, ts, md
LAG={'United States':1,'United States (interwar)':1}
REARM=6
MONTHLY=['United States','United States (interwar)','Canada','Japan','Korea','Brazil']
def panel(cn):
    out=[]
    for nm,p,kind in bench.PANELS[cn]['ch']:
        try: s=pro(p,kind)
        except Exception: continue
        s=s[s>0].dropna()
        if len(s)>=36: out.append((nm,s))
    return out
def peaks(cn):
    """[(peak month, trough month)] of the committee's contractions."""
    out=[]
    for e in bench.PANELS[cn]['chrono']:
        pk,tr,f=bench.ep3(e,'M')
        if f=='M': out.append((ts(pk),ts(tr)))
        else: out.append((bench.q2m(pk),bench.q2m(tr)))
    return out
def logs(chs, sm):
    X=pd.concat([(np.log(s)*100.0).rename(nm) for nm,s in chs],axis=1).sort_index()
    return X.rolling(sm).mean() if sm>1 else X
def count_calls(cond, lag, rearm=REARM):
    """cond: boolean Series by data month.  Returns [(call month, data month)] with one call per
    episode: silent after a call until cond has been False `rearm` consecutive months."""
    out=[]; state='quiet'; off=0
    for t,v in cond.items():
        if state=='quiet':
            if bool(v): out.append((t+pd.DateOffset(months=lag),t)); state='called'; off=0
        else:
            off=off+1 if not bool(v) else 0
            if off>=rearm: state='quiet'
    return out
def clause(X, kind, **kw):
    n_ok=X.notna().sum(axis=1)
    if kind=='median':
        d=X.rolling(12,min_periods=6).max()-X
        return (d.median(axis=1)>=kw['band']) & (n_ok>=1)
    if kind=='kofn':
        d=X.rolling(12,min_periods=6).max()-X
        hit=(d>=kw['band']).sum(axis=1)
        k=kw['k']; need=(np.ceil(n_ok*k) if isinstance(k,float) else pd.Series(k,index=X.index)).clip(lower=1)
        c=(hit>=need) & (n_ok>=1)
        return c.rolling(kw.get('c',1)).sum()>=kw.get('c',1)
    if kind=='quant':
        g=X.diff(kw['h']); q=g.rolling(120,min_periods=60).quantile(kw['p']/100.0).shift(1)
        hit=(g<q).sum(axis=1)
        k=kw['k']; need=(np.ceil(n_ok*k) if isinstance(k,float) else pd.Series(k,index=X.index)).clip(lower=1)
        c=(hit>=need) & (n_ok>=1)
        return c.rolling(kw.get('c',1)).sum()>=kw.get('c',1)
    if kind=='vol':
        d=X.rolling(12,min_periods=6).max()-X
        sig=X.diff(kw['h']).rolling(60,min_periods=36).std().shift(1)
        hit=(d>=kw['mult']*sig).sum(axis=1)
        k=kw['k']; need=(np.ceil(n_ok*k) if isinstance(k,float) else pd.Series(k,index=X.index)).clip(lower=1)
        c=(hit>=need) & (n_ok>=1)
        return c.rolling(kw.get('c',1)).sum()>=kw.get('c',1)
    if kind=='zmed':
        g=X.diff(kw['h']); z=(g-g.rolling(120,min_periods=60).mean().shift(1))/g.rolling(120,min_periods=60).std().shift(1)
        c=(z.median(axis=1)<=-kw['z0']) & (n_ok>=1)
        return c.rolling(kw.get('c',1)).sum()>=kw.get('c',1)
    if kind=='cross':
        m=X.rolling(12,min_periods=6).mean()
        hit=((m-X)>=kw['margin']).sum(axis=1)
        k=kw['k']; need=(np.ceil(n_ok*k) if isinstance(k,float) else pd.Series(k,index=X.index)).clip(lower=1)
        c=(hit>=need) & (n_ok>=1)
        return c.rolling(kw.get('c',1)).sum()>=kw.get('c',1)
    raise ValueError(kind)
def score(calls, P, lo=-3, hi=18, after=3):
    """P: [(peak, trough)].  A peak's call is the earliest call whose data month lies in
    [peak-3, min(peak+18, trough+3)]; any later call with a data month inside [peak-3, trough+3]
    is a repeat inside the same contraction; every other call is an other call (an expansion)."""
    got={}; used=set(); repeat=[]
    for i,(pk,tr) in enumerate(P):
        top=min(md(tr,pk)+after,hi)
        cands=[(j,c) for j,c in enumerate(calls) if j not in used and lo<=md(c[1],pk)<=top]
        if cands:
            j,c=min(cands,key=lambda x:x[1][0]); got[i]=c; used.add(j)
    for j,c in enumerate(calls):
        if j in used: continue
        if any(lo<=md(c[1],pk)<=md(tr,pk)+after for pk,tr in P): repeat.append(c); used.add(j)
    other=[c for j,c in enumerate(calls) if j not in used]
    return got,other,repeat
def tally(got,other,P,start):
    Pr=[p for p in P if p[0]>=start]
    lags=[md(got[i][0],p[0]) for i,p in enumerate(P) if i in got]
    return dict(n=len(Pr),hits=sum(1 for i,p in enumerate(P) if i in got and p[0]>=start),other=len(other),
                inMonth=sum(l<=1 for l in lags),w3=sum(l<=3 for l in lags),w6=sum(l<=6 for l in lags),
                med=float(np.median(lags)) if lags else float('nan'),lags=lags)
GRID=[('median',dict(band=2.0))]
for band,k,c in itertools.product((1.0,2.0,3.0,4.0,5.0),(1,2,3,4,0.5,1.0),(1,2,3)): GRID.append(('kofn',dict(band=band,k=k,c=c)))
for h,p,k,c in itertools.product((3,6),(5,10,20),(1,2,0.5),(1,2)): GRID.append(('quant',dict(h=h,p=p,k=k,c=c)))
for h,mult,k,c in itertools.product((3,),(1.0,2.0,3.0),(1,2,0.5),(1,2)): GRID.append(('vol',dict(h=h,mult=mult,k=k,c=c)))
for margin,k,c in itertools.product((0.0,0.5,1.0),(1,2,0.5),(1,2)): GRID.append(('cross',dict(margin=margin,k=k,c=c)))
for h,z0,c in itertools.product((3,6),(0.5,1.0,1.5,2.0),(1,2,3)): GRID.append(('zmed',dict(h=h,z0=z0,c=c)))
def label(kind,kw): return kind+' '+' '.join(f'{a}={b}' for a,b in kw.items())
if __name__=='__main__':
    sms=(3,1)
    data={cn:(panel(cn),peaks(cn)) for cn in MONTHLY}
    for cn,(chs,P) in data.items(): print(cn,len(chs),'channels',[nm for nm,s in chs],len(P),'peaks')
    pooled=collections.defaultdict(lambda: dict(n=0,hits=0,other=0,inMonth=0,w3=0,w6=0,lags=[]))
    per={}
    for sm in sms:
        for kind,kw in GRID:
            key=(sm,label(kind,kw))
            for cn,(chs,P) in data.items():
                X=logs(chs,sm); cond=clause(X,kind,**kw).dropna()
                start=cond.index[cond.values.astype(bool)].min() if cond.any() else cond.index.min()
                first=X.dropna(how='all').index.min()+pd.DateOffset(months=12)   # scored from the first month the clause could fire
                calls=[c for c in count_calls(cond,LAG.get(cn,2)) if c[1]>=first]
                Pr=[p for p in P if p[0]>=first]
                got,other,rep=score(calls,Pr)
                t=tally(got,other,Pr,first); per[(key,cn)]=t
                pooled[key]['n']+=t['n']; pooled[key]['hits']+=t['hits']; pooled[key]['other']+=t['other']
                pooled[key]['inMonth']+=t['inMonth']; pooled[key]['w3']+=t['w3']; pooled[key]['w6']+=t['w6']; pooled[key]['lags']+=t['lags']
    print('\n=== pooled over the six monthly chronologies (peaks reachable by the panel): hits / other calls / lag<=1 / lag<=3 / lag<=6 / median lag')
    rows=[]
    for key,v in pooled.items():
        rows.append((v['hits'],-v['other'],v['w3'],v['inMonth'],key,v))
    rows.sort(reverse=True)
    for hits,mo,w3,im,key,v in rows:
        sm,lab=key
        print(f"  sm={sm} {lab:38s} hits {v['hits']:2d}/{v['n']} other {v['other']:3d} lag<=1 {v['inMonth']:2d} <=3 {v['w3']:2d} <=6 {v['w6']:2d} median {np.median(v['lags']) if v['lags'] else float('nan'):4.1f}")
    keys=list(pooled)
    print('\n=== leave one chronology out: chosen on the other five among clauses with no more other calls than the shipped clause there, by hits, then fewest other calls, then most within six months')
    oos=dict(n=0,hits=0,other=0,inMonth=0,w3=0,w6=0,lags=[]); ship=dict(n=0,hits=0,other=0,inMonth=0,w3=0,w6=0,lags=[]); picks=collections.Counter()
    for held in MONTHLY:
        others=[c for c in MONTHLY if c!=held]
        cap=sum(per[((3,'median band=2.0'),c)]['other'] for c in others)   # the shipped clause's other calls on the five: a ceiling, not a target
        def kf(key):
            h=sum(per[(key,c)]['hits'] for c in others); o=sum(per[(key,c)]['other'] for c in others); w=sum(per[(key,c)]['w6'] for c in others)
            return (o<=cap,h,-o,w)
        best=max(keys,key=kf); picks[best]+=1
        t=per[(best,held)]; s=per[((3,'median band=2.0'),held)]
        for acc,src_ in ((oos,t),(ship,s)):
            for f in ('n','hits','other','inMonth','w3','w6'): acc[f]+=src_[f]
            acc['lags']+=src_['lags']
        print(f"  held out {held:26s} picks sm={best[0]} {best[1]:34s} -> hits {t['hits']}/{t['n']} other {t['other']:2d} lag<=3 {t['w3']} <=6 {t['w6']} lags {t['lags']}   (shipped: {s['hits']}/{s['n']} other {s['other']} lag<=3 {s['w3']} <=6 {s['w6']})")
    print(f"  out of sample, six: hits {oos['hits']}/{oos['n']} other {oos['other']} lag<=1 {oos['inMonth']} <=3 {oos['w3']} <=6 {oos['w6']} median {np.median(oos['lags']):.1f}")
    print(f"  shipped clause     : hits {ship['hits']}/{ship['n']} other {ship['other']} lag<=1 {ship['inMonth']} <=3 {ship['w3']} <=6 {ship['w6']} median {np.median(ship['lags']):.1f}")
    print('  picks:',dict(picks))
    # held out: Germany on the Council's four channels, Mexico on the panel with the vehicle channel
    from bench import load
    NAT='/home/claude/lab/nat/deu'; KEI='/home/claude/lab/kei'
    DE=[('1966-03','1967-05'),('1974-01','1975-07'),('1980-01','1982-11'),('1992-02','1993-07'),('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')]
    MX=[('1985-09','1986-12'),('1994-11','1995-05'),('2000-09','2002-01'),('2008-06','2009-05'),('2019-05','2020-05')]
    HELD={'Germany (Council, four channels)':([('industrial production',load(f'{KEI}/DEU_PRVM_BTE.csv')),('retail volume',load(f'{KEI}/DEU_TOVM_G47.csv')),('real orders received',load(f'{NAT}/DEU_orders_real_sa.csv')),('unemployment rate',100.0-load(f'{NAT}/DEU_unemployment_rate_sa_spliced.csv'))],[(ts(a),ts(b)) for a,b in DE]),
          'Mexico (panel with vehicles)':([('industrial production',load(f'{KEI}/MEX_PRVM_BTE.csv')),('construction production',load(f'{KEI}/MEX_PRVM_F.csv')),('exports',load(f'{KEI}/MEX_EX__T.csv')),('imports',load(f'{KEI}/MEX_IM__T.csv')),('retail volume',load(f'{KEI}/MEX_TOVM_G47.csv')),('unemployment',load(f'{KEI}/MEX_UNEMP__T.csv')),('IGAE',load('/home/claude/lab/mex/MEX_igae_sa.csv')),('vehicle production',load('/home/claude/lab/mex/MEX_vehicles_sa.csv'))],[(ts(a),ts(b)) for a,b in MX])}
    print('\n=== held out (no choice made on these): the shipped clause and every clause a fold chose')
    show=[(3,'median band=2.0')]+[k for k in picks if k!=(3,'median band=2.0')]
    for hn,(chs,P) in HELD.items():
        chs=[(nm,s[s>0].dropna()) for nm,s in chs]
        print(f'  {hn}: {[nm for nm,s in chs]}')
        for key in show:
            sm=key[0]; kind=key[1].split()[0]; kw={a:(float(b) if "." in b else int(b)) for a,b in (x.split("=") for x in key[1].split()[1:])}
            X=logs(chs,sm); cond=clause(X,kind,**kw).dropna()
            first=X.dropna(how='all').index.min()+pd.DateOffset(months=12)
            calls=[c for c in count_calls(cond,2) if c[1]>=first]
            Pr=[p for p in P if p[0]>=first]; got,other,rep=score(calls,Pr); t=tally(got,other,Pr,first)
            print(f"    sm={sm} {key[1]:38s} hits {t['hits']}/{t['n']} other {t['other']:2d} lag<=1 {t['inMonth']} <=3 {t['w3']} <=6 {t['w6']} lags {t['lags']}  other: {[c[1].strftime('%Y-%m') for c in other]}")
    print('\n=== per chronology, the shipped clause and the best k-of-n / moving-threshold clauses by hits then fewest other calls')
    for cn in MONTHLY:
        print(f'\n  {cn}')
        cand=[(per[(key,cn)]['hits'],-per[(key,cn)]['other'],per[(key,cn)]['w3'],key) for key in pooled]
        cand.sort(reverse=True)
        shown=[k for k in pooled if k[1].startswith('median')]+[k for _,_,_,k in cand[:6]]
        for key in shown:
            t=per[(key,cn)]
            print(f"    sm={key[0]} {key[1]:38s} hits {t['hits']}/{t['n']} other {t['other']:2d} lag<=1 {t['inMonth']} <=3 {t['w3']} <=6 {t['w6']} lags {t['lags']}")
