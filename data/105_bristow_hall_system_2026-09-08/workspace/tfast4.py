"""THE CLOSER BUILT FOR SPEED. Target: every close published within a month of the trough month ending. The binding
object today is the vacancy, which is published thirty to forty days after its month; it is dropped from the confirmer
set. What remains is fast enough in principle - aggregate weekly hours arrive on day five of the following month,
housing starts on day seventeen, the paper spread the next day, and weekly claims within five days of the week ending -
so month-T information is all in hand inside thirty-one days of month T ending. The question is whether a rule that
fires that fast can stay clean."""
import sys,itertools
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tfast4.out','w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna(); VR=(-_vload()['-vacancy rate']).dropna()
VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in VR.index})
def _rel(s,look=12): return ((s/s.rolling(look,min_periods=look).min()-1)*100).dropna()
def pub_day(d): return lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=d-1)
FAST=[('weekly hours',_rel(AW),pub_day(5)),('housing starts',_rel(LH),pub_day(17))]
SLOW=[('vacancy rate',_rel(VR),(lambda m: VPUB[m] if m in VPUB.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)))]
ICW=ICfp.dropna(); M4=ICW.rolling(4).mean().dropna(); LGW=np.log(M4)
SVg=SI  # survey-week insured rate level

def prop_demand(pct,which,look=12):
    """DEMAND PROPOSES THE CLOSE. On the way in a supply object proposes and a demand object confirms; on the way out
    the fast object is the demand one - aggregate weekly hours arrive on day five of the following month and housing
    starts on day seventeen - so demand proposes and the claims flow confirms. Dated at the month of the object's own
    twelve-month low."""
    objs={'hours':(AW,5),'starts':(LH,17),'either':None}[which] if which!='either' else None
    src=[(AW,5),(LH,17)] if which=='either' else [objs]
    out_=[]
    for ser,pd_ in src:
        mn=ser.rolling(look,min_periods=look).min(); rel_=((ser/mn-1)*100).dropna()
        armed=True
        for m,v in rel_.items():
            if armed and v>=pct:
                seg=ser[(ser.index>=m-pd.DateOffset(months=look))&(ser.index<=m)]
                lo=seg.idxmin()
                out_.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pd_-1),pd.Timestamp(lo.year,lo.month,1)))
                armed=False
            elif not armed and v<pct*0.5: armed=True
    out_.sort(); return out_
CLM=np.log(ICfp.dropna().rolling(4).mean().dropna())
SVL=SI
def conf_supply(calls,drop,use_survey,svdrop,fwd=6):
    """the claims flow confirms: the four-week mean stands `drop` log points below its own maximum of the last twelve
    months, published five days after the week ends; optionally the survey-week insured rate the same way"""
    mx=CLM.rolling(52,min_periods=26).max()
    below=(mx-CLM).dropna()
    smx=SVL.rolling(12,min_periods=6).max(); sbelow=(smx-SVL).dropna()
    outc=[]
    for pp,dd in calls:
        hits=[]
        seg=below[(below.index>=dd)&(below.index<=dd+pd.DateOffset(months=fwd))]
        h=seg[seg>=drop]
        if len(h): hits.append(h.index[0]+pd.Timedelta(days=5))
        if use_survey:
            seg2=sbelow[(sbelow.index>=dd)&(sbelow.index<=dd+pd.DateOffset(months=fwd))]
            h2=seg2[seg2>=svdrop]
            if len(h2): hits.append(SW[h2.index[0]]+pd.Timedelta(days=12))
        if hits: outc.append((max(pp,min(hits)),dd))
    return outc
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
for which in ['hours','starts','either']:
  for pct in [0.5,1.0,2.0,3.0,5.0]:
    pr=prop_demand(pct,which)
    for drop in [0.02,0.04,0.06,0.10,0.15]:
      for usesv in [False,True]:
        for svdrop in ([0.2,0.4] if usesv else [0.0]):
          cc=conf_supply(pr,drop,usesv,svdrop)
          if not cc: continue
          rows,prem,oth=quick(cc)
          CAND.append((len(rows),sum(1 for i,(l,e) in rows.items() if 0<=l<=31),sum(1 for i,(l,e) in rows.items() if i>=4 and 0<=l<=31),
                       rows,f'{which} rise{pct} claims-drop{drop} survey{int(usesv)}/{svdrop}',cc))
P(f"candidates built: {len(CAND)}")
CAND.sort(key=lambda c:(-c[2],-c[1],-c[0]))
P(f"{'episodes':>8s} {'w31/13':>7s} {'from1961':>9s}  configuration")
for c in CAND[:15]: P(f"{c[0]:>8d} {c[1]:>7d} {c[2]:>9d}  {c[4]}")
P("through the whole chronology")
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
    BEST.append(dict(tag=tag,med=float(np.median(lg)),worst=max(lg),w31=sum(1 for x in lg if x<=31),
             w31b=sum(1 for i,l,e in rows if i>=4 and l<=31),ex=sum(1 for e in er if e==0),
             w1=sum(1 for e in er if abs(e)<=1),prem=len(prem),oth=len(oth),fa=len(r['other']),det=len(r['lags_p']),lags=lg))
score('shipped K J H S',TLH)
for c in CAND[:30]:
    TL=dict(TLH); TL['Q']=c[6]; score(c[4],TL)
BEST.sort(key=lambda r:(r['prem']>0,r['fa']>0,-r['w31b'],-r['w31'],r['med']))
P(f"{'w31/13':>7s} {'from1961':>9s} {'med':>5s} {'worst':>6s} {'exact':>6s} {'w1':>4s} {'prem':>5s} {'othcl':>6s} {'onsets':>7s} {'fa':>3s}  configuration")
for r in BEST[:20]:
    P(f"{r['w31']:>7d} {r['w31b']:>9d} {r['med']:>5.0f} {r['worst']:>6d} {r['ex']:>6d} {r['w1']:>4d} {r['prem']:>5d} {r['oth']:>6d} {r['det']:>5d}/13 {r['fa']:>3d}  {r['tag']}")
    if r['w31b']>=5: P(f"          lags {r['lags']}")
out.close()
