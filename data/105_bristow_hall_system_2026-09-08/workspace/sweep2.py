"""Joint sweep: the two levers that buy speed cleanly (vacancy line, starts line) together, with the rest re-swept conditional on them.
Zero other calls on BOTH vintages required. Date errors and margins reported for every survivor."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep1.py').read().split("BASE=dict(")[0].replace("out=open('sweep1.out','w')","out=open('sweep2.out','w')"))
BASE=dict(sahm=0.50,vac=0.36,u45=0.45,low=0.25,starts=35,half=4,h1=2.0,h2=1.20)
def full(nm,p,verbose=False):
    rs=[run(p,s) for s in (s_cur,spl)]
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in rs)
    lp=[rs[0]['lags_p'].get(i) for i in range(13)]; lf=[rs[1]['lags_p'].get(i) for i in range(13)]
    ep=[rs[0]['errs_p'].get(i) for i in range(13)]
    v73=[rs[0]['lags_p'][i] for i in range(5,13) if i in rs[0]['lags_p']]
    P(f"{'OK ' if ok else 'BAD'} {nm:38s} cur {lp}")
    P(f"     fp  {lf} | 1973-on med {np.median(v73):.1f} mean {np.mean(v73):.1f} | dates {ep} exact {sum(1 for e in ep if e==0)} w1 {sum(1 for e in ep if e is not None and abs(e)<=1)} | others {[o[1] for r in rs for o in r['other']]}")
    return ok,lp
for vac in [0.36,0.35]:
    for st in [35,32,30]:
        full(f'vacancy {vac}, starts {st}',{**BASE,'vac':vac,'starts':st})
P("\n--- with vacancy 0.35 + starts 30, re-sweep the rest ---")
B2={**BASE,'vac':0.35,'starts':30}
for l in [0.25,0.22]: full(f'  low {l}',{**B2,'low':l})
for u in [0.45,0.42]: full(f'  u45 {u}',{**B2,'u45':u})
for h in [4,3]: full(f'  rate half {h}',{**B2,'half':h})
for h1 in [2.0,1.8]: full(f'  hours {h1}',{**B2,'h1':h1})
P("\n--- with vacancy 0.35 + starts 32 (1969 not early), re-sweep ---")
B3={**BASE,'vac':0.35,'starts':32}
for l in [0.25,0.22]: full(f'  low {l}',{**B3,'low':l})
for h in [4,3]: full(f'  rate half {h}',{**B3,'half':h})
P("\nquiet margins at the chosen values:")
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p_,t in zip(PK,TR): q[(idx>=p_-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def inw(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
def wmax(ser,dd): seg=ser[(ser.index>=dd-pd.DateOffset(months=6))&(ser.index<=dd+pd.DateOffset(months=4))]; return (round(float(seg.max()),3),seg.idxmax().strftime('%Y-%m')) if len(seg) else (float('nan'),'')
for st in [35,32,30]:
    _,MX=mkpair(st,4)
    ql=[(p_,dd) for p_,dd in leg_gapx(s_cur,0.25,rearm='window') if not inw(dd)]+[(p_,dd) for p_,dd in leg_gapx(spl,0.25,rearm='window') if not inw(dd)]+[(p_,dd) for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)]
    mm=sorted({wmax(MX,dd) for p_,dd in ql if not np.isnan(wmax(MX,dd)[0])},reverse=True)[:4]
    h=(MX>=1.0).reindex(pd.date_range('1960-01-01','2026-07-01',freq='MS')).fillna(False); q=quiet(h.index)
    P(f"   starts {st}: pair quiet-window maxima {mm}; quiet months at the line {[m.strftime('%Y-%m') for m,v in h.items() if v and q[m]]}")
for vl in [0.36,0.35]:
    qf=[(p_,dd) for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)]
    P(f"   vacancy {vl}: pre-1971 quiet 0.45 proposals blocked with vacancy maxima {[(dd.strftime('%Y-%m'),wmax(vr,dd)[0]) for p_,dd in qf]}; quiet Sahm-0.50 crossings still 1976-11, 2003-06 (vacancy 0.05 / 0.28 -> margin {round(vl-0.28,3)} at 2003)")
out.close()
