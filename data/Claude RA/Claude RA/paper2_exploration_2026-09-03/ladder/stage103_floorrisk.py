"""Stage 103: weekly claims ARE revised (63% of weeks by >1%, max 29%), and the floor's
verdict flips in 18% of weeks at 3%.  So: how much slack does the floor have at each of
v10's nine call dates, and does resampled revision noise ever change the record?"""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
exec(open("stage44_evt.py").read().split("print(\"\\n=== (B) EXTREME")[0])
import numpy as np, pandas as pd, os
G=np.asarray(GATE[12],bool); NG=~G
QC=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
h6=fpch("HOUST_all_vintages.csv",6)
def persist_k(series,th,k):
    a=(series<=-th)
    for j in range(1,k): a=a & series.shift(j).le(-th)
    return np.asarray(D(a.fillna(False)),bool)
HOU=persist_k(h6,0.19,3)
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
def build(claims_series):
    m8=claims_series.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
    CLx=np.nan_to_num(sd(rr,5),nan=-9); co=CLx>=0.03; cco=CLx>=0.12
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
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&co&G)
    armed|=(CLA&NG)
    return [str(e["onset"].date()) for e in eps],[x["lag"] for x in res],f,int((armed&QC).sum()),CLx
base=build(ic)
print("v10 on current-vintage claims: dates %s | false %s | quiet-armed %d"
      % ("identical" if base[0]==REF else base[0], base[2] if base[2] else 0, base[3]))
CLb=base[4]
print("\nfloor slack at each call date (the floor is 3%%; the clause floor 12%%):")
for d in REF:
    i=int(np.where(cal==pd.Timestamp(d))[0][0])
    print("   %s  claims 8-week average %6.1f%% above its 52-week minimum  -> slack %+.1f pp over the 3%% floor" %
          (d,100*CLb[i],100*CLb[i]-3))
# ---- resampled revision noise on the pre-2009 claims ----
df=pd.read_csv(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other/icsa_first_vs_current.csv"),parse_dates=["week"])
df["fv"]=pd.to_datetime(df.first_vintage.astype(str),format="%Y%m%d")
gen=df[df.fv>pd.Timestamp("2009-05-28")]
rev=((gen.first_print/gen.current)-1).values          # first print relative to the settled value
rev=rev[np.isfinite(rev)]
print("\nresampling the observed first-print revision distribution (n=%d, sd %.3f) onto the whole claims history" % (len(rev),rev.std()))
rng=np.random.default_rng(11)
bad=0; falses=0; moved=0
R=300
for b in range(R):
    e=rng.choice(rev,size=len(ic),replace=True)
    noisy=pd.Series(ic.values*(1+e),index=ic.index)
    d,l,f,arm,_=build(noisy)
    if f: falses+=1
    if d!=REF: moved+=1
    if f or d!=REF: bad+=1
print("  %d replications: record unchanged in %d (%.0f%%) | a call moved in %d | a false episode appeared in %d"
      % (R,R-bad,100*(R-bad)/R,moved,falses))
