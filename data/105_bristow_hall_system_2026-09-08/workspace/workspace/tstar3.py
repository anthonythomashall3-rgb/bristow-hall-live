"""THE CLOSER BUILT ON WHAT THE FLOOR MEASUREMENT SHOWS. Housing starts stand one per cent above their own twelve-month
minimum IN the trough month itself in seven of the nine episodes the instrument can reach, and that reading is
published on day seventeen of the following month - inside a month of the trough month ending. Starts turn before the
trough; claims turn before it too. So the close is built as: a demand object standing above its own twelve-month low
PROPOSES, the claims flow already off its own peak CONFIRMS, and the close is dated at the demand object's own low."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tstar3.out','w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna(); VR=(-_vload()['-vacancy rate']).dropna()
VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in VR.index})
CL=ICfp.dropna().rolling(4).mean().dropna(); LCL=np.log(CL)
OBJ={'starts':(LH,17),'hours':(AW,5)}
def closer(pct,look,claimdrop,which,minmonths=3):
    """which: 'starts', 'hours' or 'both' (either may propose). The claims condition is measured on the day the
    demand reading is published, using the four-week mean's distance below its own 52-week maximum."""
    mxc=LCL.rolling(52,min_periods=26).max(); belowc=(mxc-LCL).dropna()
    out_=[]
    for nm in (['starts','hours'] if which=='both' else [which]):
        ser,pday=OBJ[nm]
        mn=ser.rolling(look,min_periods=look).min(); rel_=((ser/mn-1)*100).dropna()
        armed=True; lastfire=None
        for m,v in rel_.items():
            if armed and v>=pct:
                pub=pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pday-1)
                seg=belowc[belowc.index<=pub]
                if len(seg) and seg.iloc[-1]<claimdrop: continue   # before 1967 there is no claims series to test
                w=ser[(ser.index>=m-pd.DateOffset(months=look))&(ser.index<=m)]
                lo=w.idxmin()
                if lastfire is not None and (m-lastfire).days<minmonths*30: continue
                out_.append((pub,pd.Timestamp(lo.year,lo.month,1))); armed=False; lastfire=m
            elif not armed and v<pct*0.5: armed=True
    out_.sort(); return out_
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
    if len(rows)<13: return None
    r=score13(turns); lg=[x[1] for x in rows]; er=[x[2] for x in rows]
    rec=dict(tag=tag,med=float(np.median(lg)),worst=max(lg),w31=sum(1 for x in lg if 0<=x<=31),
             w31b=sum(1 for i,l,e,_ in rows if i>=4 and 0<=l<=31),ex=sum(1 for e in er if e==0),
             w1=sum(1 for e in er if abs(e)<=1),prem=len(prem),oth=len(oth),fa=len(r['other']),det=len(r['lags_p']),
             lags=lg,rows=rows)
    RES.append(rec); return rec
score('shipped K J H S',TLH)
for which in ['starts','both']:
    cc=closer(1.0,12,0.05,which)
    P(f"diagnostic: {which} +1% over 12m low, claims 0.05 off peak -> {len(cc)} calls; in trough windows: "+str([f"{p:%Y-%m-%d}/{d:%Y-%m}" for p,d in cc if any(TR[i]-pd.DateOffset(months=6)<=d<=TR[i]+pd.DateOffset(months=12) for i in range(13))][:14]))
for which in ['starts','hours','both']:
  for pct in [0.5,1.0,2.0,3.0]:
    for look in [12,18,24]:
      for cd in [0.02,0.05,0.10,0.15,0.20]:
        cc=closer(pct,look,cd,which)
        if not cc:
            P(f"   empty: {which} {pct} {look} {cd}"); continue
        TL=dict(TLH); TL['Q']=cc
        try:
            r=score(f'{which} +{pct}% over {look}m low, claims {cd} off peak',TL)
            if r is None: P(f"   short: {which} {pct} {look} {cd} closes {len(RES[-1]['rows'])}")
        except Exception as e:
            P(f"   ERROR {which} {pct} {look} {cd}: {type(e).__name__} {e}")
CLEAN=[r for r in RES if r['prem']==0 and r['oth']==0 and r['fa']==0 and r['det']==13]
CLEAN.sort(key=lambda r:(-r['w31b'],-r['w31'],r['med'],-r['ex']))
P(f"configurations run {len(RES)}, of which clean (no premature close, none outside a window, onset side untouched): {len(CLEAN)}")
P(f"{'w31/13':>7s} {'from1961':>9s} {'med':>5s} {'worst':>6s} {'exact':>6s} {'w1':>4s}  configuration")
for r in CLEAN[:18]:
    P(f"{r['w31']:>7d} {r['w31b']:>9d} {r['med']:>5.0f} {r['worst']:>6d} {r['ex']:>6d} {r['w1']:>4d}  {r['tag']}")
if CLEAN:
    b=CLEAN[0]; P(f"\nbest: {b['tag']}")
    for i,l,e,leg in b['rows']: P(f"   {TR[i]:%Y-%m}  lag {l:+5d}  date error {e:+d}  by {leg}")
out.close()
