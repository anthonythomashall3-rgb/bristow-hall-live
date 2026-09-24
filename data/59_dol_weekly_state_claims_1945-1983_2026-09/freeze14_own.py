"""ROUTE v14 (6 September 2026) = v13 + the hours x nondurable-employment pair (2.0, 1.20) admitted as a FLOW-TRACK confirmer - the demand side may confirm a claims-flow proposal only through this pair (two demand objects at their lines in the same month), never through the vacancy rate alone (that made July 2023). First prints from October 1961, the current vintage before (the route's convention where first prints do not exist). Adds no window exposure to the flow confirmers (6.00% with or without it); zero other calls on both vintages; one tick from the 1951 pause on the hours line (1.7 admits July 1951) and from the 1967 pause on the employment line (1.0 admits February 1967) - lines inherited from v7, not chosen here. Buys 1948 (95 -> 36) and 1953 (127 -> 97).
v13 header: = v12 with the second insured-rate reading at 0.25 — Anthony: "freeze v13" after the choice was put to him: fastest rule in the folder with zero observed other calls on both vintages; ten quiet-month proposals, none confirmed; modelled hazard one in 76.
(v12 header follows.)
v12 = v10 + (1) a SECOND reading of the insured rate's gap at 0.35 (seven-tenths of its line), re-armed when its four-month
window has closed and the gap is below the line, admitted as a supply-track proposal ONLY when the housing x rate pair confirms
it (collection 48's lever, at the corner of its clean plateau: 0.45 admits December 1980, 0.30 proposes in ten quiet months);
(2) Sahm's start-of-sample convention (the twelve-month minimum, or the months available once six exist) - affects 1948 only.
Everything else v10.  The supply pair (both supply objects at 0.7 of their lines) was tested and is redundant beside (1).
X stays on Sahm 0.50: Sahm* 0.46 would open 2024 a month earlier but dates it March, not Paper 1's April."""
exec(open('speed_menu.py').read().split("for vint in ('current','firstprints'):")[0])
import hashlib, csv
LOW=0.25
def latest_vintage(series):
    rows=list(csv.reader(open(AL+series+"_all_vintages.csv"))); return pd.Series({pd.Timestamp(r[0]):float(r[-1]) for r in rows[1:] if r[-1] not in ('','.')}).sort_index()
AWc=latest_vintage('AWHMAN'); NDc=latest_vintage('NDMANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l
f3 =lambda v,l:(-(v/v.shift(3)-1)*100)/l
P1c=pd.concat([f12(AWc,2.0),f3(NDc,1.2)],axis=1).min(axis=1).round(9).dropna()
P1x=pd.concat([P1c[P1c.index<P1.index.min()],P1]).sort_index()
HP_FLOW=dict(name='hours pair',gap=P1x,line=1.0,pub_day=5)
def v12(vint):
    global g
    g_old=g; g=g6
    try:
        s=s_cur if vint=='current' else s_fp; IURG=gap_w(s)
        F=track(flows(vint),g,[dict(name='IUR gap 0.50',gap=IURG,line=0.50,pub_day=12,pub_lag_days=12),HP_FLOW])
        SL={'U':leg_w(IURG),'X':leg_X2(g,0.5)}; Hx=dict(name='housing35 exact',gap=pairx(35),line=1.0,pub_day=18)
        Sx=track(SL,None,[CONF['V'],Hx,CONF['P']]); UL=ulow(IURG,LOW); Lc=track({'L':UL},None,[Hx])
        legs={'flow':[(p,d) for p,d,_,_ in F],'supply':[(p,d) for p,d,_,_ in Sx],'low':[(p,d) for p,d,_,_ in Lc]}
        with contextlib.redirect_stdout(io.StringIO()):
            turns=B.american_chronology(legs,CL); plainS=B.american_chronology(SL,CL)
        calls=[]
        for o in turns:
            if o['kind']!='peak': continue
            src={'flow':F,'supply':Sx,'low':Lc}[o['leg']]; mm=[c for c in src if c[0]==o['published'] and c[1]==o['date']]
            calls.append((o['published'],o['date'],o['leg']+':'+(mm[0][2] if mm else '?'),mm[0][3] if mm else None))
        return calls,turns,IURG,UL,plainS
    finally: g=g_old
for vint in ('current','firstprints'):
    calls,turns,IURG,UL,plainS=v12(vint); lags,other,tr=score(calls,turns)
    L=[lags[i][0] if i in lags else None for i in range(13)]; E=[lags[i][1] if i in lags else None for i in range(13)]; LT=[tr[i][0] if i in tr else None for i in range(13)]; ET=[tr[i][1] if i in tr else None for i in range(13)]
    Lv=[l for l in L if l is not None]; L73=[lags[i][0] for i in range(5,13) if i in lags]
    P(f"\nv14 [{vint}]  peaks {len(Lv)}/13  lags {L}  median {np.median(Lv):.0f} mean {np.mean(Lv):.1f} worst {max(Lv)} | 1973 on median {np.median(L73):.0f} mean {np.mean(L73):.1f} | in-month {sum(1 for l in Lv if l<=0)} within31 {sum(1 for l in Lv if l<=31)}")
    P(f"   peak date errors {E} exact {sum(1 for e in E if e==0)} mae {np.mean([abs(e) for e in E if e is not None]):.2f} | other calls {other}")
    P(f"   troughs {len([l for l in LT if l is not None])}/13 lags {LT} median {np.median([l for l in LT if l is not None]):.0f} | date errors {ET} exact {sum(1 for e in ET if e==0)} | closers {sorted(set(tr[i][2] for i in tr))}")
    P("   turns: "+'; '.join(f"{PK13[i]:%Y-%m} {lags[i][4]} {lags[i][2]} ({lags[i][3]})" for i in sorted(lags)))
    P("   every turn 2023 on: "+'; '.join(f"{o['kind']} {o['published']:%Y-%m-%d} dated {o['date']:%Y-%m} by {o['leg']}" for o in turns if o['published']>=pd.Timestamp('2023-01-01')))
calls,turns,IURG,UL,plainS=v12('current')
nS=sum(1 for o in plainS if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01') and qm.get(pd.Timestamp(o['date'].year,o['date'].month,1),False))
nq=sum(1 for p,d in UL if p>=pd.Timestamp('1948-06-01') and qm.get(pd.Timestamp(d.year,d.month,1),False))
inwin=lambda d: any(PK13[i]-pd.DateOffset(months=6)<=d<=TR13[i] for i in range(13))
tails=[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in UL if p>=pd.Timestamp('1948-06-01') and not inwin(d)]
eF=win_expo([HS['S'],hits(IURG.resample('MS').max(),0.5),hits(P1x,1.0)],7,5)[0]; eS=win_expo([HS['V'],hits(pairx(35),1.0),HS['P']],7,5)[0]; eL=win_expo([hits(pairx(35),1.0)],7,5)[0]
hz=3/QY*eF/100+nS/QY*eS/100+nq/QY*eL/100; hz_t=hz+len(tails)/(2026.6-1971)*eL/100
hi=poisson_hi(3,QY)*eF/100+poisson_hi(nS,QY)*eS/100+poisson_hi(nq,QY)*eL/100
P(f"\nHAZARD: flow 3 quiet proposals x {eF:.2f}% + supply {nS} x {eS:.2f}% + low reading {nq} quiet proposals x {eL:.2f}% (housing pair alone) = observed {hz*100:.3f}%/yr, one in {1/hz:.0f}; 95% ceiling one in {1/hi:.0f}")
P(f"   the low reading's proposals outside every recession window (tails, not quiet months by the route's convention): {tails} - if counted, {hz_t*100:.3f}%/yr, one in {1/hz_t:.0f}")
P(f"   at 0.25 the reading does not re-arm inside the 1980-81 double dip (the gap never falls below the line between the 1980 and 1981 episodes); the December 1980 hazard of the 0.45 setting (RULE.md v12) does not arise here")
P("\nLIVE EDGE: "+f"insured-rate gap {IURG.index[-1]:%Y-%m-%d} {IURG.iloc[-1]:+.2f} (low reading's line {LOW}, U's 0.50); low reading's last proposal {max(UL)[0]:%Y-%m-%d}; housing pair {pairx(35).index[-1]:%Y-%m} {pairx(35).iloc[-1]:+.2f}; state {'OPEN' if turns[-1]['kind']=='peak' else 'CLOSED'} since {turns[-1]['published']:%Y-%m-%d}")
W=shim.W; files=['freeze14.py','freeze13.py','freeze12.py','more_speed.py','speed_menu.py','v11_freeze_test.py','v11_candidate.py','twotrack.py','dominance.py','frontier.py','hazard_v5.py','expose.py','eta5159_gate.py','legU.py','minimise.py','shim.py']
files+=[W+'/lab/weekly/'+f for f in ('american_chronology.py','union_peaks.py','legs_1948.py','union_troughs.py')]+[W+'/bristow_rule_v3.py']+[W+'/lab/fh/'+f for f in ('HYB_state_claims_nsa_log.csv','HYB_state_claims_sa_rt_log.csv','HYB_nat_sa_rt.csv','HYB_national_nsa_weeklyavg.csv','build_rt.py')]
P("\nSHA-256:"); cat=hashlib.sha256()
for f in files:
    h=hashlib.sha256(open(f,'rb').read()).hexdigest(); cat.update(h.encode()); P(f"   {h}  {os.path.relpath(f,os.getcwd()) if f.startswith('/') else f}")
P(f"   concatenated: {cat.hexdigest()}")
open('FREEZE14_OWNFIELD_2026-09-06.txt','w').write('\n'.join(out)+'\n'); open('SHA256_v14_ownfield_2026-09-06.txt','w').write('\n'.join(l for l in out if 'concatenated' in l or (len(l.split())>=2 and len(l.split()[0])==64))+'\n')
