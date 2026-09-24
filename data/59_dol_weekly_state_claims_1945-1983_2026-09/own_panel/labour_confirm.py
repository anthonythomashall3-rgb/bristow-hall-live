"""THE OWED EXPERIMENT (5 September 2026, night): can the claims legs keep their speed if only the LABOUR-SUPPLY objects confirm them?
Under Paper 1's chronology (onset April 2024, end August 2024) the route's 2023 call is a false alarm and 2024 a miss, because the
vacancy rate confirmed leg C's July 2023 proposal and no claims leg proposes in 2024.  Here the confirmer set is varied with every
line frozen and nothing re-chosen: Sahm 0.50 on first prints and the insured rate's gap at 0.50 (leg U's own object, exact tenths,
published 5 days after its week - the route's convention) are the labour-supply confirmers; the vacancy rate, the housing pair and
the hours pair are the demand-side ones.  Scored on THIRTEEN turns (the twelve committee turns and Paper 1's 2024), with the hazard
as first factor x window exposure of the confirmer union, exact arithmetic.  CLAIMS_FIELD=HYB so every leg runs to July 2026."""
exec(open('dominance.py').read().split('rows=[]')[0])
PK13=PK+[pd.Timestamp('2024-04-01')]; TR13=TR+[pd.Timestamp('2024-08-01')]
_i=pd.read_csv(shim.W+'/archive/data/fred/IURSA.csv'); _i.columns=['d','v']; _i['d']=pd.to_datetime(_i['d']); s_iur=_i.set_index('d')['v'].astype(float).dropna()
x=s_iur.rolling(1).mean(); IURG=(x-x.rolling(52,min_periods=52).min().shift(1)).round(9).dropna()
CONF['U']=dict(name='IUR gap 0.50',gap=IURG,line=0.50,pub_day=5,pub_lag_days=5)
HS['U']=hits(IURG.resample('MS').max(),0.50)
def onsets13(legs,conf,tl=('K','J','H','S','T')):
    sec=[CONF[c] for c in conf if c!='S']; sahm=g if 'S' in conf else None
    with contextlib.redirect_stdout(io.StringIO()):
        if conf: t=B.american_chronology({q:PLU[q] for q in legs},{q:TLG[q] for q in tl},sahm=sahm,line=0.5,second=sec if sec else None,horizon_months=4,back_months=6)
        else:    t=B.american_chronology({q:PLU[q] for q in legs},{q:TLG[q] for q in tl})
    return [(o['published'],o['date'],o['leg'],o.get('condition')) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')],t
def rec13(on):
    lags={}; other=[]
    for pub,d,leg,cond in on:
        hit=None
        for i,(p,q) in enumerate(zip(PK13,TR13)):
            if p-pd.DateOffset(months=6)<=d<=q: hit=i; break
        if hit is None: other.append((pub.strftime('%Y-%m-%d'),d.strftime('%Y-%m'),leg,cond))
        elif hit not in lags: lags[hit]=((pub-me(PK13[hit])).days,leg,cond)
    return lags,other
out=[]
def run(nm,legs,conf):
    on,t=onsets13(legs,conf); lags,other=rec13(on)
    L=[lags[i][0] if i in lags else None for i in range(13)]; Lv=[l for l in L if l is not None]
    ff,nq=first_factor(legs); expo=win_expo([HS[c] for c in conf],7,5)[0] if conf else 100.0; hz=ff*expo/100
    closes=[(o['published'].strftime('%Y-%m-%d'),o['date'].strftime('%Y-%m'),o['leg']) for o in t if o['kind']=='trough' and o['published']>=pd.Timestamp('2023-01-01')]
    out.append(f"{nm}\n   legs {''.join(legs)} confirmers {'+'.join(conf) or 'none'} | peaks {len(Lv)}/13 lags {L} median {np.median(Lv):.0f} worst {max(Lv)} | other {other}\n   first factor {ff*100:.2f}%/yr ({nq} quiet episodes) x exposure {expo:.2f}% = hazard {hz*100:.3f}%/yr = one in {1/hz if hz>0 else float('inf'):.0f} | 2024: {'called '+str(lags[12][1:]) if 12 in lags else 'MISSED'} | troughs 2023-26 {closes}")
run("CONTROL v9 (demand + supply confirm)",PK5,('S','V','H','P'))
run("v9 minus housing pair (proposed v10)",PK5,('S','V','P'))
run("SUPPLY ONLY: Sahm confirms",PK5,('S',))
run("SUPPLY ONLY: Sahm or IUR gap confirms",PK5,('S','U'))
run("SUPPLY + hours pair",PK5,('S','U','P'))
run("claims flows only propose (no U), Sahm or IUR confirm",('A','B','C','M'),('S','U'))
run("HUB-LIKE: U proposes, demand confirms (vacancy, housing, hours)",('U',),('V','H','P'))
run("HUB-LIKE: U proposes, Sahm or demand confirms",('U',),('S','V','H','P'))
run("HUB-LIKE without housing pair",('U',),('S','V','P'))
txt='\n'.join(out); print(txt); open('LABOUR_CONFIRM_2026-09-05.txt','w').write(txt+'\n')

# ---- TWO-TRACK RULE: a claims-flow proposal (A B C M) confirmed by the labour-supply side (Sahm, IUR gap); a labour-supply proposal
# (U = IUR gap 0.50; X = Sahm 0.50 on first prints, published the 5th of the month after, dated the crossing month less three, Paper 1's
# convention) confirmed by the demand side (vacancy, housing pair, hours pair).  Each track confirmed in its own window (6 back, 4 forward)
# by the same machine, then the confirmed calls of both tracks are read as two legs by one state machine with the v9 closers.
def leg_X(gap=g,line=0.5):
    out=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line: out.append((pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4), t-pd.DateOffset(months=3))); armed=False
        elif not armed and v<0.0: armed=True     # re-arm when the gap closes (the rate back at its own minimum)
    return out
PLU['X']=leg_X()
def confirmed(legs,conf):
    sec=[CONF[c] for c in conf if c!='S']; sahm=g if 'S' in conf else None
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:PLU[q] for q in legs},{q:TLG[q] for q in ('K','J','H','S','T')},sahm=sahm,line=0.5,second=sec if sec else None,horizon_months=4,back_months=6)
    return [(o['published'],o['date']) for o in t if o['kind']=='peak'],t
def two_track(nm,flow_conf=('S','U'),supply_legs=('U','X'),demand_conf=('V','H','P'),flow_legs=('A','B','C','M')):
    F,_=confirmed(flow_legs,flow_conf); Sx,_=confirmed(supply_legs,demand_conf)
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({'flow':F,'supply':Sx},{q:TLG[q] for q in ('K','J','H','S','T')})
    on=[(o['published'],o['date'],o['leg'],None) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')]
    lags,other=rec13(on); L=[lags[i][0] if i in lags else None for i in range(13)]; Lv=[l for l in L if l is not None]
    ff,nq=first_factor(flow_legs); e1=win_expo([HS[c] for c in flow_conf],7,5)[0]
    e2=win_expo([HS[c] for c in demand_conf],7,5)[0]
    # supply-side proposal rate: quiet-month episodes of U and X (their own first factor)
    onS=[(p,d) for p,d in sorted(PLU['U']+PLU['X']) if p>=pd.Timestamp('1948-06-01')]; nqS=sum(1 for p,d in onS if qm.get(pd.Timestamp(d.year,d.month,1),False))
    hz=ff*e1/100+(nqS/QY)*e2/100
    closes=[(o['published'].strftime('%Y-%m-%d'),o['date'].strftime('%Y-%m'),o['leg']) for o in t if o['kind']=='trough' and o['published']>=pd.Timestamp('2023-01-01')]
    out.append(f"{nm}\n   flows {''.join(flow_legs)} confirmed by {'+'.join(flow_conf)}; supply {''.join(supply_legs)} confirmed by {'+'.join(demand_conf)} | peaks {len(Lv)}/13 lags {L} median {np.median(Lv):.0f} worst {max(Lv)} | other {other}\n   hazard = {ff*100:.2f}% x {e1:.2f}% + {nqS/QY*100:.2f}% ({nqS} quiet supply proposals) x {e2:.2f}% = {hz*100:.3f}%/yr = one in {1/hz if hz>0 else float('inf'):.0f} | 2024: {'called '+str(lags[12][1:]) if 12 in lags else 'MISSED'} | troughs 2023-26 {closes} | by leg {[lags[i][1] for i in sorted(lags)]}")
out.append("\n==== TWO-TRACK ====")
two_track("TWO-TRACK, full")
two_track("TWO-TRACK without housing pair",demand_conf=('V','P'))
two_track("TWO-TRACK, supply track alone (hub in this harness)",flow_legs=(),flow_conf=('S','U')) if False else None
run("HUB in this harness: U and X propose, demand confirms",('U','X'),('V','H','P'))
run("HUB without housing pair",('U','X'),('V','P'))
print('\n'.join(out[-5:])); open('LABOUR_CONFIRM_2026-09-05.txt','w').write('\n'.join(out)+'\n')
