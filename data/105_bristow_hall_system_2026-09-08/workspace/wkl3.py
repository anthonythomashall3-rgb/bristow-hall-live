"""THE SURVEY-WEEK LEG ADDED TO THE RULE. The survey-week insured rate is made an eighth object: a proposer on the
same conjunction terms as the others, confirmed inside the same window. Swept on the frozen rule, with every other
call printed in full, so the price of each line is visible."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('wkl3.out','w')"))
D=W+'/lab/data/fred_weekly'
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
# Rule 23 clause 1: where a vintage record exists it is used. This line's transcription of the printed
# weekly releases IS the as-printed record to April 1983, so it is used to its end and the Department's current
# file only afterwards.
IURW=pd.concat([own,frd[frd.index>own.index.max()]]).sort_index()
def survey(s):
    rows={}
    for t,v in s.items():
        m=pd.Timestamp(t.year,t.month,1); d=abs((t-pd.Timestamp(t.year,t.month,12)).days)
        if m not in rows or d<rows[m][0]: rows[m]=(d,v,t)
    idx=sorted(rows); return pd.Series([rows[m][1] for m in idx],index=idx), pd.Series([rows[m][2] for m in idx],index=idx)
SI,SW=survey(IURW)
def leg_sv(line,look=52,pub=12,rearm='zero'):
    gap=(SI-SI.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((SW[t]+pd.Timedelta(days=pub),t)); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
SRC=open('walk3.py').read()
def build8(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
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
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    U=confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')
    X=hubv(p['sahm']); I=confirm_w(leg_ic(ICfp,p['ic']),C1,'month')
    legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm=p.get('wrearm','zero')),C1+C2,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
P(f"{'wline':>7s} {'rearm':7s}  onsets 1948..2024                                            others")
for wl in [None,0.8,0.6,0.5,0.45,0.4,0.35,0.30,0.25]:
    for rear in (['zero'] if wl is None else ['zero','window']):
        p=dict(BASE); p['wline']=wl; p['wrearm']=rear
        r,t=build8(p); lp=[r['lags_p'].get(i) for i in range(13)]
        legs_used=[r['opens'][i]['leg'] if i in r['opens'] else '-' for i in range(13)]
        P(f"{str(wl):>7s} {rear:7s}  {lp}  {[(d,lg) for d,_,lg in r['other']]}")
        P(f"        legs {legs_used}")
out.close()
