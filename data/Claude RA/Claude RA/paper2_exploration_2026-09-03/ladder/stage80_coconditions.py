"""Stage 80: generalise the co-condition.  For each remaining channel, find the cheapest
co-condition that leaves every onset date, every end date and the no-inversion world
untouched while cutting the channel's quiet exposure."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
WINS=[(pd.Timestamp(p),pd.Timestamp(t)) for p,t in T_P1]
QUIET=np.ones(N,bool)&(cal>=pd.Timestamp("1968-06-01"))
for p,t in WINS: QUIET &= ~((cal>=p-pd.DateOffset(months=6))&(cal<=t+pd.DateOffset(months=12)))
def sd(s,lag):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
IG=sd(iur4-iur4.rolling(52).min(),12); CL=sd(r8,5); S=Srel.reindex(cal).ffill().values.astype(float)
CO={"none":np.ones(N,bool),
    "claims 8wk >= 5% over 52wk min":CL>=0.05,
    "claims 8wk >= 10% over 52wk min":CL>=0.10,
    "claims 8wk >= 15%":CL>=0.15,
    "IUR gap >= 0.10":IG>=0.10,
    "Sahm >= 0.10":S>=0.10,
    "Sahm >= 0.20":S>=0.20}
CO={k:np.nan_to_num(v,nan=False).astype(bool) for k,v in CO.items()}
FAST0={"sahm":np.asarray(D(Srel>=0.36-1e-9),bool),"iur":np.asarray(gapch(iur4,0.40),bool),
       "pay":np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       "hou":np.asarray(persist2(h3,20),bool),"bill":np.asarray(fall(tb6,60,1.45),bool)}
CLAUSE0=np.asarray(D(Srel>=0.55-1e-9),bool)
LANE0=np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool)
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
def build(fastmods, clausemod):
    fr=np.zeros(N,bool)
    for k,c in FAST0.items(): fr|=fresh(c&fastmods.get(k,np.ones(N,bool)),120)&G
    fr|=fresh((CLAUSE0&clausemod)&NG,120)
    la=fresh(LANE0,120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); r,f=score_eps(eps,T_P1)
    fz=fresh(CLAUSE0&clausemod,120); rN,_=score_eps(replay(fz),T_P1)
    return ([str(e["onset"].date()) for e in eps]==REF,
            [str(e["end_call"].date()) for e in eps], f,
            sum(1 for x in rN if x["lag"] is not None))
END0=build({}, np.ones(N,bool))[1]
print("%-10s %-34s %-7s %-7s %-7s %s" % ("channel","co-condition","dates","ends","no-inv","quiet exposure"))
best={}
for ch,arr in list(FAST0.items())+[("clause",CLAUSE0)]:
    e0=100*(arr&QUIET).sum()/QUIET.sum()
    keep=None
    for nm,c in CO.items():
        if ch=="clause": ok,ends,f,n=build({}, c)
        else: ok,ends,f,n=build({ch:c}, np.ones(N,bool))
        good = ok and ends==END0 and not f and n==9
        exp=100*(arr&c&QUIET).sum()/QUIET.sum()
        if good and (keep is None or exp<keep[1]): keep=(nm,exp)
        if nm!="none" and good:
            print("%-10s %-34s %-7s %-7s %-7s %.3f%%  (was %.3f%%)" % (ch,nm,"ok","ok","9/9",exp,e0))
    best[ch]=keep
    print("   -> best for %-8s %s" % (ch, best[ch]))
