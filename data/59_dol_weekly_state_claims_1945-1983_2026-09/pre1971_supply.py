"""THE SUPPLY TRACK BEFORE 1971 on the programme's own first prints (6 September 2026).
The weekly insured rate the tool reads (IURSA) begins 1971.  Collection 59 now holds the release's national insured unemployment
as first printed, weekly, from 1946.  Here: real-time seasonal adjustment with the lab's own weekly routine (nat_sa_rt.sa_rt:
week-of-year medians, seven-year window, refitted each December), divided by covered employment (ET Handbook 394, annual, states
and DC), rounded to one decimal = a first-print real-time insured rate 1948-70, spliced before IURSA.  The housing pair's housing
half before 1959 from the NBER starts series (collection 74) adjusted with the monthly routine.  Then v14 with U, the low reading
and the flow confirmer all running from the late 1940s.  Both vintages (the pre-2002 part is the same on both)."""
exec(open('freeze14.py').read().split("for vint in ('current','firstprints'):\n    calls,turns")[0])
G2={}; exec(open('/home/claude/lab/weekly/nat_sa_rt.py').read().split("if __name__")[0],G2); sa_rt=G2['sa_rt']
R="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/"
N=pd.read_csv(R+'59_dol_weekly_state_claims_1945-1983_2026-09/national_weekly_first_prints_1945_1983.csv',index_col=0,parse_dates=True)
iu=N['iu'].dropna(); idx=pd.date_range('1946-07-27','1983-12-31',freq='W-SAT'); iu=iu.reindex(idx)
iu=iu.interpolate(limit=6,limit_area='inside'); iu=iu[iu.first_valid_index():]
iu_sa=sa_rt(iu.dropna())
h=pd.read_csv(R+'37_dol_eta5159_2026-09/raw/hbook.csv',low_memory=False); h['C2']=pd.to_numeric(h['C2'],errors='coerce')
ce=h[~h.ST.isin(['US','PR','VI'])].groupby('YR')['C2'].sum(); ce.index=[pd.Timestamp(y,7,1) for y in ce.index]
ce_w=ce.reindex(ce.index.union(iu_sa.index)).interpolate().reindex(iu_sa.index)
iur_rt=(iu_sa/ce_w*100).round(1)
j=pd.concat([iur_rt.rename('rt'),s_cur.rename('iursa')],axis=1).dropna()
P(f"first-print real-time insured rate: {iur_rt.index.min().date()}..{iur_rt.index.max().date()}; vs IURSA 1971-83 median diff {(j.rt-j.iursa).median():+.2f} pt, |diff|<=0.2 share {((j.rt-j.iursa).abs()<=0.2).mean():.2f}; gap agreement: |gap diff|<=0.1 share {((gap_w(j.rt)-gap_w(j.iursa)).abs()<=0.1).mean():.2f}")
s_ext=pd.concat([iur_rt[iur_rt.index<s_cur.index.min()],s_cur]).sort_index()
s_ext_fp=pd.concat([iur_rt[iur_rt.index<s_fp.index.min()],s_fp]).sort_index()
# housing half before 1959: NBER starts, real-time monthly SA
nb=pd.read_csv(R+'74_nber_housing_starts_1939_1963_2026-09/housing_starts_nonfarm_monthly_1939_1963_nber_m02161.csv',index_col=0,parse_dates=True).iloc[:,0]
G3={}; exec(open('/home/claude/lab/fh/build_rt.py').read().split("L=pd.read_csv(")[0],G3)
nb_sa=np.exp(G3['sa_realtime'](pd.DataFrame({'h':nb}))['h'])
lh_ext=pd.concat([np.log(nb_sa[nb_sa.index<HO.index.min()])*100, lh]).sort_index()
def pairx_ext(hl):
    u10=(UR*10).round()
    return pd.concat([(lh_ext.rolling(12).max()-lh_ext.rolling(2).mean())/hl,(u10-u10.rolling(12).min())/2.0],axis=1).min(axis=1,skipna=False).round(9).dropna()
HxE=dict(name='housing35 exact (NBER before 1959)',gap=pairx_ext(35),line=1.0,pub_day=18)
P(f"housing pair with the NBER half: from {pairx_ext(35).index.min():%Y-%m}; quiet months >=1 before 1960: "+', '.join(m.strftime('%Y-%m') for m,v in pairx_ext(35).loc[:'1959-12'].items() if v>=1 and qm.get(m,False)))
def run_ext(nm,vint,sx,hx,low_on=True,u_on=True):
    global g
    g_old=g; g=g6
    try:
        s=sx; IURG=gap_w(s)
        F=track(flows(vint),g,[dict(name='IUR gap 0.50',gap=IURG,line=0.50,pub_day=12,pub_lag_days=12),HP_FLOW])
        SL={'X':leg_X2(g,0.5)}
        if u_on: SL['U']=leg_w(IURG)
        Sx=track(SL,None,[CONF['V'],hx,CONF['P']]); legs={'flow':[(p,d) for p,d,_,_ in F],'supply':[(p,d) for p,d,_,_ in Sx]}
        UL=ulow(IURG,LOW) if low_on else []
        if low_on: legs['low']=[(p,d) for p,d,_,_ in track({'L':UL},None,[hx])]
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,CL); plainS=B.american_chronology(SL,CL)
        calls=[(o['published'],o['date'],o['leg'],None) for o in turns if o['kind']=='peak']
        lags,other,tr=score(calls,turns); Lg=[lags[i][0] if i in lags else None for i in range(13)]; Lv=[l for l in Lg if l is not None]; L73=[lags[i][0] for i in range(5,13) if i in lags]
        nS=sum(1 for o in plainS if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01') and qm.get(pd.Timestamp(o['date'].year,o['date'].month,1),False))
        qS=[o['date'].strftime('%Y-%m') for o in plainS if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01') and qm.get(pd.Timestamp(o['date'].year,o['date'].month,1),False)]
        nq=sum(1 for p,d in UL if p>=pd.Timestamp('1948-06-01') and qm.get(pd.Timestamp(d.year,d.month,1),False)); qL=[d.strftime('%Y-%m') for p,d in UL if p>=pd.Timestamp('1948-06-01') and qm.get(pd.Timestamp(d.year,d.month,1),False) and d<pd.Timestamp('1971-01-01')]
        P(f"{nm:46} [{vint:11}] {len(Lv)}/13 lags {Lg} median {np.median(Lv):3.0f} mean {np.mean(Lv):4.1f} 1973on {np.median(L73):3.0f} | other {[(o[0],o[1],o[2]) for o in other]} | quiet proposals: U/X {nS} {qS}; low {nq} (pre-1971 {qL}) | by leg {[lags[i][2] for i in sorted(lags)]}")
    finally: g=g_old
run_ext("v14 (control)",'current',s_cur,dict(name='housing35 exact',gap=pairx(35),line=1.0,pub_day=18))
run_ext("A. v14 + first-print insured rate before 1971",'current',s_ext,dict(name='housing35 exact',gap=pairx(35),line=1.0,pub_day=18))
run_ext("B. A + NBER housing half before 1959",'current',s_ext,HxE)
run_ext("B",'firstprints',s_ext_fp,HxE)
run_ext("C. B without the low reading before... (U only)",'current',s_ext,HxE,low_on=False)
open('PRE1971_SUPPLY_2026-09-06.txt','w').write('\n'.join(out)+'\n')
iur_rt.to_csv(R+'59_dol_weekly_state_claims_1945-1983_2026-09/national_iur_realtime_sa_first_prints_1948_1983.csv',header=['iur_rt_sa'])
P("\n==== BOTH VINTAGES 1971-83: the insured-rate legs on the release's first prints (real-time SA of the printed insured unemployment / covered employment) instead of IURSA ====")
s_v=pd.concat([iur_rt[(iur_rt.index>=pd.Timestamp('1971-01-01'))&(iur_rt.index<=pd.Timestamp('1983-05-14'))], s_cur[s_cur.index>pd.Timestamp('1983-05-14')]]).sort_index()
s_v=pd.concat([s_cur[s_cur.index<pd.Timestamp('1971-01-01')],s_v]).sort_index()
run_ext("v14 with 1971-83 insured rate as first printed",'current',s_v,dict(name='housing35 exact',gap=pairx(35),line=1.0,pub_day=18))
j=pd.concat([gap_w(iur_rt).rename('fp'),gap_w(s_cur).rename('cur')],axis=1).loc['1972-01':'1983-05'].dropna()
P(f"insured-rate gap, first prints vs current 1972-83: crossings of 0.50 (first week in each episode) fp {[t.strftime('%Y-%m-%d') for t,v in j.fp.items() if v>=0.5 and j.fp.shift(1)[t]<0.5][:12]} | cur {[t.strftime('%Y-%m-%d') for t,v in j.cur.items() if v>=0.5 and j.cur.shift(1)[t]<0.5][:12]}")
P(f"   crossings of 0.25: fp {[t.strftime('%Y-%m-%d') for t,v in j.fp.items() if v>=0.25 and j.fp.shift(1)[t]<0.25][:14]} | cur {[t.strftime('%Y-%m-%d') for t,v in j.cur.items() if v>=0.25 and j.cur.shift(1)[t]<0.25][:14]}")
open('PRE1971_SUPPLY_2026-09-06.txt','w').write('\n'.join(out)+'\n')
