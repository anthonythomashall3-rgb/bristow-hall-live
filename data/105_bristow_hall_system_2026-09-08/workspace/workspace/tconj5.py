"""RECOVERY MEASURED AS A RISE FROM THE LOW, NOT A RETRACE OF A GAP. The gap formulation cannot use an object that
never crossed its line on the way in, and in most episodes the housing pair and the hours pair never do - so only the
vacancy and the paper spread can ever confirm a close, and the vacancy is the slow one. The natural mirror of the
onset side is instead: on the way in a demand object FALLS; on the way out it RISES from its own low. Housing starts,
aggregate weekly hours, the vacancy rate and the paper spread are all built that way here and swept."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tconj5.out','w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna(); VR=(-_vload()['-vacancy rate']).dropna()
P(f"levels for the recovery objects: housing starts {LH.index.min():%Y-%m}..{LH.index.max():%Y-%m}, hours {AW.index.min():%Y-%m}..{AW.index.max():%Y-%m}, vacancy {VR.index.min():%Y-%m}..{VR.index.max():%Y-%m}")
def rise_from_low(ser,pct,look=12,pubday=None,pubs=None,pct_of_level=True):
    """the month the series stands `pct` per cent above its own trailing-12-month minimum; published on its own clock"""
    mn=ser.rolling(look,min_periods=look).min()
    rel_=((ser/mn-1)*100).dropna()
    out_={}
    for m,v in rel_.items():
        if v>=pct: out_[m]=True
    def pub(m):
        if pubs is not None and m in pubs.index: return pubs[m]
        return pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=(pubday or 18)-1)
    return rel_, pub
VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in VR.index})
RECOV=[('housing starts',*rise_from_low(LH,0,pubday=18)),('weekly hours',*rise_from_low(AW,0,pubday=5)),
       ('vacancy rate',*rise_from_low(VR,0,pubs=VPUB))]
SPN=(-GSP)  # the spread narrowing: the negative of the widening gap
ICW=ICfp.dropna(); LGW=np.log(ICW.rolling(4).mean().dropna())
def prop_weekly(drop,pub=5,minw=8,dating='low',settle=0):
    """dating: 'low' - the month of the four-week mean's own minimum since the episode peak; 'settled' - the same but
    ignoring the last `settle` weeks, so the low has been established rather than just printed; 'cross' - the month
    the fall crossed the drop."""
    out_=[]; hi=None
    for tt,v in LGW.items():
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is not None and (hi[1]-v)>=drop and (tt-hi[0]).days>=minw*7:
            if dating=='cross': dd=pd.Timestamp(tt.year,tt.month,1)
            else:
                end=tt-pd.Timedelta(weeks=settle) if dating=='settled' else tt
                seg=LGW[(LGW.index>=hi[0])&(LGW.index<=end)]
                if not len(seg): seg=LGW[(LGW.index>=hi[0])&(LGW.index<=tt)]
                lo=seg.idxmin(); dd=pd.Timestamp(lo.year,lo.month,1)
            out_.append((tt+pd.Timedelta(days=pub),dd)); hi=None
    return out_
def confirm_r(calls,pct,nmin=1,back=0,fwd=6):
    outc=[]
    for pp,dd in calls:
        hits=[]
        for nm,rel_,pub in RECOV:
            seg=rel_[(rel_.index>=dd-pd.DateOffset(months=back))&(rel_.index<=dd+pd.DateOffset(months=fwd))]
            h=seg[seg>=pct]
            if len(h): hits.append((pub(h.index[0]),nm))
        sp=GSP[(GSP.index>=dd-pd.Timedelta(days=30))&(GSP.index<=dd+pd.DateOffset(months=fwd))]
        if len(sp):
            h=sp[sp<=round(LINE,3)*0.5]
            if len(h): hits.append((h.index[0]+pd.Timedelta(days=1),'spread back'))
        if len(hits)>=nmin:
            hits.sort(); outc.append((max(pp,hits[nmin-1][0]),dd,hits[nmin-1][1]))
    return outc
def score(nm,TL):
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
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')],
          'W':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')],
          'V':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')],
          'B':[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    rows=[]; prem=[]
    for i in range(13):
        c=[x for x in turns if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c:
            lag=(c[0]['published']-me(TR[i])).days
            rows.append((i,lag,(c[0]['date'].year-TR[i].year)*12+c[0]['date'].month-TR[i].month,c[0]['leg']))
            if lag<0: prem.append(TR[i].strftime('%Y-%m'))
    oth=[x for x in turns if x['kind']=='trough' and not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13))]
    if not rows: P(f"{nm:46s} no closes"); return None
    lg=[x[1] for x in rows]; er=[x[2] for x in rows]; r=score13(turns)
    P(f"{nm:46s} closed {len(rows):2d}/13 med {np.median(lg):5.0f} mean {np.mean(lg):5.0f} worst {max(lg):4d} exact {sum(1 for e in er if e==0):2d} w1 {sum(1 for e in er if abs(e)<=1):2d} PREM {len(prem)}{prem if prem else ''} othercl {len(oth)} | onsets {len(r['lags_p'])}/13 fa {len(r['other'])}")
    return rows
P("\nreference"); score('  K J H S as shipped',TLH)
P("\nthe clean corner (two recovery objects, five per cent) under three ways of dating the close")
for dating,settle in [('low',0),('settled',8),('settled',13),('cross',0)]:
    for d in [0.15,0.12,0.10]:
        TL=dict(TLH); TL['Q']=[(a,b) for a,b,c in confirm_r(prop_weekly(d,dating=dating,settle=settle),5.0,2)]
        score(f'  drop {d} dating {dating}{settle if settle else ""}',TL)
out.close()
