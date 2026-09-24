"""Stage 105: the claims floor as written ('met today') is flipped by ordinary claims
revisions.  Robustify it the way the rest of the rule already works -- 'met at any point
in the prior W weeks' -- so one revised week cannot block or admit a call.  Test the
baseline record, the quiet exposure, and robustness to resampled revision noise."""
exec(open("stage104_split.py").read().split('d,e,f=build2(ic,ic,True)')[0])
import numpy as np, pandas as pd, os
def build3(claims_floor, claims_end, W=1, gf=0.03, cf=0.12, floor_on=True):
    m8=claims_floor.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
    CLx=np.nan_to_num(sd(rr,5),nan=-9)
    if floor_on:
        base_co=(CLx>=gf); base_cc=(CLx>=cf)
        if W>1:
            k=W*7
            co=pd.Series(base_co).rolling(k,min_periods=1).max().fillna(0).astype(bool).values
            cco=pd.Series(base_cc).rolling(k,min_periods=1).max().fillna(0).astype(bool).values
        else: co,cco=base_co,base_cc
    else: co=np.ones(N,bool); cco=np.ones(N,bool)
    F=[np.asarray(D(Srel>=0.36-1e-9),bool),np.asarray(gapch(iur4,0.40),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       HOU,np.asarray(fall(tb6,60,1.45),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&co,120)&G
    CLA=np.asarray(D(Srel>=0.55-1e-9),bool)&cco
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    global ma8d
    m8e=claims_end.rolling(8).mean(); v=m8e.copy(); v.index=v.index+pd.Timedelta(days=5)
    save=ma8d.copy(); ma8d=v.reindex(cal).ffill().values
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    ma8d=save
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&co&G)
    armed|=(CLA&NG)
    return ([str(e["onset"].date()) for e in eps],[str(e["end_call"].date()) for e in eps],f,int((armed&QC).sum()))
print("%-34s %-10s %-9s %-8s %s" % ("floor form","onsets","ends","false","quiet-armed days"))
for W,gf,cf in [(1,0.03,0.12),(4,0.03,0.12),(8,0.03,0.12),(13,0.03,0.12),
                (8,0.05,0.15),(8,0.08,0.20),(13,0.05,0.15),(13,0.08,0.20),(13,0.10,0.25)]:
    d,e,f,arm=build3(ic,ic,W,gf,cf)
    print("%-34s %-10s %-9s %-8s %d" % ("met within %2d wk, %.0f%%/%.0f%%"%(W,100*gf,100*cf),
          "ok" if d==REF else "CHANGED","ok" if e==REFe else "CHANGED",len(f) if f else 0,arm))
df=pd.read_csv(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other/icsa_first_vs_current.csv"),parse_dates=["week"])
df["fv"]=pd.to_datetime(df.first_vintage.astype(str),format="%Y%m%d")
g=df[df.fv>pd.Timestamp("2009-05-28")]
rev=((g.first_print/g.current)-1).values; rev=rev[np.isfinite(rev)]
rng=np.random.default_rng(3); R=200
print("\nrobustness to resampled claims-revision noise (floor input only; onsets and false episodes):")
print("%-34s %-22s %s" % ("floor form","onsets unchanged","false episodes"))
for W,gf,cf in [(1,0.03,0.12),(8,0.03,0.12),(13,0.05,0.15),(13,0.08,0.20)]:
    ok=fa=0
    for b in range(R):
        e_=rng.choice(rev,size=len(ic),replace=True)
        noisy=pd.Series(ic.values*(1+e_),index=ic.index)
        d,en,f,arm=build3(noisy,ic,W,gf,cf)
        if d==REF: ok+=1
        if f: fa+=1
    print("%-34s %-22s %d of %d" % ("met within %2d wk, %.0f%%/%.0f%%"%(W,100*gf,100*cf),
          "%d of %d (%.0f%%)"%(ok,R,100*ok/R), fa, R))
