"""Stage 176: the faster end rule, inside the machine.  A ten-week claims average and a one per
cent fall gives the end call three weeks earlier and the trough date one episode better, but the
end call is not a standalone object -- it opens and closes episodes, and a looser rule can end an
episode inside a recession and let a second one open.  This runs it in the full replay."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
ZM={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in NAMES}
ZNn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
def hits_v14():
    h=np.zeros(N,bool)
    for n in ["Sahm","payrolls","housing","bill"]:
        z=np.where(np.isfinite(Zz[n]),Zz[n],-99.0); h|=(z>=ZM[n]+0.25)
    h|=np.asarray(gapch(iur4,0.40),bool)
    return h
def mad_ma(w):
    m=ic.rolling(w).mean(); x=m.copy(); x.index=x.index+pd.Timedelta(days=5)
    return x.reindex(cal).ffill().values.astype(float)
def replay_v(trig, ma, endpct):
    eps=[]; open_=False; i=0
    while i<N:
        if not open_:
            if trig[i] and cal[i]>=pd.Timestamp("1968-06-01"):
                open_=True; start=i; runmax=-1; pk=None; endcall=None
            i+=1; continue
        v=ma[i]
        if not np.isnan(v):
            if v>runmax: runmax=v; pk=i; endcall=None
        ok=(not np.isnan(v)) and pk is not None and v<=runmax*(1-endpct)
        if ok and endcall is None: endcall=i
        if endcall is not None and B3[i] and CALM[i]:
            eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i])); open_=False
        i+=1
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,
                              end_call=cal[endcall] if endcall else None,close=None))
    return eps
h=hits_v14()
fr=fresh(h&CO,120)&G
fr=fr|fresh((Zc>=ZNn+2.0)&CCO&NG,120)
la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not fr[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
fr=fr|valid
print("%-10s %-7s %-6s %-7s %-26s %s"%("weeks","fall","episodes","false","end lags (months)","end call dates"))
for w in [8,10,13]:
  for pct in [0.01,0.02,0.03]:
    ma=mad_ma(w)
    eps=replay_v(fr,ma,pct)
    res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    if det!=9: print("%-10d %-7.0f%% %-6d %-7s  only %d of 9 detected"%(w,100*pct,len(eps),"-",det)); continue
    print("%-10d %-7.0f%% %-6d %-7d %-26s %s"%(w,100*pct,len(eps),len(f) if f else 0,
          str([r["end_lag"] for r in res]),[str(e["end_call"].date()) for e in eps][:4]))
    print("%-10s %-7s trough weeks %s | closes %s"%("","",[r["tr_err"] for r in res],
          [str(e["close"].date()) if e["close"] is not None else "open" for e in eps][-3:]))
