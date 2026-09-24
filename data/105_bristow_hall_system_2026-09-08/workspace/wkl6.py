"""THE SURVEY-WEEK LEG ADDED TO THE RULE. The survey-week insured rate is made an eighth object: a proposer on the
same conjunction terms as the others, confirmed inside the same window. Swept on the frozen rule, with every other
call printed in full, so the price of each line is visible."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('wkl6.out','w')"))
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
    CW={'C1':C1,'C2':C2,'all':C1+[Hc]}[p.get('wconf','all')]
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm=p.get('wrearm','zero')),CW,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm=p.get('wrearm2','window')),CW,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
P(f"{'W low':>6s} {'W high':>7s} {'rearmL':7s}  onsets                                                        dates  others")
for rl in ['zero','window']:
    for wl in [None,0.40,0.35,0.30,0.25,0.20,0.15]:
        for wh in [None,0.60,0.50,0.45,0.40]:
            p=dict(BASE); p['wline']=wl; p['wrearm']=rl; p['wline2']=wh; p['wrearm2']='window'; p['wconf']='C2'
            r,t=build8(p); lp=[r['lags_p'].get(i) for i in range(13)]; er=[r['errs_p'].get(i) for i in range(13)]
            o=[(d,lg) for d,_,lg in r['other']]
            if len(r['lags_p'])<13: continue
            v=[x for x in lp[4:] if x is not None]
            P(f"{str(wl):>6s} {str(wh):>7s} {rl:7s}  {lp}  ex{sum(1 for e in er if e==0)} w1 {sum(1 for e in er if e is not None and abs(e)<=1)} | med69 {np.median(v):.0f} over31 {sum(1 for x in v if x>31)}  {o}")
out.close()
