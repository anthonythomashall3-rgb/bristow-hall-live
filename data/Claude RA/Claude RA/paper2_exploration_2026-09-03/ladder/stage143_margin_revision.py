"""Stage 143: two checks on v13.  First a model-free description of the margin -- how close the
trigger statistic ever came to the line in each quiet year -- because seventeen annual maxima
cannot support an extreme value fit.  Second the revision test: v13 leans on continued claims,
which are revised, so the published revisions are resampled and the whole record replayed."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd, os
ALL=["Sahm","IUR","payrolls","housing","bill","claims","contclaims","IP"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in ALL}
ZMAXn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
V13=["Sahm","payrolls","housing","contclaims"]
LIN13={n:SC[n][0]+(ZMAXg[n]+0.25)*SC[n][1] for n in V13}
LIN11={"Sahm":0.36,"IUR":0.40,"payrolls":0.18,"housing":0.19,"bill":1.45}
def E_of(lines):
    out=np.full(N,-99.0)
    for n,t in lines.items(): out=np.maximum(out,(np.asarray(CH[n],float)-t)/SC[n][1])
    return np.where(np.isfinite(out),out,-99.0)
print("how close the trigger came to firing in each quiet year (0 = fires; units are robust sd)")
print("%-24s %-9s %-9s %-9s %-9s %s"%("rule","worst yr","median yr","yrs>-0.5","yrs>-1.0","quiet years"))
for lab,lines in [("v11 (max-margin)",LIN11),("v13 (record + 0.25 sd)",LIN13)]:
    E=E_of(lines); m=QC&G&CO
    s=pd.Series(E[m],index=cal[m]).replace(-99.0,np.nan).dropna()
    am=s.groupby(s.index.year).max()
    print("%-24s %-9.2f %-9.2f %-9d %-9d %d"%(lab,am.max(),am.median(),int((am>-0.5).sum()),int((am>-1.0).sum()),len(am)))
V=os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/CCSA_all_vintages.csv")
d=pd.read_csv(V); d["date"]=pd.to_datetime(d["date"]); d=d.set_index("date")
cols=[c for c in d.columns if c.startswith("CCSA_")]
vd=pd.to_datetime([c.split("_")[1] for c in cols],format="%Y%m%d")
first=[]
for i,wk in enumerate(d.index):
    j=np.searchsorted(vd,wk)
    while j<len(cols) and not np.isfinite(d[cols[j]].iloc[i]): j+=1
    if j<len(cols): first.append((wk,float(d[cols[j]].iloc[i]),float(d[cols[-1]].iloc[i])))
fp=pd.DataFrame(first,columns=["week","first","current"]).dropna()
fp=fp[fp.week>=pd.Timestamp("2009-09-01")]
rev=((fp["first"]/fp["current"])-1).values; rev=rev[np.isfinite(rev)]
print("\ncontinued-claims revisions, %d weeks from %s: median %+.3f%%, |rev|>1%% in %.0f%% of weeks, largest %+.1f%%"%(
    len(rev),str(fp.week.min().date()),100*np.median(rev),100*np.mean(np.abs(rev)>0.01),100*np.max(np.abs(rev))))
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
rng=np.random.default_rng(11); R=150
def replay_cc(ccx):
    c8=ccx.rolling(8).mean(); rc=(c8/c8.shift(1).rolling(52).min()-1)
    z=(sd(rc,5)-SC["contclaims"][0])/SC["contclaims"][1]
    hits=np.where(np.isfinite(z),z,-99.0)>=ZMAXg["contclaims"]+0.25
    for n in ["Sahm","payrolls","housing"]:
        zz=np.where(np.isfinite(Zz[n]),Zz[n],-99.0)
        hits=hits|(zz>=ZMAXg[n]+0.25)
    fr=fresh(hits&CO,120)&G
    zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
    fr=fr|fresh((zc>=ZMAXn+2.0)&CCO&NG,120)
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    return sum(1 for x in res if x["lag"] is not None), len(f) if f else 0
base=replay_cc(cc)
print("baseline with the current vintage: %d of 9 detected, %d false"%base)
ok=0; det9=0; fa=[]
for r in range(R):
    noise=rng.choice(rev,size=len(cc),replace=True)
    ccx=pd.Series(cc.values*(1+noise),index=cc.index)
    dt,nf=replay_cc(ccx); fa.append(nf)
    if dt==9: det9+=1
    if dt==9 and nf==0: ok+=1
print("under %d resampled revision draws: nine of nine in %d%% of draws, nine of nine AND no false alarm in %d%%"%(R,100*det9//R,100*ok//R))
print("false episodes per draw: mean %.2f, at most %d, none in %d%% of draws"%(np.mean(fa),max(fa),100*np.mean(np.array(fa)==0)))
