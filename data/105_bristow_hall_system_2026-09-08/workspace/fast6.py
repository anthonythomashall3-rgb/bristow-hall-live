"""New objects for speed, zero false alarms: a LOWER insured-rate line (0.30) confirmed only by depth/breadth objects
(the housing x rate pair; the year-over-year weekly state continued-claims breadth), beside the corner rule."""
from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur, spl
out=open('fast6.out','w')
def P(*a):
    print(*a); print(*a,file=out); out.flush()
# ---- the year-over-year weekly state breadth (breadth_yoy.py's construction): 8-week sums of state continued claims vs a year earlier
d=pd.read_csv(W+'/lab/dol/ar539.csv',low_memory=False); d['week']=pd.to_datetime(d['c2'],errors='coerce'); d=d[d['week'].notna()&d['st'].notna()]; d=d[~d['st'].isin(['PR','VI'])]
CW=d.pivot_table(index='week',columns='st',values='c8',aggfunc='first').sort_index().apply(pd.to_numeric,errors='coerce').resample('W-SAT').last()
S8=CW.rolling(8).sum(); Y=np.log(S8)-np.log(S8.shift(52)); BR=((Y>=0.10).sum(axis=1)/Y.notna().sum(axis=1)*100.0).dropna()
P("yoy state breadth (x=10, 8 weeks, share of states):",BR.index.min().date(),"->",BR.index.max().date())
# ---- IUR gap and legs
gap=(s_cur-s_cur.rolling(52,min_periods=52).min().shift(1)).dropna()
def leg_gap(line,rearm,pub=5):
    c=[]; armed=True
    for t,v in gap.items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
def confirm(calls, confs, back=6, fwd=4):
    outc=[]
    for p,dtd in calls:
        best=None
        for cf in confs:
            ser=cf['gap']; seg=ser[(ser.index>=p-pd.DateOffset(months=back))&(ser.index<=p+pd.DateOffset(months=fwd))]
            hit=seg[seg>=cf['line']]
            if len(hit)==0: continue
            t=hit.index[0]
            pub_s=(t+pd.Timedelta(days=cf['pub_lag_days'])) if 'pub_lag_days' in cf else (pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=cf['pub_day']-1))
            if best is None or pub_s<best[0]: best=(pub_s,cf['name'])
        if best: outc.append((max(p,best[0]),dtd,best[1]))
    return outc
V30=dict(name='vacancy30',gap=vr,line=0.30,pub_day=30); V42=dict(name='vacancy42',gap=vr,line=0.42,pub_day=30)
Hp=dict(name='housing35',gap=PAIR,line=1.0,pub_day=18); Pp=dict(name='hourspair',gap=P1,line=1.0,pub_day=5)
BRc=dict(name='breadth_yoy50',gap=BR,line=50.0,pub_lag_days=9)
U45=confirm(leg_gap(0.45,0.0),[V30,Hp,Pp]); X43=[(p,dd,'hub') for p,dd in leg_X2(sahm_line=0.43,vac_line=0.30)]
P("\nU-low raw crossings at 0.30 (re-arm at 0):",[(p.strftime('%Y-%m-%d')) for p,_ in leg_gap(0.30,0.0)])
P("U-low raw crossings at 0.30 (re-arm below 0.30):",[(p.strftime('%Y-%m-%d')) for p,_ in leg_gap(0.30,0.29)])
P("U-low raw crossings at 0.30 (re-arm at 0.10):",[(p.strftime('%Y-%m-%d')) for p,_ in leg_gap(0.30,0.10)])
KJHS={k:TLG[k] for k in 'KJHS'}
def run(nm,legs):
    pk={k:[(p,dd) for p,dd,_ in v] for k,v in legs.items()}
    with contextlib.redirect_stdout(io.StringIO()):
        turns=B.american_chronology(pk,KJHS)
    r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]
    P(f"\n{nm}\n   lags {[('-' if l is None else l) for l in lp]}  other {[(d,lg) for _,d,lg in r['other']]}  | 1973 on median {np.median(v73):.1f} mean {np.mean(v73):.1f} | <=31 {sum(1 for l in v73 if l<=31)}")
    cond={ (p,dd):c for v in legs.values() for p,dd,c in v}
    for i in range(5,13):
        if i in r['opens']: t=r['opens'][i]; P(f"      {PK[i]:%Y-%m}: {t['published']:%Y-%m-%d} by {t['leg']} dated {t['date']:%Y-%m} ({cond.get((t['published'],t['date']),'?')})")
    return r
run("A  corner: U45{V30|H|P} + hub43",{'U':U45,'X':X43})
for rn,rname in [(0.0,'re-arm 0'),(0.29,'re-arm below line'),(0.10,'re-arm 0.10')]:
    UL=leg_gap(0.30,rn)
    run(f"B  + U-low 0.30 ({rname}) confirmed by housing pair | yoy breadth 50",{'U':U45,'L':confirm(UL,[Hp,BRc]),'X':X43})
run("C  + U-low 0.30 (re-arm 0) confirmed by housing pair only",{'U':U45,'L':confirm(leg_gap(0.30,0.0),[Hp]),'X':X43})
run("D  + U-low 0.30 (re-arm 0) confirmed by yoy breadth only",{'U':U45,'L':confirm(leg_gap(0.30,0.0),[BRc]),'X':X43})
run("E  + U-low 0.30 (re-arm 0) confirmed by housing | breadth | vacancy 0.42",{'U':U45,'L':confirm(leg_gap(0.30,0.0),[Hp,BRc,V42]),'X':X43})
run("F  + U-low 0.20 (re-arm 0) confirmed by housing | breadth",{'U':U45,'L':confirm(leg_gap(0.20,0.0),[Hp,BRc]),'X':X43})
P("\nquiet-period readings at every U-low (0.30) crossing, re-arm 0: housing pair / breadth max within [p-6m, p+4m]")
for p,dd in leg_gap(0.30,0.0):
    inw=any(q-pd.DateOffset(months=6)<=dd<=t for q,t in zip(PK,TR))
    seg=PAIR[(PAIR.index>=p-pd.DateOffset(months=6))&(PAIR.index<=p+pd.DateOffset(months=4))]; sb=BR[(BR.index>=p-pd.DateOffset(months=6))&(BR.index<=p+pd.DateOffset(months=4))]
    P(f"   {p:%Y-%m-%d} {'RECESSION' if inw else 'quiet    '} housing pair max {seg.max() if len(seg) else float('nan'):.2f}  breadth max {sb.max() if len(sb) else float('nan'):.0f}  vacancy max {vr[(vr.index>=p-pd.DateOffset(months=6))&(vr.index<=p+pd.DateOffset(months=4))].max():.2f}")
out.close()
