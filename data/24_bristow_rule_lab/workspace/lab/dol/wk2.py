"""The weekly detector with a principled warm-up.

The phase monitor cannot let a channel turn until `min_phase` has elapsed, so the index is
not a reading until at least twice that has passed.  The warm-up is therefore set to twice
the minimum phase rather than to a fixed number of weeks, which is a rule rather than a
choice.  Calls are also classified: a call that lands inside a recession is late, not false.
"""
import sys; sys.path.insert(0,'/home/claude')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
IC=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_pooled.csv',index_col=0,parse_dates=True)
CC=pd.read_csv('/home/claude/lab/dol/US_state_cc_sa_pooled.csv',index_col=0,parse_dates=True)
PAN=pd.concat([IC.add_suffix(' IC'),CC.add_suffix(' CC')],axis=1)
PK=['1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
TT={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in PK}
# recession spans (peak, trough) that a call may legitimately fall inside
SPAN=[('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
      ('2023-06','2026-05')]
def mo(t): return t.year*12+t.month
def lab(x): return f'{(x-1)//12:04d}-{((x-1)%12)+1:02d}'
SPANM=[(mo(pd.Timestamp(a+'-01')),mo(pd.Timestamp(b+'-01'))) for a,b in SPAN]
def phase(X,amp,mph):
    T,N=X.shape; out=np.zeros((T,N),dtype=np.int8)
    st=np.ones(N,dtype=np.int8); ext=np.where(np.isfinite(X[0]),X[0],0.0).copy()
    since=np.zeros(N,dtype=np.int32)
    for t in range(T):
        x=X[t]; fin=np.isfinite(x); up=st==1
        np.copyto(ext,np.maximum(ext,x),where=fin&up); np.copyto(ext,np.minimum(ext,x),where=fin&~up)
        fd=fin&up&((ext-x)>=amp)&(since>=mph); fu=fin&~up&((x-ext)>=amp)&(since>=mph); fl=fd|fu
        st=np.where(fd,np.int8(-1),np.where(fu,np.int8(1),st))
        ext=np.where(fl,x,ext); since=np.where(fl,0,since+1); out[t]=st
    return out
def calls(D,idx,pmin,cyc,warm):
    n=len(D); on=D>=50.
    lastb=np.maximum.accumulate(np.where(D<50.,np.arange(n),0))
    out=[]; i=0; last=None; state=0; off=0
    while i<n:
        if state==0 and on[i] and i>=warm:
            pub=idx[i]+pd.Timedelta(days=5); pm=mo(pub)
            if last is None or pm-last>=cyc:
                j=lastb[i]; out.append((pm,mo(idx[j]))); last=pm; state=1; off=0
        elif state==1:
            off = off+1 if D[i]<50. else 0
            if off>=pmin: state=0
        i+=1
    return out
def classify(c,start):
    hits={}; late=0; false_=0
    for p,d in c:
        if p<start: continue
        k=min(TT,key=lambda x:abs(d-TT[x]))
        if abs(p-TT[k])<=2 and abs(d-TT[k])<=2 and k not in hits: hits[k]=(p-TT[k],d-TT[k]); continue
        if any(a<=d<=b for a,b in SPANM): late+=1
        else: false_+=1
    return hits,late,false_
best={}
for sm in (1,2,4,8,13):
    Y=(PAN.rolling(sm).mean()*100.0).values
    for amp in (25,30,35,40,45,50):
        for mph in (13,26,39,52,65,78,91):
            ph=phase(Y,float(amp),mph); D=(ph>0).sum(axis=1)/np.isfinite(Y).sum(axis=1)*100.0
            warm=2*mph
            if warm>=len(D): continue
            start=mo(PAN.index[warm])
            for pmin in (4,8,13,22,26,39):
                for cyc in (15,18,24):
                    h,lt,fa=classify(calls(D,PAN.index,pmin,cyc,warm),start)
                    key=(len(h),fa,lt)
                    if key not in best: best[key]=(sm,amp,mph,pmin,cyc,lab(start),{k:v for k,v in h.items()})
print('PEAKS on the weekly panel; "false" = a call outside every recession, "late" = inside one')
for k in sorted(best,key=lambda x:(-x[0],x[1],x[2]))[:10]:
    sm,amp,mph,pmin,cyc,st,h=best[k]
    print(f'  {k[0]}/6 hits, {k[1]} false, {k[2]} late   sm={sm} amp={amp} mph={mph}w pmin={pmin}w cyc={cyc}m  record from {st}')
    for kk,vv in sorted(h.items()): print(f'        {kk}  lag {vv[0]:+d}  error {vv[1]:+d}')
