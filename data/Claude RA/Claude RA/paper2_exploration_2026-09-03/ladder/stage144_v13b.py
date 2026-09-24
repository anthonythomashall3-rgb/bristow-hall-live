"""Stage 144: v13 without continued claims.  The revision test kills the continued-claims
channel: resampling the published revisions leaves the record intact in only a fifth of draws.
Three first-print channels -- the Sahm indicator, payrolls and housing starts -- survive on
their own, and the only claims-dependent part left is the floor, which round 24 already made
revision-proof.  Persistence is also tried as a repair for continued claims."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd, os
ALL=["Sahm","IUR","payrolls","housing","bill","claims","contclaims","IP"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in ALL}
ZMAXn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zarr={n:np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in ALL}
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
def build(names,d=0.25,d2=2.0,lane=True,extra=None):
    hits=np.zeros(N,bool)
    for n in names: hits|=(Zarr[n]>=ZMAXg[n]+d)
    if extra is not None: hits|=extra
    fr=fresh(hits&CO,120)&G
    fr=fr|fresh((Zc>=ZMAXn+d2)&CCO&NG,120)
    lv=[]
    if lane:
        la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not fr[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
                if cal[i]>=pd.Timestamp("1968-06-01"): lv.append(str(cal[i].date()))
        fr=fr|valid
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    armed=int((hits&CO&G&QC).sum())
    return eps,res,f,det,armed,lv
FIRST9=FIRST
for lab,names in [("v13  Sahm+payrolls+housing+continued claims",["Sahm","payrolls","housing","contclaims"]),
                  ("v13b Sahm+payrolls+housing",["Sahm","payrolls","housing"]),
                  ("v13c Sahm+payrolls+housing+production",["Sahm","payrolls","housing","IP"]),
                  ("v13d Sahm+payrolls+housing+bill",["Sahm","payrolls","housing","bill"])]:
    eps,res,f,det,armed,lv=build(names)
    dd=[(e["onset"]-FIRST9[i]).days for i,e in enumerate(eps)][:9]
    print("%-44s %d/9 false %d armed %d | lags %s"%(lab,det,len(f) if f else 0,armed,[r["lag"] for r in res]))
    print("%-44s ends %s troughs %s days %s"%("",[r["end_lag"] for r in res],[r["tr_err"] for r in res],dd))
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
V=os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/CCSA_all_vintages.csv")
d_=pd.read_csv(V); d_["date"]=pd.to_datetime(d_["date"]); d_=d_.set_index("date")
cols=[c for c in d_.columns if c.startswith("CCSA_")]
vd=pd.to_datetime([c.split("_")[1] for c in cols],format="%Y%m%d")
rows=[]
for i,wk in enumerate(d_.index):
    j=np.searchsorted(vd,wk)
    while j<len(cols) and not np.isfinite(d_[cols[j]].iloc[i]): j+=1
    if j<len(cols): rows.append((wk,float(d_[cols[j]].iloc[i]),float(d_[cols[-1]].iloc[i])))
fp=pd.DataFrame(rows,columns=["week","first","current"]).dropna(); fp=fp[fp.week>=pd.Timestamp("2009-09-01")]
rev=((fp["first"]/fp["current"])-1).values; rev=rev[np.isfinite(rev)]
icv=pd.read_csv(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other/icsa_first_vs_current.csv"),parse_dates=["week"])
icv["fv"]=pd.to_datetime(icv.first_vintage.astype(str),format="%Y%m%d")
gg=icv[icv.fv>pd.Timestamp("2009-05-28")]; irev=((gg.first_print/gg.current)-1).values; irev=irev[np.isfinite(irev)]
rng=np.random.default_rng(23); R=150
def persist_weeks(z, th, k):
    s=pd.Series(z, index=cal)
    w=(s>=th)
    return (w.rolling(7*k,min_periods=1).min().fillna(0).astype(bool)).values
def draw(k_persist=None, use_cc=True):
    n1=rng.choice(irev,size=len(ic),replace=True)
    icx=pd.Series(ic.values*(1+n1),index=ic.index)
    m8=icx.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
    CLx=np.nan_to_num(sd(rr,5),nan=-9)
    co=pd.Series(CLx>=0.03).rolling(56,min_periods=1).max().fillna(0).astype(bool).values
    cco=pd.Series(CLx>=0.12).rolling(56,min_periods=1).max().fillna(0).astype(bool).values
    hits=np.zeros(N,bool)
    for n in ["Sahm","payrolls","housing"]: hits|=(Zarr[n]>=ZMAXg[n]+0.25)
    if use_cc:
        n2=rng.choice(rev,size=len(cc),replace=True)
        ccx=pd.Series(cc.values*(1+n2),index=cc.index)
        c8=ccx.rolling(8).mean(); rc=(c8/c8.shift(1).rolling(52).min()-1)
        z=(sd(rc,5)-SC["contclaims"][0])/SC["contclaims"][1]
        z=np.where(np.isfinite(z),z,-99.0); th=ZMAXg["contclaims"]+0.25
        hits|=persist_weeks(z,th,k_persist) if k_persist else (z>=th)
    fr=fresh(hits&co,120)&G
    fr=fr|fresh((Zc>=ZMAXn+2.0)&cco&NG,120)
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    return sum(1 for x in res if x["lag"] is not None), len(f) if f else 0
print("\nrevision test: %d draws, both the initial-claims floor and continued claims resampled"%R)
for lab,kp,ucc in [("v13   continued claims, no persistence",None,True),
                   ("v13   continued claims, two weeks",2,True),
                   ("v13   continued claims, three weeks",3,True),
                   ("v13b  no continued claims at all",None,False)]:
    d9=0; ok=0; fa=[]
    for _ in range(R):
        dt,nf=draw(kp,ucc); fa.append(nf)
        if dt==9: d9+=1
        if dt==9 and nf==0: ok+=1
    print("  %-40s nine of nine %3d%% | nine of nine and no false alarm %3d%% | false per draw mean %.2f max %d"%(
        lab,100*d9//R,100*ok//R,np.mean(fa),max(fa)))
