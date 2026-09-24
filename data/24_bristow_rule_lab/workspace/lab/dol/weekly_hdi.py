"""The same peak detector on the weekly file, 1986 on.

The weekly ETA 539 panel is four times as frequent as the monthly one and is published the
Thursday after the week it covers, so if the same object works there the publication lag
falls by about a month.  The question is whether the per-channel turning point survives
weekly noise.  Amplitudes are in the same log points; the minimum phase is in WEEKS.
"""
import sys; sys.path.insert(0,'/home/claude')
import bristow_rule_v3 as B, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
IC=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_pooled.csv',index_col=0,parse_dates=True)
CC=pd.read_csv('/home/claude/lab/dol/US_state_cc_sa_pooled.csv',index_col=0,parse_dates=True)
PAN=pd.concat([IC.add_suffix(' IC'),CC.add_suffix(' CC')],axis=1)
PK=['1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
TT={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in PK}
S0=pd.Timestamp('1988-01-01')
def mo(t): return t.year*12+t.month
def lab(x): return f'{(x-1)//12:04d}-{((x-1)%12)+1:02d}'
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
def calls(D,idx,pmin,cyc,warm=104):
    d=D; n=len(d); on=d>=50.
    lastb=np.maximum.accumulate(np.where(d<50.,np.arange(n),0))
    out=[]; i=0; last=None; state=0; off=0
    while i<n:
        if state==0 and on[i] and i>=warm:
            pub=idx[i]+pd.Timedelta(days=5); pm=mo(pub)
            if last is None or pm-last>=cyc:
                j=lastb[i]; out.append((pm,mo(idx[j]))); last=pm; state=1; off=0
        elif state==1:
            off = off+1 if d[i]<50. else 0
            if off>=pmin: state=0
        i+=1
    return out
def score(c):
    hits={}; oth=0
    for p,dd in c:
        if p<mo(S0): continue
        k=min(TT,key=lambda x:abs(dd-TT[x]))
        if abs(p-TT[k])<=2 and abs(dd-TT[k])<=2 and k not in hits: hits[k]=(p-TT[k],dd-TT[k])
        else: oth+=1
    return hits,oth
X=(PAN*100.0).values; idx=PAN.index
best={}
for sm in (1,4,8,13):
    Y=(PAN.rolling(sm).mean()*100.0).values
    for amp in (20,25,30,35,40,45,50,55,60):
        for mph in (13,26,39,52,65,78):
            ph=phase(Y,float(amp),mph)
            D=(ph>0).sum(axis=1)/np.isfinite(Y).sum(axis=1)*100.0
            for pmin in (4,8,13,22,26):
                for cyc in (15,18,24):
                    h,o=score(calls(D,idx,pmin,cyc))
                    key=(len(h),o)
                    if key not in best: best[key]=(sm,amp,mph,pmin,cyc,{k:v for k,v in h.items()})
print('PEAKS on the weekly panel, 1988-2026 (six targets reachable)')
for k in sorted(best,key=lambda x:(-x[0],x[1]))[:8]:
    sm,amp,mph,pmin,cyc,h=best[k]
    print(f'  {k[0]}/6 hits, {k[1]:2d} other   sm={sm} amp={amp} mph={mph}w pmin={pmin}w cyc={cyc}m')
    for kk,vv in sorted(h.items()): print(f'        {kk}  lag {vv[0]:+d}  error {vv[1]:+d}')
