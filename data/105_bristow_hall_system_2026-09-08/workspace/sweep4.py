"""Structural sweep of the objects themselves (not just their lines), with zero other calls on both vintages required:
 (a) the housing half's smoothing k (1, 2, 3 months) and its line; (b) the rate half's minimum window (6, 9, 12, 18 months);
 (c) the insured-rate gap's lookback (26, 39, 52, 78, 104 weeks) on both branches. Leg H on the true release clock throughout."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast40.py').read().split("V26=dict(")[0].replace("out=open('fast40.out','w')","out=open('sweep4.out','w')"))
TLH={k:list(v) for k,v in TLC.items()}; TLH['H']=[(p-pd.Timedelta(days=4),dd) for p,dd in TLC['H']]
def mkpair2(starts,half,k=2,minw=12):
    rate=(((UR-UR.rolling(minw).min())*10).round()/half); hh=(lh.rolling(12).max()-lh.rolling(k).mean())/starts
    ev=[(relH[m],'D',m) for m in hh.index if m in relH.index]+[(relU[m],'U',m) for m in rate.index if m in relU.index and m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(hh.get(lastD,np.nan),rate.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastU); mx[key]=max(mx.get(key,-9),v)
        if v>=1.0 and key not in fires: fires[key]=d
    G=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name=f'p{starts}x{half}k{k}m{minw}',gap=G,line=1.0,pubs=PB), pd.Series(mx).sort_index()
def leg_gapL(s,line,look,pub=12,rearm='zero'):
    gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
def go(nm,starts=33,half=4,k=2,minw=12,look45=52,look25=52,vac=0.35):
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Vc=dict(name='vac',gap=vr,line=vac,pubs=VJ36['pubs']); Hc,MX=mkpair2(starts,half,k,minw); Hh=mkhours(2.0,1.20)
    res=[]
    for s in (s_cur,spl):
        U=confirm_w(leg_gapL(s,0.45,look45,rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapL(s,0.25,look25,rearm='window')+F25,[Hc],'month'); X=hub_actual(0.50,vr,vac)
        pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; v73=[res[0]['lags_p'][i] for i in range(5,13) if i in res[0]['lags_p']]
    P(f"{'OK ' if ok else 'BAD'} {nm:40s} {lp} fp2007 {res[1]['lags_p'].get(10)} med {np.median(v73):.1f} mean {np.mean(v73):.1f} others {[o[1] for r in res for o in r['other']]}")
    return ok
P("baseline"); go('v2.6')
P("\n--- housing half: k-month mean, line swept ---")
for k in [1,2,3]:
    for st in [40,37,35,33,31,29,27]: go(f'k={k} starts {st}',starts=st,k=k)
P("\n--- rate half: minimum window ---")
for mw in [6,9,12,18,24]: go(f'rate min window {mw}',minw=mw)
P("\n--- insured-rate lookback (0.45 branch) ---")
for lk in [26,39,52,78,104]: go(f'look45 {lk}',look45=lk)
P("\n--- insured-rate lookback (0.25 branch) ---")
for lk in [26,39,52,78,104]: go(f'look25 {lk}',look25=lk)
out.close()
