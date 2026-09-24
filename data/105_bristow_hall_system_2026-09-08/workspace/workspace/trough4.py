"""THE TROUGH SIDE, WITH THE COMMITTEE'S REAL ANNOUNCEMENT DATES AND TWO FASTER CLOSERS. Correction first: the trough
announcement dates used in trough3 were invented for every episode before 1980, and the July 1980 trough was recorded a
year early. The committee's dating committee was formed in 1978 and its announcement dates begin with the June 1980
peak announcement, so the comparison runs from 1980 only. Then two closers the tool has never had: the drop in WEEKLY
initial claims (the mirror of the monthly closer H, which is what actually does the work) and the fall in the
survey-week insured rate."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('trough4.out','w')"))
NBERT={'1980-07':'1981-07-08','1982-11':'1983-07-08','1991-03':'1992-12-22','2001-11':'2003-07-17',
       'the committee published no trough announcement dates before 1980':None,
       '2009-06':'2010-09-20','2020-04':'2021-07-19','2024-08':None}
ICW=ICfp.dropna()
P(f"weekly initial claims for the closer: {ICW.index.min():%Y-%m-%d} to {ICW.index.max():%Y-%m-%d}, {len(ICW)} weeks")
def close_weekly(drop,pub=5,minw=8):
    """the episode's own weekly peak, then a fall of `drop` log points from it; dated the month of the low"""
    lg=np.log(ICW.rolling(4).mean().dropna()); out_=[]
    hi=None; hit=None
    for tt,v in lg.items():
        if hi is None or v>hi[1]: hi=(tt,v); hit=None
        if hi is not None and (hi[1]-v)>=drop and (tt-hi[0]).days>=minw*7:
            lowm=lg[(lg.index>=hi[0])&(lg.index<=tt)]
            out_.append((tt+pd.Timedelta(days=pub),pd.Timestamp(lowm.idxmin().year,lowm.idxmin().month,1) if False else pd.Timestamp(tt.year,tt.month,1)))
            hi=None
    return out_
def close_survey(drop,pub=12):
    """the episode's own survey-week peak in the insured rate, then a fall of `drop` points from it"""
    out_=[]; hi=None
    for tt,v in SI.items():
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is not None and (hi[1]-v)>=drop:
            out_.append((SW[tt]+pd.Timedelta(days=pub),tt)); hi=None
    return out_
def rep(nm,TL):
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1); C1=[Vc,Hh,SP]; C2=[Hc,SP]
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=p['vl']]
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
    r=score13(turns)
    rows=[]
    for i in range(13):
        cand=[x for x in turns if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if cand: rows.append((i,(cand[0]['published']-me(TR[i])).days,(cand[0]['date'].year-TR[i].year)*12+cand[0]['date'].month-TR[i].month,cand[0]['leg']))
    lg=[x[1] for x in rows]; er=[x[2] for x in rows]
    allt=[x for x in turns if x['kind']=='trough']
    oth=[x for x in allt if not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13))]
    onl=[r['lags_p'].get(i) for i in range(13)]
    P(f"{nm:44s} closed {len(rows)}/13 median {np.median(lg):5.0f} mean {np.mean(lg):5.0f} worst {max(lg):4d} exact {sum(1 for e in er if e==0):2d} w1 {sum(1 for e in er if abs(e)<=1):2d} EARLY {sum(1 for e in er if e<0):2d} other closes {len(oth)} | onsets ok {len(r['lags_p'])==13} others {len(r['other'])}")
    return rows
P("\nthe closers as shipped")
rep('v3.6 as shipped (K J H S)',TLH)
P("\nwith the weekly initial-claims closer added, drop swept")
for d in [0.20,0.15,0.12,0.10,0.08,0.06]:
    TL=dict(TLH); TL['Q']=close_weekly(d); rep(f'  weekly initial claims drop {d}',TL)
P("\nwith the survey-week insured-rate closer added, drop swept")
for d in [1.2,1.0,0.8,0.6,0.5,0.4]:
    TL=dict(TLH); TL['R']=close_survey(d); rep(f'  survey-week rate falls {d} points',TL)
out.close()
