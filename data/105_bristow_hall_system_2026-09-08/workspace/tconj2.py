"""THE CONJUNCTION APPLIED TO THE TROUGH SIDE. Every closer the tool has is a single object crossing a line, and the
two fast ones close before the trough. The onset side's whole strength is that one object proposes and a second
confirms inside a window; the trough side has never been given that structure. Here a claims-side fall PROPOSES the
close and a demand-side recovery CONFIRMS it, and the close is dated at the proposing object's own minimum inside the
episode rather than at its crossing month."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tconj2.out','w')"))
p0=dict(BASE)
G=vgap2(p0['vk'],p0['vb']); VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
Hc,MX=mkpair3(p0['starts'],p0['half'],3,p0['minw']); Hh=mkhours(p0['hrs'],p0['nd'])
ICW=ICfp.dropna(); M4=ICW.rolling(4).mean().dropna(); LGW=np.log(M4)
CCW=pd.read_csv(D+'/CCSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna(); LGC=np.log(CCW.rolling(4).mean().dropna())
def pubof2(cf,t):
    if 'pub_lag_days' in cf: return t+pd.Timedelta(days=cf['pub_lag_days'])
    if 'pubs' in cf: return cf['pubs'][t]
    return pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=cf['pub_day']-1)
REC=[dict(name='vacancy recovered',gap=G,line=p0['vl'],pubs=VPUB),
     dict(name='housing pair recovered',gap=Hc['gap'],line=Hc['line'],pub_day=Hc.get('pub_day',18)),
     dict(name='spread narrowed',gap=GSP,line=round(LINE,3),pub_lag_days=1),
     dict(name='hours pair recovered',gap=Hh['gap'],line=Hh['line'],pub_day=Hh.get('pub_day',5))]
def prop_weekly(drop,pub=5,minw=8):
    """weekly initial claims: the episode's own four-week-mean peak, then a fall of `drop` log points from it.
    Dated at the month of the LOW seen so far, which is known on the day the proposal is made."""
    out_=[]; hi=None
    for tt,v in LGW.items():
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is not None and (hi[1]-v)>=drop and (tt-hi[0]).days>=minw*7:
            seg=LGW[(LGW.index>=hi[0])&(LGW.index<=tt)]; lo=seg.idxmin()
            out_.append((tt+pd.Timedelta(days=pub),pd.Timestamp(lo.year,lo.month,1))); hi=None
    return out_
def prop_cont(drop,pub=5,minw=8):
    out_=[]; hi=None
    for tt,v in LGC.items():
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is not None and (hi[1]-v)>=drop and (tt-hi[0]).days>=minw*7:
            seg=LGC[(LGC.index>=hi[0])&(LGC.index<=tt)]; lo=seg.idxmin()
            out_.append((tt+pd.Timedelta(days=pub),pd.Timestamp(lo.year,lo.month,1))); hi=None
    return out_
def prop_survey(drop,pub=12):
    out_=[]; hi=None
    for tt,v in SI.items():
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is not None and (hi[1]-v)>=drop:
            seg=SI[(SI.index>=hi[0])&(SI.index<=tt)]; out_.append((SW[tt]+pd.Timedelta(days=pub),seg.idxmin())); hi=None
    return out_
def confirm_t(calls,retrace,back=0,fwd=6):
    """A close is confirmed when a demand object has RETRACED a stated fraction of its own deterioration: it must have
    come down from its worst reading of the last eighteen months by `retrace` of the distance between that worst
    reading and its line. Being below the line is not enough - during a recession several of these objects are below
    their lines already, which is why the level test confirms everything and vetoes nothing."""
    outc=[]
    for pp,dd in calls:
        best=None
        for cf in REC:
            ser=cf['gap']
            wors=ser[(ser.index>=dd-pd.DateOffset(months=18))&(ser.index<=dd)]
            if not len(wors): continue
            mx=wors.max()
            if mx<=cf['line']: continue                      # never deteriorated: it cannot recover
            target=mx-(mx-cf['line'])*retrace
            seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]
            hit=seg[seg<=target]
            if not len(hit): continue
            tt=hit.index[0]; ps=pubof2(cf,tt)
            if best is None or ps<best[0]: best=(ps,cf['name'])
        if best: outc.append((max(pp,best[0]),dd,best[1]))
    return outc
def score(nm,TL):
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50
    G2=vgap2(p['vk'],p['vb']); pubs=VPUB; Vc=dict(name='vac',gap=G2,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1); C1=[Vc,Hh,SP]; C2=[Hc,SP]
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G2[(G2.index>=m-pd.DateOffset(months=6))&(G2.index<=m)]; hit=w[w>=p['vl']]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')],
          'W':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')],
          'V':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')],
          'B':[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    rows=[]; prem=0; PREMDET=[]
    for i in range(13):
        c=[x for x in turns if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c:
            lag=(c[0]['published']-me(TR[i])).days
            rows.append((i,lag,(c[0]['date'].year-TR[i].year)*12+c[0]['date'].month-TR[i].month,c[0]['leg']))
            if lag<0: prem+=1; PREMDET.append((TR[i].strftime('%Y-%m'),c[0]['published'].strftime('%Y-%m-%d'),c[0]['leg']))
    oth=[x for x in turns if x['kind']=='trough' and not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13))]
    if not rows: P(f"{nm:50s} no closes"); return
    lg=[x[1] for x in rows]; er=[x[2] for x in rows]
    r=score13(turns)
    P(f"{nm:50s} closed {len(rows):2d}/13 median {np.median(lg):5.0f} mean {np.mean(lg):5.0f} worst {max(lg):4d} exact {sum(1 for e in er if e==0):2d} w1 {sum(1 for e in er if abs(e)<=1):2d} PREMATURE {prem}{PREMDET if prem else ''} other {len(oth)} | onsets {len(r['lags_p'])}/13 falsealarm {len(r['other'])}")
    return rows
P("the shipped closers, for reference"); score('  K J H S as shipped',TLH)
P("\nweekly initial claims proposing, a demand recovery confirming")
for d in [0.20,0.15,0.12,0.10,0.08,0.06]:
    for fr in [1.0,0.9,0.75,0.6]:
        TL=dict(TLH); TL['Q']=[(a,b) for a,b,c in confirm_t(prop_weekly(d),fr)]
        score(f'  claims drop {d} retrace {fr:.2f}',TL)
P("\nsurvey-week insured rate proposing, a demand recovery confirming")
for d in [1.0,0.8,0.6,0.5,0.4]:
    for fr in [1.0,0.9,0.75,0.6]:
        TL=dict(TLH); TL['R']=[(a,b) for a,b,c in confirm_t(prop_survey(d),fr)]
        score(f'  survey-week fall {d} retrace {fr:.2f}',TL)
out.close()
