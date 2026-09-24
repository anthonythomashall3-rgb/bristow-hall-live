"""Stage 145: v14, the union.  v11 and the record-based rule fire on different recessions
first, and both have zero armed quiet days, so their union cannot arm on a quiet day either.
The union is therefore at least as fast as each of them everywhere and no more exposed."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd, os
ALL=["Sahm","IUR","payrolls","housing","bill","claims","contclaims","IP"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in ALL}
ZMAXn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zarr={n:np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in ALL}
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
V11={"Sahm":0.36,"IUR":0.40,"payrolls":0.18,"housing":0.19,"bill":1.45}
def hits_v11():
    F=[np.asarray(D(Srel>=0.36-1e-9),bool),np.asarray(gapch(iur4,0.40),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       persist_k(h6,0.19,3),np.asarray(fall(tb6,60,1.45),bool)]
    h=np.zeros(N,bool)
    for c in F: h|=c
    return h
def hits_rec(names,d=0.25):
    h=np.zeros(N,bool)
    for n in names: h|=(Zarr[n]>=ZMAXg[n]+d)
    return h
def assemble(h,clause_z=2.0,clause_raw=None,lane=True):
    fr=fresh(h&CO,120)&G
    CLA=(np.asarray(D(Srel>=clause_raw-1e-9),bool)&CCO&NG) if clause_raw else ((Zc>=ZMAXn+clause_z)&CCO&NG)
    fr=fr|fresh(CLA,120)
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
    armed=int(((h&CO&G)|CLA)[QC].sum())
    return eps,res,f,det,armed,lv
V13D=["Sahm","payrolls","housing","bill"]
CASES=[("v11",hits_v11(),0.55),
       ("v13b  Sahm + payrolls + housing",hits_rec(["Sahm","payrolls","housing"]),None),
       ("v13d  Sahm + payrolls + housing + bill",hits_rec(V13D),None),
       ("v14   v11 or v13d",hits_v11()|hits_rec(V13D),0.55),
       ("v14b  v11 or v13b",hits_v11()|hits_rec(["Sahm","payrolls","housing"]),0.55)]
print("%-40s %-6s %-7s %-7s %-24s %s"%("rule","det","false","armedQ","lags","days from the first day"))
for lab,h,craw in CASES:
    eps,res,f,det,armed,lv=assemble(h,clause_raw=craw)
    dd=[(e["onset"]-FIRST[i]).days for i,e in enumerate(eps)][:9]
    print("%-40s %-6s %-7d %-7d %-24s %s"%(lab,"%d/9"%det,len(f) if f else 0,armed,str([r["lag"] for r in res]),dd))
    print("%-40s ends %s troughs %s mean|days| %.1f  inside a week %d"%("",[r["end_lag"] for r in res],[r["tr_err"] for r in res],float(np.mean(np.abs(dd))),sum(1 for x in dd if abs(x)<=7)))
icv=pd.read_csv(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other/icsa_first_vs_current.csv"),parse_dates=["week"])
icv["fv"]=pd.to_datetime(icv.first_vintage.astype(str),format="%Y%m%d")
gg=icv[icv.fv>pd.Timestamp("2009-05-28")]; irev=((gg.first_print/gg.current)-1).values; irev=irev[np.isfinite(irev)]
rng=np.random.default_rng(31); R=150
def draw(h):
    n1=rng.choice(irev,size=len(ic),replace=True)
    icx=pd.Series(ic.values*(1+n1),index=ic.index)
    m8=icx.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
    CLx=np.nan_to_num(sd(rr,5),nan=-9)
    co=pd.Series(CLx>=0.03).rolling(56,min_periods=1).max().fillna(0).astype(bool).values
    cco=pd.Series(CLx>=0.12).rolling(56,min_periods=1).max().fillna(0).astype(bool).values
    fr=fresh(h&co,120)&G
    fr=fr|fresh((Zc>=ZMAXn+2.0)&cco&NG,120)
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    return sum(1 for x in res if x["lag"] is not None), len(f) if f else 0
print("\nrevision test on the claims floor (%d draws)"%R)
for lab,h,craw in CASES:
    ok=0
    for _ in range(R):
        dt,nf=draw(h)
        if dt==9 and nf==0: ok+=1
    print("  %-40s nine of nine and no false alarm in %3d%% of draws"%(lab,100*ok//R))
