import os,sys,bisect,json,datetime as dt
import numpy as np
REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
sys.path.insert(0,REPO+"/method_source")
os.environ["NOWCAST_DISABLE"]="1";os.environ["INDEX_OUT"]=REPO+"/research/scratch_r52/x.json"
os.chdir(REPO+"/research/channel_structure_ch1/scratch/work")
import index_v1 as m
CHAN=m.CHANNELS;CH=list(CHAN.keys());MEMBERS=[]
for c in CH:MEMBERS+=CHAN[c][1]
DAYS=m.DAYS;T=m.T;RECS=m.RECS
def asof(zd,ks,d):
    i=bisect.bisect_right(ks,d)-1
    return zd[ks[i]] if i>=0 else None
def mu_cur(n,ks,v):
    b=[T[n][k] for k in ks if m.is_baseline(k)];mu=sum(b)/len(b);return mu,(sum((x-mu)**2 for x in b)/len(b))**.5
def mu_med(n,ks,v):
    md=float(np.median(v));return md,float(np.median(np.abs(v-md)))*1.4826
def rez(fn):
    Z={}
    for n in MEMBERS:
        ks=sorted(T[n]);v=np.array([T[n][k] for k in ks]);mu,sd=fn(n,ks,v)
        if sd==0 or np.isnan(sd):sd=1.0
        Z[n]=({k:(T[n][k]-mu)/sd for k in ks},ks,mu,sd)
    return Z
def line(Z,drop=None):
    W=np.array([CHAN[c][0] for c in CH])
    L=np.full(len(DAYS),np.nan)
    Xc={n:(Z[n][0],Z[n][1]) for n in MEMBERS}
    for i,d in enumerate(DAYS):
        cs=[]
        for ci,c in enumerate(CH):
            r=[]
            for x in CHAN[c][1]:
                if x==drop:continue
                v=asof(Xc[x][0],Xc[x][1],d)
                if v is not None:r.append(v)
            cs.append(np.mean(r) if r else np.nan)
        cs=np.array(cs);p=~np.isnan(cs)
        if p.any():L[i]=np.sum(W[p]*cs[p])/W[p].sum()
    return L
def sig(L,nm):
    exp=np.array([L[i] for i,d in enumerate(DAYS) if m.is_baseline(d) and not np.isnan(L[i])])
    mu,sd=exp.mean(),exp.std();a,b=RECS[nm]
    w=[L[i] for i,d in enumerate(DAYS) if a<=d<=b and not np.isnan(L[i])]
    return (max(w)-mu)/sd
Zc=rez(mu_cur);Zm=rez(mu_med)
base_cur82=sig(line(Zc),"1981-82");base_stat82=sig(line(Zm),"1981-82")
base_cur80=sig(line(Zc),"1980");base_stat80=sig(line(Zm),"1980")
print(f"baseline 1981-82: cur {base_cur82:.2f} stat {base_stat82:.2f} (flip: stat>cur = {base_stat82>base_cur82})")
# per-member: d_mu,d_sd and leave-one-out effect on stat 1981-82 sigma-severity
rows=[]
for n in MEMBERS:
    dmu=Zm[n][2]-Zc[n][2];dsd=Zm[n][3]-Zc[n][3]
    s82=sig(line(Zm,drop=n),"1981-82")
    rows.append((n,dmu,dsd,s82,s82-base_stat82))
rows.sort(key=lambda r:r[4])  # most negative = removing it most LOWERS 1981-82 => biggest driver up
print(f"{'member':14}{'d_mu':>9}{'d_sd':>9}{'stat82_woN':>12}{'effect':>9}")
for n,dmu,dsd,s,eff in rows:
    ch=[c for c in CH if n in CHAN[c][1]][0]
    print(f"{n:14}{dmu:9.3f}{dsd:9.3f}{s:12.2f}{eff:9.3f}  [{ch}]")
