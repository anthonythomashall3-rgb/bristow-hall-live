"""Stage 116: 'within the week' for ONSETS, stated as an optimisation rather than an
aspiration.  The recession's first day is the first day of the month after the peak.
Maximise how many of the nine calls land within +-7 days of it, subject to zero false
episodes and all nine detected.  Note which calls are LATE (need speed) and which are
EARLY (need the opposite)."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd, itertools
FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
m8=ic.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
CLx=np.nan_to_num(sd(rr,5),nan=-9)
CO=pd.Series(CLx>=0.03).rolling(8*7,min_periods=1).max().fillna(0).astype(bool).values
CCO=CLx>=0.12
def build(sahm,iur,payx,hou,bill,clause):
    F=[np.asarray(D(Srel>=sahm-1e-9),bool),np.asarray(gapch(iur4,iur),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-payx).values,index=pd.to_datetime(pay.rel.values))),bool),
       persist_k(h6,hou,3),np.asarray(fall(tb6,60,bill),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&CO,120)&G
    CLA=np.asarray(D(Srel>=clause-1e-9),bool)&CCO
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    if len(eps)!=9: return None
    d=[e["onset"] for e in eps]
    dd=[(d[i]-FIRST[i]).days for i in range(9)]
    return d,dd,f,sum(1 for x in res if x["lag"] is not None)
base=build(0.36,0.40,0.18,0.19,1.45,0.55)
print("v11 days from the recession's first day: %s" % base[1])
print("   within +-7 days: %d of 9 | late (>+7): %s | early (<-7): %s"
      % (sum(1 for x in base[1] if abs(x)<=7),
         [i for i,x in enumerate(base[1]) if x>7],[i for i,x in enumerate(base[1]) if x<-7]))
GR={"sahm":[0.36,0.40,0.45,0.50,0.55,0.60],"iur":[0.40,0.45,0.50,0.55,0.60],
    "pay":[0.18,0.22,0.26,0.30],"hou":[0.19,0.22,0.25],"bill":[1.45,1.60,1.80,2.00,2.20],
    "clause":[0.55,0.60,0.70]}
best=[]
for s_ in GR["sahm"]:
  for i_ in GR["iur"]:
    for p_ in GR["pay"]:
      for h_ in GR["hou"]:
        for b_ in GR["bill"]:
          for c_ in GR["clause"]:
            r=build(s_,i_,p_,h_,b_,c_)
            if r is None: continue
            d,dd,f,det=r
            if f or det!=9: continue
            nwk=sum(1 for x in dd if abs(x)<=7)
            best.append((nwk,-sum(abs(x) for x in dd),s_,i_,p_,h_,b_,c_,dd,[str(x.date()) for x in d]))
best.sort(reverse=True)
print("\nfrontier: most onsets inside a week of the day the recession began, zero false alarms, 9/9 detected")
print("%-6s %-46s %s" % ("in wk","thresholds (sahm,iur,pay,hou,bill,clause)","days from the first day"))
seen=set()
for nwk,neg,s_,i_,p_,h_,b_,c_,dd,d in best[:10]:
    k=tuple(dd)
    if k in seen: continue
    seen.add(k)
    print("%-6d %-46s %s" % (nwk,"%.2f %.2f %.2f %.2f %.2f %.2f"%(s_,i_,p_,h_,b_,c_),dd))
    if len(seen)>=6: break
print("\ntotal parameter sets tried: %d ; sets with zero false alarms and 9/9: %d" % (
    len(GR['sahm'])*len(GR['iur'])*len(GR['pay'])*len(GR['hou'])*len(GR['bill'])*len(GR['clause']), len(best)))
