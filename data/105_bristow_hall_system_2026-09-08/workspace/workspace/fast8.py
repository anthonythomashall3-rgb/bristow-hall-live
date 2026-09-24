"""The fast form: four supply-side readings, each with its admissible demand-side partners; current file and first prints."""
from mini import *
from hub import leg_X2
from legu_min import s_cur, spl
out=open('fast8.out','w')
def P(*a):
    print(*a); print(*a,file=out); out.flush()
# yoy weekly state breadth, current file (ar539 c8) and on the page-8 first prints (insured unemployment by state as first published)
d=pd.read_csv(W+'/lab/dol/ar539.csv',low_memory=False); d['week']=pd.to_datetime(d['c2'],errors='coerce'); d=d[d['week'].notna()&d['st'].notna()]; d=d[~d['st'].isin(['PR','VI'])]
CW=d.pivot_table(index='week',columns='st',values='c8',aggfunc='first').sort_index().apply(pd.to_numeric,errors='coerce').resample('W-SAT').last()
def breadth(X):
    S8=X.rolling(8).sum(); Y=np.log(S8)-np.log(S8.shift(52)); return ((Y>=0.10).sum(axis=1)/Y.notna().sum(axis=1)*100.0).dropna()
BR=breadth(CW)
FPw=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','45_dol_first_prints_2026-09/state_iu_first_print_wide.csv'),index_col=0,parse_dates=True)
FPw=FPw.drop(columns=[c for c in FPw.columns if c in ('Puerto Rico','Virgin Islands')]).resample('W-SAT').last()
FPw=FPw.where(FPw>0)   # archive gaps are NaN; keep them NaN (the 41 missing weeks)
BRfp=breadth(FPw)
BRs=pd.concat([BR[BR.index<BRfp.dropna().index.min()],BRfp.dropna()]).sort_index()
P("yoy breadth: current",BR.index.min().date(),"->",BR.index.max().date(),"| first-print breadth from",BRfp.dropna().index.min().date())
P("first-print vs current breadth, monthly max, Oct 2007-Jun 2008:",pd.concat([BR.rename('cur'),BRfp.rename('fp')],axis=1)['2007-10':'2008-06'].resample('MS').max().round(0).T.to_string())
P("first-print vs current breadth, 2023-03..2024-12:",pd.concat([BR.rename('cur'),BRfp.rename('fp')],axis=1)['2023-03':'2024-12'].resample('MS').max().round(0).T.to_string())
def gapof(s): return (s-s.rolling(52,min_periods=52).min().shift(1)).dropna()
def leg_gap(gap,line,rearm=0.0,pub=5):
    c=[]; armed=True
    for t,v in gap.items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
def leg_br(Bx,line=50.0,k=1,quiet_weeks=26,pub_days=9):
    outc=[]; below=0; run=0; start=None
    for t,v in Bx.items():
        if v>=line:
            run+=1
            if run==1: start=t
            if run==k and below>=quiet_weeks: outc.append((t+pd.Timedelta(days=pub_days),pd.Timestamp(start.year,start.month,1)))
            if run>=k: below=0
        else: run=0; below+=1
    return outc
def confirm(calls, confs, back=6, fwd=4):
    outc=[]
    for p,dtd in calls:
        best=None
        for cf in confs:
            ser=cf['gap']; seg=ser[(ser.index>=p-pd.DateOffset(months=back))&(ser.index<=p+pd.DateOffset(months=fwd))]; hit=seg[seg>=cf['line']]
            if len(hit)==0: continue
            t=hit.index[0]
            pub_s=(t+pd.Timedelta(days=cf['pub_lag_days'])) if 'pub_lag_days' in cf else (pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=cf['pub_day']-1))
            if best is None or pub_s<best[0]: best=(pub_s,cf['name'])
        if best: outc.append((max(p,best[0]),dtd,best[1]))
    return outc
V30=dict(name='vacancy30',gap=vr,line=0.30,pub_day=30); Hp=dict(name='housing35',gap=PAIR,line=1.0,pub_day=18); Pp=dict(name='hourspair',gap=P1,line=1.0,pub_day=5)
KJHS={k:TLG[k] for k in 'KJHS'}
def run(nm,legs):
    pk={k:[(p,dd) for p,dd,_ in v] for k,v in legs.items()}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,KJHS)
    r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]; v=[l for l in lp if l is not None]
    P(f"\n{nm}\n   lags {[('-' if l is None else l) for l in lp]}  other {[(d,lg) for _,d,lg in r['other']]}")
    P(f"   1973 on: median {np.median(v73):.1f} mean {np.mean(v73):.1f} worst {max(v73)} <=0 {sum(1 for l in v73 if l<=0)} <=31 {sum(1 for l in v73 if l<=31)} | all 13: median {np.median(v):.0f} mean {np.mean(v):.1f} | dates exact {sum(1 for e in r['errs_p'].values() if e==0)} within1 {sum(1 for e in r['errs_p'].values() if abs(e)<=1)} | troughs {len(r['lags_t'])} median {np.median(list(r['lags_t'].values())):.0f}")
    cond={(p,dd):c for vv in legs.values() for p,dd,c in vv}
    for i in range(5,13):
        if i in r['opens']: t=r['opens'][i]; P(f"      {PK[i]:%Y-%m}: {t['published']:%Y-%m-%d} by {t['leg']} dated {t['date']:%Y-%m} ({cond.get((t['published'],t['date']),'?')})")
    return r
X43=[(p,dd,'hub') for p,dd in leg_X2(sahm_line=0.43,vac_line=0.30)]
for vint,s,Bx in [('CURRENT FILE',s_cur,BR),('FIRST PRINTS (advance IUR 2002 on; page-8 breadth 2003 on)',spl,BRs)]:
    gp=gapof(s)
    U45=confirm(leg_gap(gp,0.45),[V30,Hp,Pp]); UL=confirm(leg_gap(gp,0.25),[Hp]); BRL=confirm(leg_br(Bx),[Hp])
    P(f"\n==== {vint} ====")
    P("  U-low 0.25 raw crossings:",[p.strftime('%Y-%m-%d') for p,_ in leg_gap(gp,0.25)])
    P("  breadth raw crossings:",[p.strftime('%Y-%m-%d') for p,_ in leg_br(Bx)])
    run("corner (U45{V|H|P} + hub43)",{'U':U45,'X':X43})
    run("FAST FORM: + U-low 0.25{housing} + breadth{housing}",{'U':U45,'L':UL,'R':BRL,'X':X43})
    run("  without the breadth branch",{'U':U45,'L':UL,'X':X43})
out.close()
