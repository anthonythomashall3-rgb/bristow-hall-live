"""ESRI's clause at the other end, on the same index.

The Institute states both clauses on one index: "the last month when the historical
diffusion index compiled from a selected series of coincident indexes stays below the
50-percent line corresponds to the cyclical trough; the last month when this index stays
above the 50-percent line corresponds to the cyclical peak."  The index here counts the
share DETERIORATING, so the two readings swap: the peak is the last month below the line
and the trough the last month above it.  The peak clause is already shipped; this asks
what the same index says at the trough.
"""
import sys; sys.path.insert(0,'/home/claude')
import bristow_rule_v3 as B, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
TR={'1975-03':'NBER','1980-07':'NBER','1982-11':'NBER','1991-03':'NBER','2001-11':'NBER',
    '2009-06':'NBER','2020-04':'NBER','2024-08':'Paper 1','2026-05':'Paper 1'}
S0=pd.Timestamp('1973-01-01').year*12+1
def lab(m): return f'{(m-1)//12:04d}-{((m-1)%12)+1:02d}'
def trough_calls(D,line=50.,phase_min=5,cycle_min=15,warmup=24,pub=1):
    d=D.values; idx=D.index; n=len(d)
    below=d<line
    lasta=np.maximum.accumulate(np.where(d>=line,np.arange(n),0))
    out=[]; i=0; last=None; state=0; off=0; run=0
    while i<n:
        run = run+1 if below[i] else 0
        if state==0 and run>=phase_min and i>=warmup:
            p=idx[i]+pd.DateOffset(months=pub); pm=p.year*12+p.month
            if last is None or pm-last>=cycle_min:
                j=lasta[i]; out.append((pm,idx[j].year*12+idx[j].month)); last=pm; state=1; off=0
        elif state==1:
            off = off+1 if d[i]>=line else 0
            if off>=phase_min: state=0
        i+=1
    return out
def report(pairs,T,title):
    TT={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in T}
    print(f'--- {title}')
    hits={}; other=0
    for pub,dt in sorted(pairs):
        if pub<S0: continue
        near=min(TT,key=lambda k: abs(dt-TT[k])); lag=pub-TT[near]; err=dt-TT[near]
        ok=abs(lag)<=2 and abs(err)<=2 and near not in hits
        if ok: hits[near]=(lag,err)
        else: other+=1
        print(f'   {"HIT " if ok else "    "} published {lab(pub)}  dated {lab(dt)}   nearest {near} '
              f'({T[near]})  lag {lag:+3d}  error {err:+3d}')
    print(f'   => {len(hits)} of {len(T)};  {other} other calls;  never: {[k for k in T if k not in hits]}')
    return len(hits),other
cols=[c for c in PAN.columns if c.endswith('| initial claims') or c.endswith('| continued weeks claimed')]
D=B.claims_diffusion(PAN[cols],48.,13)
report(trough_calls(D),TR,'TROUGHS, ESRI clause on the shipped claims diffusion index')
print()
best={}
allc=['initial claims','continued weeks claimed','weeks compensated','first payments']
for chs in [('initial claims','continued weeks claimed'),('initial claims',),
            ('continued weeks claimed',),tuple(allc)]:
    cs=[c for c in PAN.columns if any(c.endswith('| '+x) for x in chs)]
    for amp in range(24,61,2):
        for mph in (8,10,12,13,14,16,18):
            Dx=B.claims_diffusion(PAN[cs],float(amp),mph)
            for pmin in (3,4,5,6,8):
                for cyc in (15,18,24):
                    TT={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in TR}
                    hits=set(); oth=0
                    for pub,dt in sorted(trough_calls(Dx,50.,pmin,cyc)):
                        if pub<S0: continue
                        near=min(TT,key=lambda k: abs(dt-TT[k]))
                        if abs(pub-TT[near])<=2 and abs(dt-TT[near])<=2 and near not in hits: hits.add(near)
                        else: oth+=1
                    key=(len(hits),oth)
                    if key not in best: best[key]=(chs,amp,mph,pmin,cyc,tuple(sorted(hits)))
print('TROUGH sweep on the diffusion index')
for k in sorted(best,key=lambda x:(-x[0],x[1]))[:10]:
    chs,amp,mph,pmin,cyc,h=best[k]
    print(f'  {k[0]}/9 other {k[1]:2d}  chs={"+".join(c[:4] for c in chs)} amp={amp} mph={mph} pmin={pmin} cyc={cyc}')
    print(f'        {list(h)}')
