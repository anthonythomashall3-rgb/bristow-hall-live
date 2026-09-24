"""Peak re-entry: can a second call inside one episode be had at zero false-call cost?

The shipped machine re-arms only when breadth falls back below a low line.  1981-07 and
Paper 1's 2024-03 are second peaks inside episodes where breadth never went back down, so
they cannot be emitted.  This tries a re-entry clause that is itself a fresh-deterioration
test: after a call, the detector re-arms once breadth has retreated `back` points from its
own post-call maximum, and can then fire again only on a NEW HIGH - breadth exceeding that
post-call maximum by `up` points.  A second wave has to be broader than the first.
"""
import sys; sys.path.insert(0,'/home/claude')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
M_SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def breadth(P,sm,L,gap):
    K=P.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
PK={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER','1990-07':'NBER','2001-03':'NBER',
    '2007-12':'NBER','2020-02':'NBER','2023-06':'Paper1','2024-03':'Paper1'}

def peaks2(Bd,thb,reb,r,mp,line,back,up):
    """Shipped machine plus the re-entry clause.  back=None or up=None disables it."""
    b=Bd.values; idx=Bd.index; out=[]; state='armed'; off=0
    bmax=-1e9; bmin=1e9; ref=-1e9
    for i in range(r,len(b)):
        on=bool(np.all(b[i-r+1:i+1]>=thb))
        if state=='called':
            # the shipped low-line route back to armed
            off = off+1 if b[i]<reb else 0
            if off>=mp: state='armed'; off=0; ref=-1e9; continue
            # the re-entry route: retreat from the post-call maximum
            if b[i]>bmax: bmax=b[i]; bmin=b[i]
            if b[i]<bmin: bmin=b[i]
            if back is not None and (bmax-bmin)>=back:
                state='rearmed'; ref=bmax; off=0
            continue
        if state=='rearmed':
            if b[i]<reb:
                off+=1
                if off>=mp: state='armed'; off=0; ref=-1e9
            else: off=0
            if on and b[i]>=ref+up:
                j=i
                while j>0 and b[j]>=line: j-=1
                out.append((idx[i]+pd.DateOffset(months=1),mo(idx[j])))
                state='called'; off=0; bmax=b[i]; bmin=b[i]
            continue
        if on:
            j=i
            while j>0 and b[j]>=line: j-=1
            out.append((idx[i]+pd.DateOffset(months=1),mo(idx[j])))
            state='called'; off=0; bmax=b[i]; bmin=b[i]
    return out

def score(calls):
    hits={}; other=0
    for pub,dt in sorted(calls):
        if pub<pd.Timestamp('1973-01-01'): continue
        near=min(PK,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
        lag=md(mo(pub),pd.Timestamp(near+'-01')); err=md(dt,pd.Timestamp(near+'-01'))
        if abs(lag)<=2 and abs(err)<=2 and near not in hits: hits[near]=(lag,err)
        else: other+=1
    return hits,other

BD=breadth(M_SA,2,36,25.)
base,ob=score(peaks2(BD,65.,30.,1,2,60.,None,None))
print(f'shipped: {len(base)}/9 hits, {ob} other  {sorted(base)}')
print()
best=[]
for back in [5,8,10,12,15,18,20,25,30]:
    for up in [0,2,3,5,8,10,12,15,20]:
        h,o=score(peaks2(BD,65.,30.,1,2,60.,float(back),float(up)))
        best.append((len(h),-o,back,up,sorted(h)))
best.sort(reverse=True)
for n,no,back,up,h in best[:15]:
    print(f'  back={back:3d} up={up:3d}   {n}/9 hits  {-no} other   {h}')
