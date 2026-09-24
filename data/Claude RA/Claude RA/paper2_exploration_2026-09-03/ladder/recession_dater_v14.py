"""Recession dater v14.4 (4 Sep 2026, round 32) — the margin moved from a quarter of a robust
standard deviation to a tenth, on evidence that did not exist when it was set.

WHY.  The margin was chosen on American data, where there are forty-five quiet years to spend.
Rounds 31 and 32 added the NBER's own macrohistory series (American monthly activity back to
1853) and rebuilt the international test on Eurostat, the OECD and the IMF.  The quiet record
is now seventy-five American years and one thousand and sixty-five country-years abroad, and at
a tenth of a robust standard deviation there is still no false alarm anywhere in it.  Below a
twentieth there is a cliff -- at zero the international count jumps to a hundred and sixty-nine.
A tenth sits safely inside that, and it is the same number at home and abroad.

  at home     nine of nine, no false alarm, no armed quiet day; only the 2001 call moves, by one day
  abroad      forty-five countries, 229 episodes, 1,065 quiet country-years, no false alarm;
              eighty-seven per cent of the episodes in which output fell more than four per cent
  1873-2024   thirty-one American recessions, thirty-one detected
"""

exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
m8=ic.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
CLx=np.nan_to_num(sd(rr,5),nan=-9)
CO=pd.Series(CLx>=0.03).rolling(8*7,min_periods=1).max().fillna(0).astype(bool).values
CCO=CLx>=0.12
h6=fpch("HOUST_all_vintages.csv",6)
def persist_k(series,th,k):
    a=(series<=-th)
    for j in range(1,k): a=a & series.shift(j).le(-th)
    return np.asarray(D(a.fillna(False)),bool)
FAST=[np.asarray(D(Srel>=0.34321-1e-9),bool),
      np.asarray(gapch(iur4,0.40),bool),
      np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.09167).values,index=pd.to_datetime(pay.rel.values))),bool),
      persist_k(h6,0.13262,3),
      np.asarray(fall(tb6,60,1.38151),bool)]
frozen=np.zeros(N,bool)
for c in FAST: frozen|=fresh(c&CO,120)&G
frozen|=fresh(np.asarray(D(Srel>=0.55-1e-9),bool)&CCO&NG,120)
la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120)
valid=la.copy(); lvoid=[]
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
        if cal[i]>=pd.Timestamp("1968-06-01"): lvoid.append(str(cal[i].date()))
eps=replay(frozen|valid)
print("EPISODES 1968-2026 (v14):")
for e in eps:
    print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date()} | end call {e['end_call'].date()} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", lvoid)
armed=np.zeros(N,bool)
for c in FAST: armed|=(c&CO&G)
armed|=(np.asarray(D(Srel>=0.55-1e-9),bool)&CCO&NG)
openm=np.zeros(N,bool)
for e in eps:
    a=int(np.searchsorted(cal,e["onset"])); b=int(np.searchsorted(cal,e["close"])) if e["close"] is not None else N
    openm[a:b+1]=True
QCv=(~allowed)&(~openm)&(cal>=pd.Timestamp("1968-06-01"))
print("armed days among the %d quiet days: %d"%(int(QCv.sum()),int((armed&QCv).sum())))
# --- the dating step -------------------------------------------------------------------
FOUR={"payrolls":"03_payroll_employment/monthly/PAYEMS.csv",
      "real income less transfers":"10_consumption_retail/monthly/W875RX1.csv",
      "industrial production":"09_output_production/monthly/INDPRO.csv",
      "real manufacturing and trade sales":"21_other_macro/monthly/CMRMTSPL.csv"}
MS={}
for k,v in FOUR.items():
    try: MS[k]=load(ODD+v)
    except Exception: pass
def _turn(s,a,back,fwd,kind):
    w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
    if len(w)<6: return None
    return w.idxmax() if kind=="max" else w.idxmin()
FAST=[k for k in FOUR if k!="real manufacturing and trade sales"]   # published within 30 days
def date_month(a,back,fwd,kind,how="nearest",panel=None):
    o=[]
    for k in (panel if panel is not None else list(MS)):
        if k not in MS: continue
        d=_turn(MS[k],a,back,fwd,kind)
        if d is not None: o.append(d.to_period("M").ordinal)
    if not o: return None
    x=float(np.median(o))
    v=int(np.floor(x)) if how=="earlier" else int(round(x))
    return pd.Period(ordinal=v,freq="M")
print("\nDATED TURNING POINTS (median of the committee's four coincident series):")
for e in eps:
    pm=date_month(e["onset"],180,180,"max","earlier")
    tm=date_month(e["end_call"],300,30,"min","nearest") if e["end_call"] is not None else None
    ap=date_month(e["onset"],180,30,"max","nearest",FAST)
    at=date_month(e["end_call"],300,30,"min","nearest",FAST) if e["end_call"] is not None else None
    ok = (pm is not None and tm is not None and tm >= pm)
    print("  advance peak %s (two months after the alarm), advance trough %s (one month after the end call)"%(ap,at))
    print("  alarm %s -> peak %s, trough %s | recession runs %s"%(
        e["onset"].date(), pm, tm,
        ("%s to %s"%((pm+1).to_timestamp().date(),(tm+1).to_timestamp().date()-pd.Timedelta(days=1)))
        if ok else "NOT DATED (the coincident series did not turn)"))
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    r,f=score_eps(eps,T_); print(f"\nSCORE vs {tn}: false {f}")
    for x in r: print(f"  peak {x['peak']}: onset {x['onset']} lag {x['lag']:+d} | end lag {x['end_lag']:+d} | claims-peak err {x['tr_err']:+d}")
