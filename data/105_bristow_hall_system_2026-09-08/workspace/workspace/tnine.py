"""THE TWO-ROUTE CLOSER, BUILT FROM THE FLOOR MEASUREMENT. Housing starts stand above their own low inside the month
at seven of the nine troughs the instrument reaches; the claims flow covers the other two, 1991 and 2020. So the close
has two routes and one dating rule: it is PUBLISHED when either route fires, and DATED at the month the claims
four-week mean peaked, which is what a trough is and which is known on the day of publication."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tnine.out','w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna()
CL=ICfp.dropna().rolling(4).mean().dropna(); LCL=np.log(CL)
MXC=LCL.rolling(52,min_periods=26).max(); BELOW=(MXC-LCL).dropna()
def datemonth(pub,back=18):
    w=CL[(CL.index>=pub-pd.DateOffset(months=back))&(CL.index<=pub)]
    if not len(w): return None
    lo=w.idxmax(); return pd.Timestamp(lo.year,lo.month,1)
def route_demand(ser,pday,pct,look):
    mn=ser.rolling(look,min_periods=look).min(); rel_=((ser/mn-1)*100).dropna()
    out_=[]; armed=True
    for m,v in rel_.items():
        if armed and v>=pct:
            out_.append(pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pday-1)); armed=False
        elif not armed and v<pct*0.5: armed=True
    return out_
def route_claims(kind,par):
    out_=[]
    if kind=='runs':
        run=0; prev=None
        for t,v in CL.items():
            if prev is not None and v<prev: run+=1
            else: run=0
            prev=v
            if run>=par: out_.append(t+pd.Timedelta(days=5)); run=0
    else:
        armed=True
        for t,v in BELOW.items():
            if armed and v>=par: out_.append(t+pd.Timedelta(days=5)); armed=False
            elif not armed and v<par*0.5: armed=True
    return out_
def build_closer(pct,look,use_hours,ckind,cpar,guard,gap_months=6):
    pubs=route_demand(LH,17,pct,look)
    if use_hours: pubs=pubs+route_demand(AW,5,pct,look)
    pubs=pubs+route_claims(ckind,cpar)
    pubs=sorted(set(pubs))
    out_=[]; last=None
    for pub in pubs:
        b=BELOW[BELOW.index<=pub]
        if len(b) and b.iloc[-1]<guard: continue      # the claims flow must already be off its own peak
        dd=datemonth(pub)
        if dd is None: continue
        if last is not None and (pub-last).days<gap_months*30: continue
        out_.append((pub,dd)); last=pub
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
    rec=dict(tag=tag,n=len(rows),med=float(np.median(lg)) if lg else 999,worst=max(lg) if lg else 999,
             w31=sum(1 for x in lg if 0<=x<=31),w31b=sum(1 for i,l,e,_ in rows if i>=4 and 0<=l<=31),
             ex=sum(1 for e in er if e==0),w1=sum(1 for e in er if abs(e)<=1),prem=len(prem),oth=len(oth),
             fa=len(r['other']),det=len(r['lags_p']),rows=rows,lags=lg)
    RES.append(rec); return rec
b=score('shipped K J H S',TLH)
P(f"shipped: within the month {b['w31']}/13 (from 1970 {b['w31b']}/9), median {b['med']:.0f}, exact {b['ex']}")
for pct in [0.5,1.0,2.0]:
  for look in [12,18]:
    for uh in [False,True]:
      for ckind,cpar in [('runs',3),('runs',4),('below',0.02),('below',0.04),('below',0.06)]:
        for guard in [0.0,0.02,0.05]:
          for gapm in [4,6,9]:
            cc=build_closer(pct,look,uh,ckind,cpar,guard,gapm)
            if not cc: continue
            TL=dict(TLH); TL['Q']=cc
            score(f'starts+{pct}%/{look}m{" +hours" if uh else ""}, claims {ckind} {cpar}, guard {guard}, gap {gapm}m',TL)
CLEAN=[r for r in RES if r['prem']==0 and r['oth']==0 and r['fa']==0 and r['det']==13 and r['n']==13]
CLEAN.sort(key=lambda r:(-r['w31b'],-r['w31'],r['med'],-r['ex']))
P(f"configurations run {len(RES)}; clean (13 closes, none premature, none outside a window, onset side untouched) {len(CLEAN)}")
P(f"{'w31/13':>7s} {'from1970':>9s} {'med':>5s} {'worst':>6s} {'exact':>6s} {'w1':>4s}  configuration")
for r in CLEAN[:15]: P(f"{r['w31']:>7d} {r['w31b']:>9d} {r['med']:>5.0f} {r['worst']:>6d} {r['ex']:>6d} {r['w1']:>4d}  {r['tag']}")
if CLEAN:
    t=CLEAN[0]; P(f"\nbest: {t['tag']}")
    for i,l,e,leg in t['rows']: P(f"   {TR[i]:%Y-%m}  lag {l:+5d}  date error {e:+d}  by {leg}")
out.close()
