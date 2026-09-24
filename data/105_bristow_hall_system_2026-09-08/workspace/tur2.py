"""THE OBJECT THAT CANNOT TURN EARLY. Starts and claims lead the trough, so they close before it. The unemployment rate
does not: it peaks at or after the trough, never before, and its first print lands on day five of the following month.
Two forms are tried as the CONFIRMER, with the fast leading objects as the PROPOSER - speed from the object that leads,
safety from the one that cannot: (1) the rate rounds over, its three-month mean no higher than k months earlier;
(2) the rule closes itself, the branch that opened the episode back below its own line."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tur2.out','w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna()
CL=ICfp.dropna().rolling(4).mean().dropna(); LCL=np.log(CL); MXC=LCL.rolling(52,min_periods=26).max(); BELOW=(MXC-LCL).dropna()
URc=UR.dropna(); U3=URc.rolling(3).mean().dropna()
def urpub(m): return rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
def roll_over(k,tol):
    """the first month whose three-month mean of the unemployment rate is no higher than k months earlier, by tol"""
    out_={}
    for m,v in U3.items():
        p=m-pd.DateOffset(months=k)
        if p in U3.index and v<=U3[p]-tol: out_[m]=urpub(m)
    return out_
def selfclose():
    """the low branch back below its own line: the insured rate no longer above its 52-month minimum by the line"""
    gap=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()
    return {m:(m+pd.DateOffset(months=1)+pd.Timedelta(days=11)) for m,v in gap.items() if v<=0.10}
def datemonth(pub,back=18):
    w=CL[(CL.index>=pub-pd.DateOffset(months=back))&(CL.index<=pub)]
    return pd.Timestamp(w.idxmax().year,w.idxmax().month,1) if len(w) else None
def prop_fast(pct,look,use_hours,use_claims,cpar):
    ev=[]
    for ser,pday in ([(LH,17)]+([(AW,5)] if use_hours else [])):
        mn=ser.rolling(look,min_periods=look).min(); rel_=((ser/mn-1)*100).dropna()
        armed=True
        for m,v in rel_.items():
            if armed and v>=pct: ev.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pday-1),m)); armed=False
            elif not armed and v<pct*0.5: armed=True
    if use_claims:
        armed=True
        for t,v in BELOW.items():
            if armed and v>=cpar: ev.append((t+pd.Timedelta(days=5),pd.Timestamp(t.year,t.month,1))); armed=False
            elif not armed and v<cpar*0.5: armed=True
    ev.sort(); return ev
def make(pct,look,uh,uc,cpar,conf,k,tol,gapm):
    CONF=roll_over(k,tol) if conf=='rollover' else selfclose()
    out_=[]; last=None
    for pub,m in prop_fast(pct,look,uh,uc,cpar):
        hits=[p for mm,p in CONF.items() if m-pd.DateOffset(months=3)<=mm<=m+pd.DateOffset(months=6)]
        if not hits: continue
        pp=max(pub,min(hits)); dd=datemonth(pp)
        if dd is None: continue
        if last is not None and (pp-last).days<gapm*30: continue
        out_.append((pp,dd)); last=pp
    return out_
p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50
VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in vgap2(4,4).index})
G2=vgap2(p['vk'],p['vb']); Vc=dict(name='vac',gap=G2,line=p['vl'],pubs=VPUB)
F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1); C1=[Vc,Hh,SP]; C2=[Hc,SP]
def hubv(sl):
    calls=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=sl:
            w=G2[(G2.index>=m-pd.DateOffset(months=6))&(G2.index<=m)]; hit=w[w>=p['vl']]
            if len(hit):
                kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                calls.append((max(sp,VPUB[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
        elif not armed and v<sl: armed=True
    return calls
LEGS={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
      'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
      'X':[(a,b) for a,b,c in hubv(p['sahm'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')],
      'W':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')],
      'V':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')],
      'B':[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]}
RES=[]
def score(tag,TL):
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(LEGS,TL)
    rows=[]; prem=[]
    for i in range(13):
        c=[x for x in turns if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c:
            lag=(c[0]['published']-me(TR[i])).days
            rows.append((i,lag,(c[0]['date'].year-TR[i].year)*12+c[0]['date'].month-TR[i].month,c[0]['leg']))
            if lag<0: prem.append(TR[i].strftime('%Y-%m'))
    oth=[x for x in turns if x['kind']=='trough' and not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13))]
    r=score13(turns); lg=[x[1] for x in rows]; er=[x[2] for x in rows]
    RES.append(dict(tag=tag,n=len(rows),med=float(np.median(lg)) if lg else 999,worst=max(lg) if lg else 999,
        w31=sum(1 for x in lg if 0<=x<=31),w31b=sum(1 for i,l,e,_ in rows if i>=4 and 0<=l<=31),
        ex=sum(1 for e in er if e==0),w1=sum(1 for e in er if abs(e)<=1),prem=len(prem),oth=len(oth),
        fa=len(r['other']),det=len(r['lags_p']),rows=rows))
score('shipped K J H S',TLH)
for conf in ['rollover','selfclose']:
  for k,tol in ([(1,0.0),(2,0.0),(1,0.1),(2,0.1),(3,0.1)] if conf=='rollover' else [(0,0.0)]):
    for pct in [0.5,1.0,2.0]:
      for look in [12]:
        for uh in [True]:
          for uc,cpar in [(False,0),(True,0.04),(True,0.08)]:
            for gapm in [6]:
              cc=make(pct,look,uh,uc,cpar,conf,k,tol,gapm)
              if not cc: continue
              TL=dict(TLH); TL['Q']=cc
              score(f'{conf} k{k} tol{tol} starts+{pct}/{look}m{" +hrs" if uh else ""}{" +claims"+str(cpar) if uc else ""} gap{gapm}',TL)
ALL=sorted(RES,key=lambda r:(r['prem']>0 or r['oth']>0 or r['fa']>0 or r['n']<13,-r['w31b'],-r['w31'],r['med']))
P(f"configurations {len(RES)}")
P(f"{'w31/13':>7s} {'from1970':>9s} {'closes':>7s} {'med':>5s} {'exact':>6s} {'prem':>5s} {'othcl':>6s} {'FA':>3s}  configuration")
for r in ALL[:18]: P(f"{r['w31']:>7d} {r['w31b']:>9d} {r['n']:>7d} {r['med']:>5.0f} {r['ex']:>6d} {r['prem']:>5d} {r['oth']:>6d} {r['fa']:>3d}  {r['tag']}")
CLEAN=[r for r in RES if r['prem']==0 and r['oth']==0 and r['fa']==0 and r['n']==13 and r['det']==13]
P(f"\nclean: {len(CLEAN)}")
CLEAN.sort(key=lambda r:(-r['w31b'],-r['w31'],r['med'],-r['ex']))
for r in CLEAN[:8]:
    P(f"   w31 {r['w31']}/13 from1970 {r['w31b']}/9 median {r['med']:.0f} exact {r['ex']} | {r['tag']}")
    P("      "+"  ".join(f"{TR[i]:%Y-%m}:{l:+d}/{e:+d}" for i,l,e,_ in r['rows']))
out.close()
