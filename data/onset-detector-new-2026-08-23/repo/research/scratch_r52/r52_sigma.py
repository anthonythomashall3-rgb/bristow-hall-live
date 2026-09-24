import os,sys,bisect,json,datetime as dt
import numpy as np
REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
sys.path.insert(0,REPO+"/method_source")
os.environ["NOWCAST_DISABLE"]="1"; os.environ["INDEX_OUT"]=REPO+"/research/scratch_r52/x.json"
os.chdir(REPO+"/research/channel_structure_ch1/scratch/work")
import index_v1 as m
CHAN=m.CHANNELS;CH=list(CHAN.keys());MEMBERS=[]
for c in CH:MEMBERS+=CHAN[c][1]
DAYS=m.DAYS;T=m.T;RECS=m.RECS;W=np.array([CHAN[c][0] for c in CH])
def asof(zd,ks,d):
    i=bisect.bisect_right(ks,d)-1
    return zd[ks[i]] if i>=0 else None
def mu_cur(n,ks,v):
    b=[T[n][k] for k in ks if m.is_baseline(k)];mu=sum(b)/len(b);sd=(sum((x-mu)**2 for x in b)/len(b))**.5;return mu,sd
def mu_med(n,ks,v):
    md=float(np.median(v));return md,float(np.median(np.abs(v-md)))*1.4826
def mu_mean(n,ks,v): return float(v.mean()),float(v.std())
def rez(fn):
    Z={}
    for n in MEMBERS:
        ks=sorted(T[n]);v=np.array([T[n][k] for k in ks]);mu,sd=fn(n,ks,v)
        if sd==0 or np.isnan(sd):sd=1.0
        Z[n]=({k:(T[n][k]-mu)/sd for k in ks},ks,mu,sd)
    return Z
def line(Z):
    X=np.full((len(DAYS),len(MEMBERS)),np.nan)
    for j,n in enumerate(MEMBERS):
        zd,ks=Z[n][0],Z[n][1]
        for i,d in enumerate(DAYS):
            val=asof(zd,ks,d)
            if val is not None:X[i,j]=val
    L=np.full(len(DAYS),np.nan)
    for i in range(len(DAYS)):
        cs=[]
        for ci,c in enumerate(CH):
            r=[X[i,MEMBERS.index(x)] for x in CHAN[c][1]]
            r=[x for x in r if not np.isnan(x)]
            cs.append(np.mean(r) if r else np.nan)
        cs=np.array(cs);p=~np.isnan(cs)
        if p.any():L[i]=np.sum(W[p]*cs[p])/W[p].sum()
    return L
Lc=line(rez(mu_cur));Lm=line(rez(mu_med));Le=line(rez(mu_mean))
def sigsev(L):
    exp=np.array([L[i] for i,d in enumerate(DAYS) if m.is_baseline(d) and not np.isnan(L[i])])
    mu=exp.mean();sd=exp.std()
    o={}
    for nm,(a,b) in RECS.items():
        w=[L[i] for i,d in enumerate(DAYS) if a<=d<=b and not np.isnan(L[i])]
        o[nm]=round((max(w)-mu)/sd,2) if w else None
    return o,round(mu,4),round(sd,4)
sc,muc,sdc=sigsev(Lc);sm,mum,sdm=sigsev(Lm);se,mue,sde=sigsev(Le)
print("expansion mu/sd: current",muc,sdc," median",mum,sdm," mean",mue,sde)
print(f"{'ep':9}{'cur_sig':>9}{'stat_sig':>10}{'delta':>8}{'rel%':>8}{'mean_sig':>9}")
for nm in RECS:
    c,s=sc[nm],sm[nm];rel=round(100*(s-c)/c,1) if c else None
    print(f"{nm:9}{c:9}{s:10}{round(s-c,2):8}{rel:8}{se[nm]:9}")
print("margin 1980 vs 1981-82: current",round(sc['1980']-sc['1981-82'],3),"-> statistical",round(sm['1980']-sm['1981-82'],3))
