"""Recession dater v11-A — the A PRIORI rule (4 Sep 2026, round 25).

A companion to v11, not a replacement, and the answer to the question a referee will ask
first: how much of the record depends on thresholds fitted to the record?

v11's six lines are max-margin midpoints between each channel's calm-period maximum and the
smallest reading it must carry -- which consults the recessions.  v11-A replaces all six at
once with a single sentence that consults none of them:

    EVERY CHANNEL FIRES WHEN IT EXCEEDS ITS OWN CALM-PERIOD MAXIMUM BY FIVE PERCENT.

One parameter for the whole rule instead of six fitted thresholds.  Structure, gate, claims
floor, freshness, lane, end rule and close rule are v11's, unchanged.

   Sahm 0.350 · insured unemployment 0.236 · payrolls -0.086% · housing -12.8% x3
   · bill 1.407 pp · no-inversion clause 0.525

RESULT: nine of nine recessions detected, ZERO false episodes, zero armed days on the
13,911 calm days, nine of nine in the no-inversion simulation, and the same nine end calls
and dated troughs as v11.

   onsets   6 Oct 1969 · 17 Oct 1973 · 6 Dec 1979 · 18 Aug 1981 · 3 Aug 1990
            · 11 Jan 2001 · 18 Dec 2007 · 28 Feb 2020 · 3 May 2024
   lags     -2, -1, -1, +1, +1, -2, 0, 0, +1
   days from the day each recession began: -87, -45, -57, +17, +2, -80, -14, -2, +2

Against v11 it is FASTER on four calls -- 1973 by 8 days, 1980 by 28, 2001 by 22, and
2007-09 by 17 days, which moves that call to 18 December 2007, a fortnight BEFORE the
recession began.  It costs the 2001 call, which goes from one month early to two, so seven
of nine sit inside a month against v11's eight; and its fitted hazard is 0.0200 a year, one
in 50, against v11's one in 95.

WHICH TO USE.  v11 for the chronology: tighter lags, half the hazard.  v11-A for the
robustness statement, which is the stronger scientific claim: with not one threshold fitted
to any recession, the rule still detects all nine with no false alarms.  The record is not
an artefact of the fitting."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd
m8=ic.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
CLx=np.nan_to_num(sd(rr,5),nan=-9)
CO=pd.Series(CLx>=0.03).rolling(8*7,min_periods=1).max().fillna(0).astype(bool).values
CCO=CLx>=0.12
S=Srel.reindex(cal).ffill().values.astype(float)
IURg=sd(iur4-iur4.rolling(52).min(),12)
PAY1=sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
H6=np.minimum.reduce([sd(-h6.shift(j)) for j in range(3)]); BILL=sd(-(tb6-tb6.shift(60)),1)
def qmax(v,gated):
    m=QC&(G if gated else np.ones(N,bool))&(CO if gated else CCO)
    x=v[m]; x=x[np.isfinite(x)]; return float(np.max(x))
C=1.05
TH={"Sahm":qmax(S,True)*C,"IUR":qmax(IURg,True)*C,"payrolls":qmax(-PAY1,True)*C,
    "housing":qmax(H6,True)*C,"bill":qmax(BILL,True)*C,"clause":qmax(S,False)*C}
print("a-priori thresholds (calm-period maximum x 1.05):", {k:round(v,3) for k,v in TH.items()})
FAST=[np.asarray(D(Srel>=TH["Sahm"]-1e-9),bool), np.asarray(gapch(iur4,TH["IUR"]),bool),
      np.asarray(D(pd.Series((pay.d1.astype(float)<=-TH["payrolls"]).values,index=pd.to_datetime(pay.rel.values))),bool),
      persist_k(h6,TH["housing"],3), np.asarray(fall(tb6,60,TH["bill"]),bool)]
frozen=np.zeros(N,bool)
for c in FAST: frozen|=fresh(c&CO,120)&G
frozen|=fresh(np.asarray(D(Srel>=TH["clause"]-1e-9),bool)&CCO&NG,120)
la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy(); lv=[]
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
        if cal[i]>=pd.Timestamp("1968-06-01"): lv.append(str(cal[i].date()))
eps=replay(frozen|valid); res,f=score_eps(eps,T_P1)
print("onsets:", [str(e["onset"].date()) for e in eps])
print("lags %s | ends %s | troughs %s | false %s | lane voided %s"
      % ([x["lag"] for x in res],[x["end_lag"] for x in res],[x["tr_err"] for x in res], f if f else 0, lv))
armed=np.zeros(N,bool)
for c in FAST: armed|=(c&CO&G)
armed|=(np.asarray(D(Srel>=TH["clause"]-1e-9),bool)&CCO&NG)
print("armed days on the canonical quiet set:", int((armed&QC).sum()), "of", int(QC.sum()))
