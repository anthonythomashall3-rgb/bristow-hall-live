"""THE CLOSER BUILT FOR SPEED. Target: every close published within a month of the trough month ending. The binding
object today is the vacancy, which is published thirty to forty days after its month; it is dropped from the confirmer
set. What remains is fast enough in principle - aggregate weekly hours arrive on day five of the following month,
housing starts on day seventeen, the paper spread the next day, and weekly claims within five days of the week ending -
so month-T information is all in hand inside thirty-one days of month T ending. The question is whether a rule that
fires that fast can stay clean."""
import sys,itertools
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tfast3.out','w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna(); VR=(-_vload()['-vacancy rate']).dropna()
VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in VR.index})
def _rel(s,look=12): return ((s/s.rolling(look,min_periods=look).min()-1)*100).dropna()
def pub_day(d): return lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=d-1)
FAST=[('weekly hours',_rel(AW),pub_day(5)),('housing starts',_rel(LH),pub_day(17))]
SLOW=[('vacancy rate',_rel(VR),(lambda m: VPUB[m] if m in VPUB.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)))]
ICW=ICfp.dropna(); M4=ICW.rolling(4).mean().dropna(); LGW=np.log(M4)
SVg=SI  # survey-week insured rate level
def prop(drop,minw,falling):
    """weekly initial claims: a fall of `drop` log points from the episode's own four-week-mean peak, optionally
    requiring the latest reading still to be below the one four weeks before. Dated at the month of the low."""
    out_=[]; hi=None
    for k,(tt,v) in enumerate(LGW.items()):
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is None: continue
        if (hi[1]-v)>=drop and (tt-hi[0]).days>=minw*7:
            if falling:
                prev=LGW[LGW.index<=tt-pd.Timedelta(weeks=4)]
                if not len(prev) or v>=prev.iloc[-1]: continue
            seg=LGW[(LGW.index>=hi[0])&(LGW.index<=tt)]; lo=seg.idxmin()
            out_.append((tt+pd.Timedelta(days=5),pd.Timestamp(lo.year,lo.month,1))); hi=None
    return out_
def conf(calls,pct,nmin,useslow,spread_on,fwd):
    objs=FAST+(SLOW if useslow else [])
    outc=[]
    for pp,dd in calls:
        hits=[]
        for nm,rl,pf in objs:
            seg=rl[(rl.index>=dd)&(rl.index<=dd+pd.DateOffset(months=fwd))]; h=seg[seg>=pct]
            if len(h): hits.append(pf(h.index[0]))
        if spread_on:
            sp=GSP[(GSP.index>=dd)&(GSP.index<=dd+pd.DateOffset(months=fwd))]
            h=sp[sp<=round(LINE,3)*0.5]
            if len(h): hits.append(h.index[0]+pd.Timedelta(days=1))
        if len(hits)>=nmin:
            hits.sort(); outc.append((max(pp,hits[nmin-1]),dd))
    return outc
p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50
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

def quick(cc):
    """the closer on its own: per-episode lag, premature closes, closes outside every window - no chronology needed"""
    rows={}; oth=0; prem=0
    for pp,dd in cc:
        k=[i for i in range(13) if TR[i]-pd.DateOffset(months=6)<=dd<=TR[i]+pd.DateOffset(months=12)]
        if not k: oth+=1; continue
        i=k[0]; lag=(pp-me(TR[i])).days
        if lag<0: prem+=1
        if i not in rows: rows[i]=(lag,(dd.year-TR[i].year)*12+dd.month-TR[i].month)
    return rows,prem,oth
CAND=[]
for drop in [0.02,0.03,0.05,0.08,0.10,0.15]:
  for minw in [4,8,13]:
    for falling in [False,True]:
      pr=prop(drop,minw,falling)
      for pct in [0.5,1.0,2.0,3.0,5.0]:
        for nmin in [1,2,3]:
          for useslow in [False,True]:
            for spread_on in [False,True]:
              cc=conf(pr,pct,nmin,useslow,spread_on,6)
              if not cc: continue
              rows,prem,oth=quick(cc)
              # a closer that fires in an expansion is harmless: the chronology only uses a close when an episode is
              # open. Only a close published before its own trough month ended is a fault, and even that is decided by
              # the chronology. So nothing is filtered here; candidates are ranked and the best are run in full.
              CAND.append((len(rows),sum(1 for i,(l,e) in rows.items() if 0<=l<=31),sum(1 for i,(l,e) in rows.items() if i>=4 and 0<=l<=31),
                           rows,f'drop{drop} minw{minw} fall{int(falling)} rise{pct} n{nmin} slow{int(useslow)} spr{int(spread_on)}',cc))
P(f"candidates built: {len(CAND)}")
CAND.sort(key=lambda c:(-c[2],-c[1],-c[0]))
P(f"{'episodes':>8s} {'w31/13':>7s} {'w31 from1961':>13s}  configuration")
for c in CAND[:20]: P(f"{c[0]:>8d} {c[1]:>7d} {c[2]:>13d}  {c[4]}")
P("now the best thirty through the whole chronology")
BEST=[]
def score(tag,TL):
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(LEGS,TL)
    rows=[]; prem=[]
    for i in range(13):
        c=[x for x in turns if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c:
            lag=(c[0]['published']-me(TR[i])).days
            rows.append((i,lag,(c[0]['date'].year-TR[i].year)*12+c[0]['date'].month-TR[i].month))
            if lag<0: prem.append(TR[i].strftime('%Y-%m'))
    oth=[x for x in turns if x['kind']=='trough' and not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13))]
    if len(rows)<13: return None
    r=score13(turns); lg=[x[1] for x in rows]; er=[x[2] for x in rows]
    rec=dict(tag=tag,med=float(np.median(lg)),worst=max(lg),w31=sum(1 for x in lg if x<=31),
             w31b=sum(1 for i,l,e in rows if i>=4 and l<=31),ex=sum(1 for e in er if e==0),
             w1=sum(1 for e in er if abs(e)<=1),prem=len(prem),oth=len(oth),fa=len(r['other']),det=len(r['lags_p']),lags=lg)
    BEST.append(rec); return rec
b=score('shipped K J H S',TLH)
for c in CAND[:30]:
    TL=dict(TLH); TL['Q']=c[6]; score(c[4],TL)
BEST.sort(key=lambda r:(-r['w31b'],-r['w31'],r['med']))
P(f"{'w31/13':>7s} {'from1961':>9s} {'med':>5s} {'worst':>6s} {'exact':>6s} {'w1':>4s} {'prem':>5s} {'othcl':>6s} {'onsets':>7s} {'fa':>3s}  configuration")
for r in BEST[:22]:
    P(f"{r['w31']:>7d} {r['w31b']:>9d} {r['med']:>5.0f} {r['worst']:>6d} {r['ex']:>6d} {r['w1']:>4d} {r['prem']:>5d} {r['oth']:>6d} {r['det']:>5d}/13 {r['fa']:>3d}  {r['tag']}")
    if r['w31b']>=6: P(f"          lags {r['lags']}")
out.close()
