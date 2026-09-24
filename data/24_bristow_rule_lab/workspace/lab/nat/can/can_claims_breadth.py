"""Canada's provincial claims file as the American state file's analogue: Statistics Canada
table 14-10-0005 (Employment Insurance / Unemployment Insurance claims received, by province,
monthly, unadjusted, from January 1943 — on disk since the Canadian panel work,
lab/acq/statcan/14100005).

The peak detector is the one the American monthly record uses (lab/dol/final_record.py):
each province's initial-and-renewal claims received, adjusted in real time (month-of-year
median factors from the seven years strictly before the year adjusted; log level), run
through the causal phase machine (a province is 'up' — claims rising, activity falling —
once its smoothed log claims have risen `amp` log points from their trough after at least
`mph` months in the phase), and the share of provinces 'up' is the historical diffusion
index; a peak is called when the index has stood at or above fifty per cent for `r` months
and is dated at the last month the index stood below fifty.  Scored against the C.D. Howe
Business Cycle Council's peaks, 1947 to 2020, and ECRI's.  The trough side is the tool's
level clause on national claims (the log level; level_trough_calls).

Publication: Statistics Canada releases the EI statistics for month T about seven to eight
weeks after T ends; 'within the month' is therefore not reachable from this file, and the
column reports the data month of the call instead — the lag a same-month source would give.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/dol')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
SRC='/home/claude/lab/acq/statcan/14100005/14100005.csv'
PROV=['Newfoundland and Labrador','Prince Edward Island','Nova Scotia','New Brunswick','Quebec','Ontario','Manitoba','Saskatchewan','Alberta','British Columbia']
COUNCIL_P=['1947-08','1951-04','1953-07','1957-03','1960-03','1974-10','1981-06','1990-03','2008-10','2020-02']
COUNCIL_T=['1948-03','1951-12','1954-07','1958-01','1961-03','1975-03','1982-10','1992-05','2009-05','2020-04']
ECRI_P=['1953-05','1956-10','1981-04','1990-03','2008-01','2019-12']; ECRI_T=['1954-06','1958-02','1982-11','1992-03','2009-07','2020-04']
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def ts(s): return pd.Timestamp(s+'-01')
def load():
    d=pd.read_csv(SRC,usecols=['REF_DATE','GEO','Type of claim','Claim detail','VALUE'])
    d=d[(d['Type of claim']=='Initial and renewal claims')&(d['Claim detail']=='Received')]
    d['t']=pd.to_datetime(d.REF_DATE,format='%Y-%m')
    P=d.pivot_table(index='t',columns='GEO',values='VALUE')
    return P
def sa_rt(s, win=7):
    x=np.log(s.clip(lower=1.0))*100.0; out=pd.Series(np.nan,index=x.index)
    for yr in sorted(set(x.index.year)):
        past=x[x.index.year<yr]
        if len(past)<24: out[x.index.year==yr]=x[x.index.year==yr]; continue
        tr=past.rolling(13,center=True,min_periods=7).mean().bfill().ffill(); r=past-tr
        hist=r[r.index.year>=yr-win]; f=hist.groupby(hist.index.month).median(); f=f-f.mean()
        for t in x.index[x.index.year==yr]: out[t]=x[t]-float(f.get(t.month,0.0))
    return out
def phase(X,amp,mph):
    T,N=X.shape; out=np.zeros((T,N),dtype=np.int8)
    # initial phase of each series from the sign of its first twelve-month change (the American
    # script starts every series 'up'; on a file that opens in an expansion that reads as a
    # contraction until each series has flipped once)
    x0=X[0]; x12=X[min(12,T-1)]
    st=np.where(np.isfinite(x0)&np.isfinite(x12)&(x12<x0),np.int8(-1),np.int8(1)).astype(np.int8)
    ext=np.where(np.isfinite(X[0]),X[0],0.0).copy(); since=np.zeros(N,dtype=np.int32)
    for t in range(T):
        x=X[t]; fin=np.isfinite(x); up=st==1
        np.copyto(ext,np.maximum(ext,x),where=fin&up); np.copyto(ext,np.minimum(ext,x),where=fin&~up)
        fd=fin&up&((ext-x)>=amp)&(since>=mph); fu=fin&~up&((x-ext)>=amp)&(since>=mph); fl=fd|fu
        st=np.where(fd,np.int8(-1),np.where(fu,np.int8(1),st)); ext=np.where(fl,x,ext); since=np.where(fl,0,since+1); out[t]=st
    return out
def hdi(SA,sm,amp,mph,warmup=12):
    X=SA.rolling(sm).mean().values
    ph=phase(X,amp,mph)
    # claims RISING = province in contraction: 'up' state (+1) means claims rising.  The machine
    # starts every province 'up', so the first `warmup` months of the index are not read.
    D=pd.Series((ph>0).sum(axis=1)/np.isfinite(X).sum(axis=1)*100.0,index=SA.index)
    return D.iloc[warmup:]
def peak_calls(D,r,pmin=5,cyc=15):
    d=D.values; idx=D.index; n=len(d); on=d>=50.
    if r>1: on=np.convolve(on.astype(int),np.ones(r,dtype=int),'full')[:n]==r
    lastb=np.maximum.accumulate(np.where(d<50.,np.arange(n),0))
    out=[]; state=0; off=0; last=None
    for i in range(n):
        if state==0 and on[i] and (last is None or md(idx[i],last)>=cyc):
            out.append((idx[i],idx[lastb[i]])); last=idx[i]; state=1; off=0
        elif state==1:
            off=off+1 if d[i]<50. else 0
            if off>=pmin: state=0
    return out
def score(calls,refs,tol=6):
    got={}; used=set()
    for i,ref in enumerate(refs):
        best=None
        for j,(pub,dt) in enumerate(calls):
            if j in used: continue
            e=md(dt,ref)
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(j,e)
        if best: got[i]=(calls[best[0]][0],calls[best[0]][1],best[1]); used.add(best[0])
    return got,[c for j,c in enumerate(calls) if j not in used]
if __name__=='__main__':
    P=load(); print('provinces on file:',[c for c in PROV if c in P.columns],'| span',P.index.min().strftime('%Y-%m'),'->',P.index.max().strftime('%Y-%m'))
    SA=pd.concat([sa_rt(P[c]).rename(c) for c in PROV if c in P.columns],axis=1)['1946-01':]
    NAT=sa_rt(P['Canada'])['1946-01':]/100.0     # log level, adjusted
    for label,RP,RT in (('the Council',COUNCIL_P,COUNCIL_T),('ECRI',ECRI_P,ECRI_T)):
        RP=[ts(x) for x in RP]; RT=[ts(x) for x in RT]
        print(f'\n=== PEAKS against {label}: provincial breadth (smooth, amp, min phase, run); hits / other / exact / within 1 / data-month lag <=1')
        rows=[]
        for sm,amp,mph,r in itertools.product((1,2,3),(5.,10.,15.,20.),(3,5),(1,2,3)):
            D=hdi(SA,sm,amp,mph); calls=peak_calls(D,r)
            got,other=score(calls,RP)
            e=[v[2] for v in got.values()]; lag=[md(v[0],RP[i]) for i,v in got.items()]
            rows.append((len(got),-len(other),sum(x==0 for x in e),sum(abs(x)<=1 for x in e),sum(l<=1 for l in lag),(sm,amp,mph,r),got,other))
        rows.sort(key=lambda r:(r[0],r[1],r[2],r[4]),reverse=True)
        for r in rows[:5]:
            print(f'  hits {r[0]}/{len(RP)} other {-r[1]} exact {r[2]} w1 {r[3]} lag<=1 {r[4]} | {r[5]}')
            print('     ',{RP[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'data '+v[0].strftime('%Y-%m')) for i,v in r[6].items()})
            if r[7]: print('      other:',[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in r[7]])
        z=[r for r in rows if r[1]==0]
        if z:
            z.sort(key=lambda r:(r[0],r[2],r[4]),reverse=True); r=z[0]
            print(f'  best with no other call: hits {r[0]}/{len(RP)} exact {r[2]} w1 {r[3]} lag<=1 {r[4]} | {r[5]}')
            print('     ',{RP[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'data '+v[0].strftime('%Y-%m')) for i,v in r[6].items()})
        print(f'\n=== TROUGHS against {label}: national claims, the tool\'s level clause (smooth, lookback, run, drop, arm)')
        rows=[]
        for sm,lb,run_,drop,gap in itertools.product((1,2,3),(24,36),(1,2,3),(1.,2.,4.),(10.,20.,30.,50.)):
            calls=B.level_trough_calls(NAT,smooth=sm,lookback=lb,run=run_,drop=drop,arm_gap=gap,rearm_gap=gap/4,min_phase=3,publication_lag=0)
            got,other=score(calls,RT)
            e=[v[2] for v in got.values()]; lag=[md(v[0],RT[i]) for i,v in got.items()]
            rows.append((len(got),-len(other),sum(x==0 for x in e),sum(abs(x)<=1 for x in e),sum(l<=1 for l in lag),(sm,lb,run_,drop,gap),got,other))
        rows.sort(key=lambda r:(r[0],r[1],r[2],r[4]),reverse=True)
        for r in rows[:4]:
            print(f'  hits {r[0]}/{len(RT)} other {-r[1]} exact {r[2]} w1 {r[3]} lag<=1 {r[4]} | {r[5]}')
            print('     ',{RT[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'data '+v[0].strftime('%Y-%m')) for i,v in r[6].items()})
            if r[7]: print('      other:',[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in r[7]])
        z=[r for r in rows if r[1]==0]
        if z:
            z.sort(key=lambda r:(r[0],r[2],r[4]),reverse=True); r=z[0]
            print(f'  best with no other call: hits {r[0]}/{len(RT)} exact {r[2]} w1 {r[3]} lag<=1 {r[4]} | {r[5]}')
            print('     ',{RT[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'data '+v[0].strftime('%Y-%m')) for i,v in r[6].items()})
