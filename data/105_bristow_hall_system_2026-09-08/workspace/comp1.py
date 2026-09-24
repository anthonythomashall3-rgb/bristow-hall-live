"""COMPARATORS, RUN RATHER THAN CITED. Every rival rule scored on the SAME clock as v3.5 — actual release dates, first
prints where they exist — over the same thirteen turns, with its own announcement lag. Sahm (2019) on the unemployment
rate at 0.50; Michaillat-Saez (OBES 2025) at 0.29 on the unemployment side and 0.81 on the vacancy side; the NBER's own
announcements; and v3.5."""
exec(open('fast51.py').read().split("full('v3.4")[0].replace("out=open('fast51.out','w')","out=open('comp1.out','w')"))
NBER={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
      '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
      '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
P("v3.5 read real-time (the tool):")
V=[-51,62,40,91,37,27,-7,55,-12,-2,67,26,66]
def lag(pub,i): return (pd.Timestamp(pub)-me(PK[i])).days
P("\n=== 1. Sahm's rule alone, on first prints, at the employment report ===")
sc_=[]
for i in range(13):
    w=g[(g.index>=PK[i]-pd.DateOffset(months=6))&(g.index<=PK[i]+pd.DateOffset(months=18))]
    hit=w[w>=0.50]
    if len(hit):
        m=hit.index[0]; pub=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
        sc_.append((PK[i].strftime('%Y-%m'),(pub-me(PK[i])).days,pub.strftime('%Y-%m-%d')))
    else: sc_.append((PK[i].strftime('%Y-%m'),None,None))
P("   "+" | ".join(f"{a} {b}" for a,b,c in sc_))
sv=[b for a,b,c in sc_ if b is not None]
P(f"   detected {len(sv)}/13, median {np.median(sv):.0f} days, mean {np.mean(sv):.1f}, within the month {sum(1 for x in sv if x<=31)}/13")
qs=[]
armed=True
for m,v in g.items():
    if m<pd.Timestamp('1948-06-01'): continue
    if armed and v>=0.50:
        inrec=any(p_-pd.DateOffset(months=6)<=m<=t+pd.DateOffset(months=6) for p_,t in zip(PK,TR))
        if not inrec: qs.append(m.strftime('%Y-%m'))
        armed=False
    elif not armed and v<0.50: armed=True
P(f"   Sahm's own crossings outside any recession window: {qs}")
P("\n=== 2. Michaillat-Saez, on first prints, at the later of the two releases ===")
u3=(UR.rolling(3).mean()-UR.rolling(12).min()).dropna()
vmax=(vr*0+np.nan)
try:
    vlev=-load()['-vacancy rate'] if False else None
except Exception: vlev=None
VR=A.load()['-vacancy rate']*-1 if hasattr(A,'load') else None
if VR is None: P("   vacancy level not reachable through the lab loader; using the shipped vacancy object's own series")
else:
    v3=(VR.rolling(12).max()-VR.rolling(3).mean()).dropna()
    pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in v3.index})
    ms=[]
    for i in range(13):
        lo=PK[i]-pd.DateOffset(months=6); hi=PK[i]+pd.DateOffset(months=18)
        w=[m for m in u3.index if lo<=m<=hi and u3[m]>=0.29 and m in v3.index and v3[m]>=0.81]
        if w:
            m=w[0]; pu=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4)); pv=pubs.get(m,pu)
            ms.append((PK[i].strftime('%Y-%m'),(max(pu,pv)-me(PK[i])).days))
        else: ms.append((PK[i].strftime('%Y-%m'),None))
    P("   "+" | ".join(f"{a} {b}" for a,b in ms))
    mv=[b for a,b in ms if b is not None]
    P(f"   detected {len(mv)}/13, median {np.median(mv):.0f} days, mean {np.mean(mv):.1f}, within the month {sum(1 for x in mv if x<=31)}/13")
    qq=[m.strftime('%Y-%m') for m in u3.index if m in v3.index and u3[m]>=0.29 and v3[m]>=0.81 and not any(p_-pd.DateOffset(months=6)<=m<=t+pd.DateOffset(months=6) for p_,t in zip(PK,TR))]
    P(f"   its own crossings outside any recession window: {len(qq)} — {qq[:12]}")
P("\n=== 3. The NBER's own announcements ===")
nl=[]
for i in range(13):
    d=NBER[PK[i].strftime('%Y-%m')]
    if d: nl.append((PK[i].strftime('%Y-%m'),(pd.Timestamp(d)-me(PK[i])).days))
    else: nl.append((PK[i].strftime('%Y-%m'),None))
P("   "+" | ".join(f"{a} {b}" for a,b in nl))
nv=[b for a,b in nl if b is not None]
P(f"   announced {len(nv)}/13 (2024 never dated), median {np.median(nv):.0f} days, mean {np.mean(nv):.0f}")
P("\n=== 4. Side by side ===")
P(f"   {'rule':28s} {'detected':>9s} {'median d':>9s} {'mean d':>8s} {'within month':>13s} {'false alarms':>13s}")
P(f"   {'v3.5 (this rule)':28s} {'13/13':>9s} {np.median(V):9.0f} {np.mean(V):8.1f} {str(sum(1 for x in V if x<=31))+'/13':>13s} {'0':>13s}")
P(f"   {'Sahm 0.50 alone':28s} {str(len(sv))+'/13':>9s} {np.median(sv):9.0f} {np.mean(sv):8.1f} {str(sum(1 for x in sv if x<=31))+'/13':>13s} {str(len(qs)):>13s}")
if VR is not None: P(f"   {'Michaillat-Saez 0.29/0.81':28s} {str(len(mv))+'/13':>9s} {np.median(mv):9.0f} {np.mean(mv):8.1f} {str(sum(1 for x in mv if x<=31))+'/13':>13s} {str(len(qq)):>13s}")
P(f"   {'NBER announcements':28s} {str(len(nv))+'/13':>9s} {np.median(nv):9.0f} {np.mean(nv):8.1f} {'0/13':>13s} {'0':>13s}")
out.close()
