"""THE DURATION GATE. Housing starts and the claims flow lead the trough, so used alone they close four to six months
early. But every one of those early closes lands only a few months after the tool opened the episode, and every good
one lands eight to ten months in. The gate is therefore the tool's own state, which it knows without any new data: a
close is not accepted until the episode has been open D months. Fast object for speed, the tool's own clock for safety."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tgrad.out','w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna()
CL=ICfp.dropna().rolling(4).mean().dropna(); LCL=np.log(CL); BELOW=(LCL.rolling(52,min_periods=26).max()-LCL).dropna()
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
OPENS=sorted(set(a for v in LEGS.values() for a,b in v))
def last_open(t):
    prev=[o for o in OPENS if o<=t]
    return prev[-1] if prev else None
def evidence_dates(pct,look,cpar):
    """each object's own recovery date, kept separate so the number agreeing can be counted"""
    out_={}
    for nm,ser,pday in [('starts',LH,17),('hours',AW,5)]:
        mn=ser.rolling(look,min_periods=look).min(); rel_=((ser/mn-1)*100).dropna()
        out_[nm]=sorted(pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pday-1) for m,v in rel_.items() if v>=pct)
    out_['claims']=sorted(t+pd.Timedelta(days=5) for t,v in BELOW.items() if v>=cpar)
    return out_
def datemonth(pub,back=18):
    w=CL[(CL.index>=pub-pd.DateOffset(months=back))&(CL.index<=pub)]
    return pd.Timestamp(w.idxmax().year,w.idxmax().month,1) if len(w) else None
def make_graded(pct,look,cpar,d1,d2,d3):
    """GRADED EVIDENCE: the earlier the tool wants to close, the more objects must agree. Before d1 months open no
    close is accepted at all; between d1 and d2 all three objects must have turned; between d2 and d3, two; after d3,
    one. The tool's own clock is the only extra input and it needs no new data."""
    EV=evidence_dates(pct,look,cpar); allev=sorted(set(x for v in EV.values() for x in v))
    out_=[]; used=set()
    for pub in allev:
        o=last_open(pub)
        if o is None or o in used: continue
        months=(pub-o).days/30.4
        if months<d1: continue
        need=3 if months<d2 else (2 if months<d3 else 1)
        agree=sum(1 for nm,v in EV.items() if any(x<=pub for x in v if x>=o))
        if agree<need: continue
        dd=datemonth(pub)
        if dd is None or dd<o-pd.DateOffset(months=12): continue
        out_.append((pub,dd)); used.add(o)
    return out_
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
    RES.append(dict(tag=tag,n=len(rows),med=float(np.median(lg)) if lg else 999,
        w31=sum(1 for x in lg if 0<=x<=31),w31b=sum(1 for i,l,e,_ in rows if i>=4 and 0<=l<=31),
        ex=sum(1 for e in er if e==0),w1=sum(1 for e in er if abs(e)<=1),prem=len(prem),oth=len(oth),
        fa=len(r['other']),det=len(r['lags_p']),rows=rows))
score('shipped K J H S',TLH)
for pct in [0.5,1.0,2.0,3.0]:
  for look in [12,18]:
    for cpar in [0.02,0.04,0.08]:
      for d1,d2,d3 in [(2,4,8),(2,5,9),(3,5,8),(3,6,9),(4,6,10),(2,6,12),(3,7,11)]:
        cc=make_graded(pct,look,cpar,d1,d2,d3)
        if not cc: continue
        TL=dict(TLH); TL['Q']=cc
        score(f'{pct}%/{look}m claims{cpar} graded {d1}/{d2}/{d3}',TL)
CLEAN=[r for r in RES if r['prem']==0 and r['oth']==0 and r['fa']==0 and r['n']==13 and r['det']==13]
CLEAN.sort(key=lambda r:(-r['w31b'],-r['w31'],r['med'],-r['ex']))
P(f"configurations {len(RES)}; clean {len(CLEAN)}")
P(f"{'w31/13':>7s} {'from1970':>9s} {'med':>5s} {'exact':>6s} {'w1':>4s}  configuration")
for r in CLEAN[:12]: P(f"{r['w31']:>7d} {r['w31b']:>9d} {r['med']:>5.0f} {r['ex']:>6d} {r['w1']:>4d}  {r['tag']}")
for r in CLEAN[:3]:
    P(f"\n   {r['tag']}")
    for i,l,e,leg in r['rows']: P(f"      {TR[i]:%Y-%m}  lag {l:+5d}  err {e:+d}  by {leg}")
out.close()
