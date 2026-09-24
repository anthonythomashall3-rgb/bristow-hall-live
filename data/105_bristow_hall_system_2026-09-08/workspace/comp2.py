"""COMPARATORS, COMPLETED. Sahm scored with a re-arm so a crossing belongs to one recession only; Michaillat-Saez on
the lab's own vacancy level; the NBER's own announcements; and v3.5. Every rule on actual release dates."""
exec(open('comp1.py').read().split('P("\\n=== 2. Michaillat-Saez')[0].replace("out=open('comp1.out','w')","out=open('comp2.out','w')"))
sys.path.insert(0,W+'/lab/slack'); from objects import load
VLEV=-load()['-vacancy rate']
P("\n=== 1b. Sahm with a re-arm (a crossing belongs to one recession only) ===")
calls=[]; armed=True
for m,v in g.items():
    if m<pd.Timestamp('1948-06-01'): continue
    if armed and v>=0.50:
        pub=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4)); calls.append((pub,m)); armed=False
    elif not armed and v<0.50: armed=True
used=set(); sv2=[]; q2=[]
for pub,m in calls:
    hit=None
    for i,(p_,t_) in enumerate(zip(PK,TR)):
        if p_-pd.DateOffset(months=6)<=m<=t_+pd.DateOffset(months=6) and i not in used: hit=i; break
    if hit is None: q2.append(m.strftime('%Y-%m'))
    else: used.add(hit); sv2.append((hit,(pub-me(PK[hit])).days))
lag2={i:d for i,d in sv2}
P("   "+" | ".join(f"{PK[i]:%Y-%m} {lag2.get(i)}" for i in range(13)))
sv2v=[d for i,d in sv2]
P(f"   detected {len(sv2)}/13, median {np.median(sv2v):.0f} days, mean {np.mean(sv2v):.1f}, within the month {sum(1 for x in sv2v if x<=31)}/13, false alarms {len(q2)} {q2}")
P("\n=== 2. Michaillat-Saez 0.29 / 0.81, first prints, later of the two releases ===")
u3=(UR.rolling(3).mean()-UR.rolling(12).min()).dropna()
v3=(VLEV.rolling(12).max()-VLEV.rolling(3).mean()).dropna()
pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in v3.index})
fires=[m for m in u3.index if m in v3.index and u3[m]>=0.29 and v3[m]>=0.81]
mcalls=[]; armed=True; prev=None
for m in v3.index:
    if m not in u3.index: continue
    on=(u3[m]>=0.29 and v3[m]>=0.81)
    if armed and on:
        pu=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4)); pv=pubs.get(m,pu)
        mcalls.append((max(pu,pv),m)); armed=False
    elif not armed and not on: armed=True
used=set(); mv=[]; qq=[]
for pub,m in mcalls:
    hit=None
    for i,(p_,t_) in enumerate(zip(PK,TR)):
        if p_-pd.DateOffset(months=6)<=m<=t_+pd.DateOffset(months=6) and i not in used: hit=i; break
    if hit is None: qq.append(m.strftime('%Y-%m'))
    else: used.add(hit); mv.append((hit,(pub-me(PK[hit])).days))
lagm={i:d for i,d in mv}
P(f"   vacancy level span {VLEV.index.min().date()} -> {VLEV.index.max().date()}")
P("   "+" | ".join(f"{PK[i]:%Y-%m} {lagm.get(i)}" for i in range(13)))
mvv=[d for i,d in mv]
P(f"   detected {len(mv)}/13, median {np.median(mvv):.0f} days, mean {np.mean(mvv):.1f}, within the month {sum(1 for x in mvv if x<=31)}/13, false alarms {len(qq)} {qq}")
nl=[(PK[i].strftime('%Y-%m'),((pd.Timestamp(NBER[PK[i].strftime('%Y-%m')])-me(PK[i])).days if NBER[PK[i].strftime('%Y-%m')] else None)) for i in range(13)]
nv=[b for a,b in nl if b is not None]
P("\n=== 4. SIDE BY SIDE, same clock, same thirteen turns ===")
P(f"   {'rule':30s} {'detected':>9s} {'median d':>9s} {'mean d':>8s} {'within month':>13s} {'false alarms':>13s}")
P(f"   {'v3.5 (this rule), real-time':30s} {'13/13':>9s} {np.median(V):9.0f} {np.mean(V):8.1f} {str(sum(1 for x in V if x<=31))+'/13':>13s} {'0':>13s}")
P(f"   {'Sahm 0.50 alone':30s} {str(len(sv2))+'/13':>9s} {np.median(sv2v):9.0f} {np.mean(sv2v):8.1f} {str(sum(1 for x in sv2v if x<=31))+'/13':>13s} {str(len(q2)):>13s}")
P(f"   {'Michaillat-Saez 0.29/0.81':30s} {str(len(mv))+'/13':>9s} {np.median(mvv):9.0f} {np.mean(mvv):8.1f} {str(sum(1 for x in mvv if x<=31))+'/13':>13s} {str(len(qq)):>13s}")
P(f"   {'NBER announcements':30s} {str(len(nv))+'/13':>9s} {np.median(nv):9.0f} {np.mean(nv):8.1f} {'0/13':>13s} {'0':>13s}")
P("\n   (Michaillat-Saez is measurable only from December 2000 on its own vacancy series unless the reconstruction is used;")
P("    the row above uses the same Barnichon reconstruction this rule uses, so the two are on identical inputs.)")
out.close()
