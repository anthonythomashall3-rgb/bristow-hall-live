"""Stage 104: is the fragility from the claims FLOOR or from the claims-based END rule?
Perturb claims in one place at a time, and compare v10 with v8 (which has no floor)."""
exec(open("stage103_floorrisk.py").read().split("base=build(ic)")[0])
import numpy as np, pandas as pd, os
REFe=['1970-12-17','1975-05-08','1980-07-24','1982-11-18','1991-05-09','2001-12-13','2009-05-14','2020-05-28','2024-09-26']
def build2(claims_for_floor, claims_for_end, floor_on=True):
    m8=claims_for_floor.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
    CLx=np.nan_to_num(sd(rr,5),nan=-9)
    co=(CLx>=0.03) if floor_on else np.ones(N,bool)
    cco=(CLx>=0.12) if floor_on else np.ones(N,bool)
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
    m8e=claims_for_end.rolling(8).mean(); v=m8e.copy(); v.index=v.index+pd.Timedelta(days=5)
    save=ma8d.copy(); ma8d=v.reindex(cal).ffill().values
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    ma8d=save
    return [str(e["onset"].date()) for e in eps],[str(e["end_call"].date()) for e in eps],f
d,e,f=build2(ic,ic,True)
print("v10 baseline: onsets %s | ends %s | false %s" % ("ok" if d==REF else d, "ok" if e==REFe else e, f if f else 0))
d,e,f=build2(ic,ic,False)
print("v8 baseline (no floor): onsets %s | ends %s | false %s" % ("ok" if d==REF else "CHANGED","ok" if e==REFe else "CHANGED",f if f else 0))
df=pd.read_csv(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other/icsa_first_vs_current.csv"),parse_dates=["week"])
df["fv"]=pd.to_datetime(df.first_vintage.astype(str),format="%Y%m%d")
rev=((df[df.fv>pd.Timestamp("2009-05-28")].first_print/df[df.fv>pd.Timestamp("2009-05-28")].current)-1).values
rev=rev[np.isfinite(rev)]
rng=np.random.default_rng(7); R=200
def trial(mode):
    ok=fa=0
    for b in range(R):
        e_=rng.choice(rev,size=len(ic),replace=True)
        noisy=pd.Series(ic.values*(1+e_),index=ic.index)
        if mode=="floor":   d,en,f=build2(noisy,ic,True)
        elif mode=="end":   d,en,f=build2(ic,noisy,True)
        elif mode=="both":  d,en,f=build2(noisy,noisy,True)
        else:               d,en,f=build2(noisy,noisy,False)   # v8, no floor
        if d==REF and en==REFe and not f: ok+=1
        if f: fa+=1
    return ok,fa
print("\n%-34s %-24s %s" % ("claims noise applied to","record unchanged","a false episode appeared")) 
for mode,lab in [("floor","v10: the floor only"),("end","v10: the end rule only"),
                 ("both","v10: both"),("none","v8: no floor, end rule only")]:
    ok,fa=trial(mode)
    print("%-34s %-24s %d of %d" % (lab,"%d of %d (%.0f%%)"%(ok,R,100*ok/R),fa,R))
